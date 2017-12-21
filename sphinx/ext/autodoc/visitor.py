# -*- coding: utf-8 -*-
"""
    sphinx.ext.autodoc.visitor
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Visitor for autodoc

    :copyright: Copyright 2007-2017 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from contextlib import contextmanager

from docutils.statemachine import StringList
from sphinx.util.inspect import Signature, getdoc

if False:
    # For type annotation
    from typing import Dict  # NOQA
    from sphinx.ext.autodoc.inspector import Attribute, Class, Function, Method  # NOQA


class SkipNode(Exception):
    pass


class Visitor(object):
    def __init__(self, options={}):
        # type: (Dict) -> None
        self.options = options
        self.indent = options.pop('indent', 0)
        self.result = StringList()

    @contextmanager
    def indented(self, indent):
        self.indent += indent
        yield
        self.indent -= indent

    def append(self, line, source=None, offset=0):
        # type: (unicode, unicode, int) -> None
        if line:  # not empty line
            line = ' ' * self.indent + line

        if source is None:
            source = '<generated>'

        self.result.append(line, source, offset)

    def dispatch_visit(self, subject):
        # type: (Namespace) -> None
        classname = subject.__class__.__name__.lower()
        method = getattr(self, 'visit_' + classname, self.unknown_visit)
        method(subject)

    def dispatch_departure(self, subject):
        # type: (Namespace) -> None
        classname = subject.__class__.__name__.lower()
        method = getattr(self, 'depart_' + classname, self.unknown_departure)
        method(subject)

    def unknown_visit(self, subject):
        # type: (Namespace) -> None
        raise NotImplementedError('Unsupported object: %r' % subject)

    def unknown_departure(self, subject):
        # type: (Namespace) -> None
        raise NotImplementedError('Unsupported object: %r' % subject)


class AutodocVisitor(Visitor):
    def visit_class(self, klass):
        # type: (Class) -> None
        self.append('')
        self.append('.. py:class:: %s' % klass.name)

        classname = getattr(klass.subject, '__name__', None)
        if klass.name != classname and classname:
            # the entry is an alias
            self.append('')
            self.append('   alias of :class:`%s`' % classname)
            raise SkipNode
        else:
            self.indent += 3

    def depart_class(self, klass):
        # type: (Class) -> None
        self.indent -= 3
        self.append('')

    def visit_method(self, method):
        # type: (Method) -> None
        sig = Signature(method.subject)
        self.append('')
        self.append('.. py:method:: %s%s' % (method.name, sig.format_args()))

        docstring = getdoc(method.subject)
        if docstring:
            source = 'docstring of %s' % method.fullname
            self.append('')
            with self.indented(3):
                for i, line in enumerate(docstring.splitlines()):
                    self.append(line, source, i + 1)

    def depart_method(self, method):
        # type: (Method) -> None
        pass

    def visit_attribute(self, attribute):
        # type: (Attribute) -> None
        self.append('')
        self.append('.. py:attribute:: %s' % attribute.name)

        analyzer = attribute.get_analyzer()
        attr_docs = analyzer.find_attr_docs()
        if attribute.fullname in attr_docs:
            self.append('')
            with self.indented(3):
                for i, line in enumerate(attr_docs[attribute.fullname].splitlines()):
                    self.append(line)

    def depart_attribute(self, attribute):
        # type: (Attribute) -> None
        pass

    def visit_function(self, function):
        # type: (Function) -> None
        sig = Signature(function.subject)
        self.append('')
        self.append('.. py:function:: %s%s' % (function.name, sig.format_args()))

        docstring = getdoc(function.subject)
        if docstring:
            source = 'docstring of %s' % function.fullname
            self.append('')
            with self.indented(3):
                for i, line in enumerate(docstring.splitlines()):
                    self.append(line, source, i + 1)

    def depart_function(self, subject):
        # type: (Function) -> None
        self.append('')
