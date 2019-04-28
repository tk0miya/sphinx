"""
    sphinx.transforms.post_transforms.code
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    transforms for code-blocks.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import sys
import warnings
from typing import NamedTuple

from docutils import nodes
from pygments.lexers import PythonConsoleLexer, get_lexer_by_name, guess_lexer
from pygments.util import ClassNotFound

from sphinx import addnodes
from sphinx.deprecation import RemovedInSphinx40Warning
from sphinx.ext import doctest
from sphinx.locale import __
from sphinx.transforms import SphinxTransform
from sphinx.util import logging
from sphinx.util.nodes import NodeMatcher

if False:
    # For type annotation
    from typing import Any, Dict, List  # NOQA
    from sphinx.application import Sphinx  # NOQA


logger = logging.getLogger(__name__)

HighlightSetting = NamedTuple('HighlightSetting', [('language', str),
                                                   ('lineno_threshold', int)])


class HighlightLanguageTransform(SphinxTransform):
    """
    Apply highlight_language to all literal_block nodes.

    This refers both :confval:`highlight_language` setting and
    :rst:dir:`highlightlang` directive.  After processing, this transform
    removes ``highlightlang`` node from doctree.
    """
    default_priority = 400

    def apply(self, **kwargs):
        # type: (Any) -> None
        visitor = HighlightLanguageVisitor(self.document,
                                           self.config.highlight_language)
        self.document.walkabout(visitor)

        for node in self.document.traverse(addnodes.highlightlang):
            node.parent.remove(node)


class HighlightLanguageVisitor(nodes.NodeVisitor):
    def __init__(self, document, default_language):
        # type: (nodes.document, str) -> None
        self.default_setting = HighlightSetting(default_language, sys.maxsize)
        self.settings = []  # type: List[HighlightSetting]
        super().__init__(document)

    def unknown_visit(self, node):
        # type: (nodes.Node) -> None
        pass

    def unknown_departure(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_document(self, node):
        # type: (nodes.Node) -> None
        self.settings.append(self.default_setting)

    def depart_document(self, node):
        # type: (nodes.Node) -> None
        self.settings.pop()

    def visit_start_of_file(self, node):
        # type: (nodes.Node) -> None
        self.settings.append(self.default_setting)

    def depart_start_of_file(self, node):
        # type: (nodes.Node) -> None
        self.settings.pop()

    def visit_highlightlang(self, node):
        # type: (addnodes.highlightlang) -> None
        self.settings[-1] = HighlightSetting(node['lang'], node['linenothreshold'])

    def visit_literal_block(self, node):
        # type: (nodes.literal_block) -> None
        setting = self.settings[-1]
        if 'language' not in node:
            node['language'] = setting.language
            node['force_highlighting'] = False
        elif 'force_highlighting' not in node:
            node['force_highlighting'] = True
        if 'linenos' not in node:
            lines = node.astext().count('\n')
            node['linenos'] = (lines >= setting.lineno_threshold - 1)

    def visit_doctest_block(self, node):
        # type: (nodes.doctest_block) -> None
        self.visit_literal_block(node)  # type: ignore


class HighlightLanguageDetector(SphinxTransform):
    """Determine language of literal_block nodes."""
    default_priority = HighlightLanguageTransform.default_priority + 10

    def apply(self, **kwargs):
        # type: (Any) -> None
        matcher = NodeMatcher(nodes.literal_block, nodes.doctest_block)
        for node in self.document.traverse(matcher):
            node['language'] = self.detect(node)

    def detect(self, node):
        # type: (nodes.literal_block) -> str
        language = node['language']
        if language in ('py', 'python'):
            if node.rawsource.startswith('>>>'):
                return 'pycon'
            else:
                return 'python'
        elif language in ('py3', 'python3', 'default'):
            if node.rawsource.startswith('>>>'):
                return 'pycon3'
            else:
                return 'python3'
        elif language == 'pycon3':  # Sphinx's custom lexer
            return 'pycon3'
        elif language == 'guess':
            try:
                lexer = guess_lexer(node.rawsource)
                return lexer.aliases[0]
            except Exception:
                return 'none'
        else:
            try:
                get_lexer_by_name(language)
                return language
            except ClassNotFound:
                logger.warning(__('Pygments lexer name %r is not known'), language,
                               location=node)
                return 'none'


class TrimDoctestFlagsTransform(SphinxTransform):
    """
    Trim doctest flags like ``# doctest: +FLAG`` from python code-blocks.

    see :confval:`trim_doctest_flags` for more information.
    """
    default_priority = HighlightLanguageDetector.default_priority + 10

    def apply(self, **kwargs):
        # type: (Any) -> None
        if not self.config.trim_doctest_flags:
            return

        for node in self.document.traverse(nodes.literal_block):
            if node['language'] in ('pycon', 'pycon3'):
                source = node.rawsource
                source = doctest.blankline_re.sub('', source)
                source = doctest.doctestopt_re.sub('', source)
                node.rawsource = source
                node[:] = [nodes.Text(source)]

    @staticmethod
    def is_pyconsole(node):
        # type: (nodes.literal_block) -> bool
        warnings.warn('TrimDoctestFlagsTransform.is_pyconsole() is deprecated.',
                      RemovedInSphinx40Warning)
        if node.rawsource != node.astext():
            return False  # skip parsed-literal node

        language = node.get('language')
        if language in ('pycon', 'pycon3'):
            return True
        elif language in ('py', 'py3', 'python', 'python3', 'default'):
            return node.rawsource.startswith('>>>')
        elif language == 'guess':
            try:
                lexer = guess_lexer(node.rawsource)
                return isinstance(lexer, PythonConsoleLexer)
            except Exception:
                pass

        return False


def setup(app):
    # type: (Sphinx) -> Dict[str, Any]
    app.add_post_transform(HighlightLanguageTransform)
    app.add_post_transform(HighlightLanguageDetector)
    app.add_post_transform(TrimDoctestFlagsTransform)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
