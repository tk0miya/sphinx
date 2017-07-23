"""
    sphinx.ext.autodoc.inspector
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Inspect utilities for autodoc

    :copyright: Copyright 2007-2018 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import sys
import inspect

from sphinx.ext.autodoc import importer
from sphinx.pycode import ModuleAnalyzer, PycodeError
from sphinx.util import logging
from sphinx.util.inspect import isenumclass, safe_getattr

if False:
    # For type annotation
    from typing import Any, Callable, Dict, Iterator, List, Tuple  # NOQA

logger = logging.getLogger(__name__)


def import_module(modname, warningiserror=False):
    # type: (str, bool) -> Any
    module = importer.import_module(modname, warningiserror)
    return Module(module, modname, None, True)


class Namespace(object):
    type = None  # type: str

    def __init__(self, subject, name, parent, is_public=True, inherited_member=False):
        # type: (Any, str, Namespace, bool, bool) -> None
        self.subject = subject
        self.name = name
        self.parent = parent
        self.is_public = is_public
        self.inherited_member = inherited_member

    def get_members(self, attrgetter=safe_getattr):
        # type: (Callable) -> Dict[str, Namespace]
        raise NotImplementedError

    @property
    def fullname(self):
        # type: () -> str
        if self.parent:
            return ".".join([self.parent.fullname, self.name])
        else:
            return self.name

    @property
    def module(self):
        if self.type == 'module':
            return self
        else:
            return self.parent.module

    def get_analyzer(self):
        # type: () -> ModuleAnalyzer
        if self.parent:
            return self.parent.get_analyzer()
        else:
            return None

    def __repr__(self):
        # type: () -> str
        return "<inspector:%s %s at %s>" % (self.type, self.name, hex(id(self)))


class Module(Namespace):
    type = 'module'

    @property
    def __all__(self):
        # type: () -> List[str]
        if hasattr(self.subject, '__all__'):
            __all__ = self.subject.__all__

            # Sometimes __all__ is broken...
            if (not isinstance(__all__, (list, tuple)) or
                    not all(isinstance(entry, str) for entry in __all__)):
                logger.warning('__all__ should be a list of strings, not %r '
                               '(in module %s) -- ignoring __all__' %
                               (__all__, self.name))
                __all__ = dir(self.subject)
        else:
            __all__ = dir(self.subject)

        return __all__

    def get_members(self, attrgetter=safe_getattr):
        # type: (Callable) -> Dict[str, Namespace]
        __all__ = self.__all__  # store calculated __all__ attribute for caching
        members = {}  # type: Dict[str, Namespace]
        for name in dir(self.subject):
            try:
                member = attrgetter(self.subject, name)
                is_public = name in __all__
                if inspect.ismodule(member):
                    members[name] = Module(member, name, self, is_public)
                elif inspect.isclass(member):
                    members[name] = Class(member, name, self, is_public)
                elif inspect.isfunction(member) or inspect.isbuiltin(member):
                    members[name] = Function(member, name, self, is_public)
                else:
                    members[name] = Attribute(member, name, self, is_public)
            except AttributeError:
                logger.warning('missing attribute mentioned in :members: or __all__: '
                               'module %s, attribute %s' % (self.name, name))

        return members

    def get_analyzer(self):
        # type: () -> ModuleAnalyzer
        try:
            return ModuleAnalyzer.for_module(self.fullname)
        except PycodeError:
            return None


class Class(Namespace):
    type = 'class'

    def get_members(self, attrgetter=safe_getattr):
        # type: (Callable) -> Dict[str, Namespace]
        try:
            if isenumclass(self.subject) and sys.version_info[:2] == (3, 4):
                # use __members__ attribute for py34's enum instead
                __dict__ = self.subject.__members__
            else:
                __dict__ = attrgetter(self.subject, '__dict__')
        except AttributeError:
            __dict__ = {}

        members = {}  # type: Dict[str, Namespace]
        for name, subject in self.iter_members(attrgetter):
            inherited = name not in __dict__
            if inspect.ismodule(subject):
                members[name] = Module(subject, name, self, inherited_member=inherited)
            elif inspect.isclass(subject):
                members[name] = Class(subject, name, self, inherited_member=inherited)
            elif callable(subject):
                members[name] = Method(subject, name, self, inherited_member=inherited)
            else:
                members[name] = Attribute(subject, name, self, inherited_member=inherited)
        return members

    def iter_members(self, attrgetter):
        # type: (Callable) -> Iterator[Tuple[str, Any]]
        """Get all members and attributes of target object."""
        members = set()
        for name in dir(self.subject):
            try:
                members.add(name)
                yield name, attrgetter(self.subject, name)
            except AttributeError:
                continue

        analyzer = self.get_analyzer()
        if analyzer:
            # append instance attributes (cf. self.attr1) if analyzer knows
            from sphinx.ext.autodoc import INSTANCEATTR  # lazy importing

            namespace = self.get_objpath()
            for (ns, name) in analyzer.find_attr_docs():
                if namespace == ns and name not in members:
                    yield name, INSTANCEATTR

    def get_objpath(self):
        # type: () -> str
        objpath = []        # type: List[str]
        namespace = self    # type: Namespace
        while namespace:
            if namespace.type == 'module':
                break
            else:
                objpath.insert(0, namespace.name)
                namespace = namespace.parent

        return '.'.join(objpath)


class Method(Namespace):
    type = 'method'

    def __init__(self, subject, name, parent, is_public=True, inherited_member=False):
        # type: (Any, str, Namespace, bool, bool) -> None
        super(Method, self).__init__(subject, name, parent, is_public, inherited_member)

        method = parent.subject.__dict__.get(self.name)
        if isinstance(method, classmethod):
            self.method_type = 'classmethod'
        elif isinstance(method, staticmethod):
            self.method_type = 'staticmethod'
        else:
            self.method_type = 'method'

    def get_members(self, attrgetter=safe_getattr):
        # type: (Callable) -> Dict[str, Namespace]
        return {}


class Function(Namespace):
    type = 'function'

    def get_members(self, attrgetter=safe_getattr):
        return {}


class Attribute(Namespace):
    type = 'attribute'

    def get_members(self, attrgetter=safe_getattr):
        # type: (Callable) -> Dict[str, Namespace]
        return {}
