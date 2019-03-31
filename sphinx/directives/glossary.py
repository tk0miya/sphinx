"""
    sphinx.directives.glossary
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    The glossary directive.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re
import unicodedata
from typing import cast

from docutils import nodes
from docutils.parsers.rst import directives
from docutils.parsers.rst.states import Body, RSTState, RSTStateMachine, SpecializedText
from docutils.statemachine import StringList

from sphinx import addnodes
from sphinx.locale import _
from sphinx.util.docutils import NullReporter, SphinxDirective, new_document

if False:
    # For type annotation
    from typing import Iterable, List, Match, Tuple, Union  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA


def split_term_classifiers(line):
    # type: (str) -> List[Union[str, None]]
    # split line into a term and classifiers. if no classifier, None is used..
    parts = re.split(' +: +', line) + [None]
    return parts


def make_glossary_term(env, textnodes, index_key, source, lineno, new_id=None):
    # type: (BuildEnvironment, Iterable[nodes.Node], str, str, int, str) -> nodes.term
    from sphinx.domains.std import StandardDomain

    # get a text-only representation of the term and register it
    # as a cross-reference target
    term = nodes.term('', '', *textnodes)
    term.source = source
    term.line = lineno

    gloss_entries = env.temp_data.setdefault('gloss_entries', set())
    termtext = term.astext()
    if new_id is None:
        new_id = nodes.make_id('term-' + termtext)
    if new_id in gloss_entries:
        new_id = 'term-' + str(len(gloss_entries))
    gloss_entries.add(new_id)

    std = cast(StandardDomain, env.get_domain('std'))
    std.add_object('term', termtext.lower(), env.docname, new_id)

    # add an index entry too
    indexnode = addnodes.index()
    indexnode['entries'] = [('single', termtext, new_id, 'main', index_key)]
    indexnode.source, indexnode.line = term.source, term.line
    term.append(indexnode)
    term['ids'].append(new_id)
    term['names'].append(new_id)

    return term


class GlossaryParser:
    class Glossary(SpecializedText):
        patterns = {'comment': r'\.\.( +|$)',
                    'text': r''}
        initial_transitions = [('comment', 'Comment'),
                               ('text', 'Body')]

        def text(self, match, context, next_state):
            # type: (Match, List[str], str) -> Tuple[List[str], str, List[str]]
            context.append(match.string)
            return context, 'Term', []

        def comment(self, match, context, next_state):
            return [], 'Glossary', []

    class Term(SpecializedText):
        def text(self, match, context, next_state):
            # type: (Match, List[str], str) -> Tuple[List[str], str, List[str]]
            context.append(match.string)
            indented, indent, line_offset, blank_finish = self.state_machine.get_indented()
            return context, 'Term', []

        def indent(self, match, context, next_state):
            # type: (Match, List[str], str) -> Tuple[List[str], str, List[str]]
            item = nodes.definition_list_item()
            for term in context:
                item += nodes.term(term, term)
            indented, indent, line_offset, blank_finish = self.state_machine.get_indented()
            item += nodes.definition()
            self.nested_parse(indented, input_offset=line_offset, node=item[-1])
            self.parent += item
            return [], 'Glossary', []

        def blank(self, match, context, next_state):
            # type: (Match, List[str], str) -> Tuple[List[str], str, List[str]]
            if context:
                item = nodes.definition_list_item()
                for term in context:
                    item += nodes.term(term, term)
                self.parent += item
            return [], 'Glossary', []

    def __init__(self, env, state):
        # type: (BuildEnvironment, RSTState) -> None
        self.env = env
        self.state = state

    def parse(self, content):
        # type: (StringList) -> List[nodes.Node]
        state_classes = (self.Glossary, self.Term)
        state_machine = RSTStateMachine(state_classes, 'Glossary')
        node = new_document('', self.state.document.settings)
        node.reporter = NullReporter()
        state_machine.run(content, node)
        return node.children


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

    def run(self):
        # type: () -> List[nodes.Node]
        items, messages = self.parse(self.content)
        #items = self.build(entries)

        node = addnodes.glossary()
        node.document = self.state.document
        node += nodes.definition_list(classes=['glossary'])
        node[0].extend(items)
        print(node)
        return messages + [node]

    def parse(self, content):
        parser = GlossaryParser(self.env, self.state)
        doctree = parser.parse(content)
        for node in doctree.traverse(nodes.term):
            pass

        return doctree, []

    def parse2(self, content):
        # type: (StringList) -> Tuple[List[Tuple[Tuple[str, str, int]], StringList], List[nodes.Node]]  # NOQA
        """Parse definition list on content.

        This directive implements a custom format of the reST definition list
        that allows multiple lines of terms before the definition.  This is
        easy to parse since we know that the contents of the glossary *must
        be* a definition list.
        """
        entries = []  # type: List[Tuple[List[Tuple[str, str, int]], StringList]]
        in_definition = True
        was_empty = True
        messages = []  # type: List[nodes.Node]
        for source, lineno, line in content.xitems():
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
                    continue
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

        return entries, messages

    def build(self, entries):
        # type: (List[Tuple[List[Tuple[str, str, int]], StringList]]) -> List[nodes.Node]
        """Parse all the entries and build a definition list."""
        items = []
        for terms, definition in entries:
            termtexts = []          # type: List[str]
            termnodes = []          # type: List[nodes.Node]
            system_messages = []    # type: List[nodes.Node]
            for line, source, lineno in terms:
                parts = split_term_classifiers(line)
                # parse the term with inline markup
                # classifiers (parts[1:]) will not be shown on doctree
                textnodes, sysmsg = self.state.inline_text(parts[0], lineno)

                # use first classifier as a index key
                term = make_glossary_term(self.env, textnodes, parts[1], source, lineno)
                term.rawsource = line
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

        return [item[1] for item in items]
