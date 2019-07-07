"""
    sphinx.domains.glossary
    ~~~~~~~~~~~~~~~~~~~~~~~

    The glossary domain.

    :copyright: Copyright 2007-2020 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re
import unicodedata
from typing import Any, Dict, Generator, Iterable, List, Tuple
from typing import cast

from docutils import nodes
from docutils.nodes import Node
from docutils.parsers.rst import directives
from docutils.statemachine import StringList

from sphinx import addnodes
from sphinx.domains import Domain
from sphinx.locale import _, __
from sphinx.util import logging
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import make_id

if False:
    # For type annotation
    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment


logger = logging.getLogger(__name__)


def split_term_classifiers(s: str) -> Tuple[str, List[str]]:
    """Split a string into a term and classifiers."""
    parts = re.split(' +: +', s)
    return parts[0], parts[1:]


def make_glossary_term(env: "BuildEnvironment", textnodes: Iterable[Node], index_key: str,
                       source: str, lineno: int, rawsource: str, node_id: str = None,
                       document: nodes.document = None) -> nodes.term:
    # get a text-only representation of the term and register it
    # as a cross-reference target
    term = nodes.term(rawsource, '', *textnodes)
    term.source = source
    term.line = lineno
    termtext = term.astext()

    if node_id:
        # node_id is given from outside (mainly i18n module), use it forcedly
        term['ids'].append(node_id)
    elif document:
        node_id = make_id(env, document, 'term', termtext)
        term['ids'].append(node_id)
        document.note_explicit_target(term)

    glossary = cast(GlossaryDomain, env.get_domain('glossary'))
    glossary.note_term(term)

    # add an index entry too
    indexnode = addnodes.index()
    indexnode['entries'] = [('single', termtext, node_id, 'main', index_key)]
    indexnode.source, indexnode.line = term.source, term.line
    term.append(indexnode)

    return term


class Glossary(SphinxDirective):
    """
    Directive to create a glossary with cross-reference targets for :term:
    roles.
    """

    has_content = True
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {
        'sorted': directives.flag,
    }

    def run(self) -> List[Node]:
        node = addnodes.glossary()
        node.document = self.state.document

        # This directive implements a custom format of the reST definition list
        # that allows multiple lines of terms before the definition.  This is
        # easy to parse since we know that the contents of the glossary *must
        # be* a definition list.

        # first, collect single entries
        entries = []  # type: List[Tuple[List[Tuple[str, str, int]], StringList]]
        in_definition = True
        in_comment = False
        was_empty = True
        messages = []  # type: List[Node]
        for line, (source, lineno) in zip(self.content, self.content.items):
            # empty line -> add to last definition
            if not line:
                if in_definition and entries:
                    entries[-1][1].append('', source, lineno)
                was_empty = True
                continue
            # unindented line -> a term
            if line and not line[0].isspace():
                # enable comments
                if line.startswith('.. '):
                    in_comment = True
                    continue
                else:
                    in_comment = False

                # first term of definition
                if in_definition:
                    if not was_empty:
                        messages.append(self.state.reporter.warning(
                            _('glossary term must be preceded by empty line'),
                            source=source, line=lineno))
                    entries.append(([(line, source, lineno)], StringList()))
                    in_definition = False
                # second term and following
                else:
                    if was_empty:
                        messages.append(self.state.reporter.warning(
                            _('glossary terms must not be separated by empty lines'),
                            source=source, line=lineno))
                    if entries:
                        entries[-1][0].append((line, source, lineno))
                    else:
                        messages.append(self.state.reporter.warning(
                            _('glossary seems to be misformatted, check indentation'),
                            source=source, line=lineno))
            elif in_comment:
                pass
            else:
                if not in_definition:
                    # first line of definition, determines indentation
                    in_definition = True
                    indent_len = len(line) - len(line.lstrip())
                if entries:
                    entries[-1][1].append(line[indent_len:], source, lineno)
                else:
                    messages.append(self.state.reporter.warning(
                        _('glossary seems to be misformatted, check indentation'),
                        source=source, line=lineno))
            was_empty = False

        # now, parse all the entries into a big definition list
        items = []
        for terms, definition in entries:
            termtexts = []          # type: List[str]
            termnodes = []          # type: List[Node]
            system_messages = []    # type: List[Node]
            for line, source, lineno in terms:
                termtext, classifiers = split_term_classifiers(line)
                # parse the term with inline markup
                # classifiers (parts[1:]) will not be shown on doctree
                textnodes, sysmsg = self.state.inline_text(termtext, lineno)

                # use first classifier as a index key
                index_key = classifiers[0] if classifiers else None
                term = make_glossary_term(self.env, textnodes, index_key, source, lineno, line,
                                          document=self.state.document)
                system_messages.extend(sysmsg)
                termtexts.append(term.astext())
                termnodes.append(term)

            termnodes.extend(system_messages)

            defnode = nodes.definition()
            if definition:
                self.state.nested_parse(definition, definition.items[0][1],
                                        defnode)
            termnodes.append(defnode)
            items.append((termtexts,
                          nodes.definition_list_item('', *termnodes)))

        if 'sorted' in self.options:
            items.sort(key=lambda x:
                       unicodedata.normalize('NFD', x[0][0].lower()))

        dlist = nodes.definition_list()
        dlist['classes'].append('glossary')
        dlist.extend(item[1] for item in items)
        node += dlist
        return messages + [node]


class GlossaryDomain(Domain):
    """Glossary domain."""
    name = 'glossary'
    label = 'glossary'

    @property
    def terms(self) -> Dict[str, Tuple[str, str]]:
        return self.data.setdefault('terms', {})  # term -> (docname, node_id)

    def note_term(self, node: nodes.term) -> None:
        name = node.astext()
        if name in self.terms:
            other = self.terms[name]
            logger.warning(__('duplicate term of glossary %s, other instance in %s') %
                           (name, other), location=node)

        self.terms[name] = (self.env.docname, node['ids'][0])

    def clear_doc(self, docname: str) -> None:
        for name, (doc, node_id) in list(self.terms.items()):
            if doc == docname:
                del self.terms[name]

    def merge_domaindata(self, docnames: Iterable[str], otherdata: Dict) -> None:
        for name, (doc, node_id) in otherdata['terms'].items():
            if doc in docnames:
                self.terms[name] = (doc, node_id)

    def get_objects(self) -> Generator[Tuple[str, str, str, str, str, int], None, None]:
        for name, (docname, node_id) in self.terms.items():
            yield name, name, 'term', docname, node_id, -1


def setup(app: "Sphinx") -> Dict[str, Any]:
    app.add_domain(GlossaryDomain)
    app.add_directive('glossary', Glossary)

    return {
        'version': 'builtin',
        'env_version': 1,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
