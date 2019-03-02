"""
    test_directive_glossary
    ~~~~~~~~~~~~~~~~~~~~~~~

    Test the glossary directive.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import pytest
from docutils import nodes
from docutils.core import publish_doctree

from sphinx import addnodes
from sphinx.io import SphinxStandaloneReader
from sphinx.parsers import RSTParser
from sphinx.testing.util import assert_node
from sphinx.util.docutils import sphinx_domains


def parse(app, docname, text):
    app.env.temp_data['docname'] = docname
    with sphinx_domains(app.env):
        parser = RSTParser()
        parser.set_application(app)
        return publish_doctree(text, app.srcdir / docname + '.rst',
                               reader=SphinxStandaloneReader(app),
                               parser=parser,
                               settings_overrides={'env': app.env,
                                                   'gettext_compact': True})


@pytest.mark.sphinx(testroot='basic')
def test_glossary(app, status, warning):
    text = ('.. glossary::\n'
            '\n'
            '   term1\n'
            '   term2\n'
            '       description\n'
            '   term3 : classifier\n'
            '       description\n'
            '       description\n'
            '   term4 : class1 : class2\n'
            '       description\n')

    # doctree
    doctree = parse(app, 'index', text)
    assert_node(doctree, [nodes.document, addnodes.glossary, nodes.definition_list,
                          (nodes.definition_list_item,
                           nodes.definition_list_item,
                           nodes.definition_list_item)])
    assert_node(doctree[0][0][0], ([nodes.term, ("term1",
                                                 addnodes.index)],
                                   [nodes.term, ("term2",
                                                 addnodes.index)],
                                   [nodes.definition, nodes.paragraph, "description"]))
    assert_node(doctree[0][0][1], ([nodes.term, ("term3",
                                                 addnodes.index)],
                                   [nodes.definition, nodes.paragraph, ("description\n"
                                                                        "description")]))
    assert_node(doctree[0][0][1][0][1],
                entries=[('single', 'term3', 'term-term3', 'main', 'classifier')])
    assert_node(doctree[0][0][2], ([nodes.term, ("term4",
                                                 addnodes.index)],
                                   [nodes.definition, nodes.paragraph, "description"]))
    assert_node(doctree[0][0][2][0][1],
                entries=[('single', 'term4', 'term-term4', 'main', 'class1')])

    # index
    objects = list(app.env.get_domain('std').get_objects())
    assert ('term1', 'term1', 'term', 'index', 'term-term1', -1) in objects
    assert ('term2', 'term2', 'term', 'index', 'term-term2', -1) in objects
    assert ('term3', 'term3', 'term', 'index', 'term-term3', -1) in objects
    assert ('term4', 'term4', 'term', 'index', 'term-term4', -1) in objects
