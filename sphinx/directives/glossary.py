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
from docutils.statemachine import StringList

from sphinx import addnodes
from sphinx.util.docutils import SphinxDirective

if False:
    # For type annotation
    from typing import Iterable, List, Tuple, Union  # NOQA
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
        node = addnodes.glossary()
        node.document = self.state.document

        # This directive implements a custom format of the reST definition list
        # that allows multiple lines of terms before the definition.  This is
        # easy to parse since we know that the contents of the glossary *must
        # be* a definition list.

        # first, collect single entries
        entries = []  # type: List[Tuple[List[Tuple[str, str, int]], StringList]]
        in_definition = True
        was_empty = True
        messages = []  # type: List[nodes.Node]
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

        # now, parse all the entries into a big definition list
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

        dlist = nodes.definition_list()
        dlist['classes'].append('glossary')
        dlist.extend(item[1] for item in items)
        node += dlist
        return messages + [node]
