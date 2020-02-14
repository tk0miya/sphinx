"""
    test_domain_index
    ~~~~~~~~~~~~~~~~~

    Tests for index domain.

    :copyright: Copyright 2007-2020 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from docutils import nodes

from sphinx import addnodes
from sphinx.testing import restructuredtext
from sphinx.testing.util import assert_node


def test_index_directive(app):
    text = (".. index:: keyword\n"
            "   pair: Sphinx; document\n")
    doctree = restructuredtext.parse(app, text)
    assert_node(doctree, (addnodes.index,
                          nodes.target))
    assert_node(doctree[0], addnodes.index,
                entries=[("single", "keyword", "index-0", "", None),
                         ("pair", "Sphinx; document", "index-0", "", None)])
    assert_node(doctree[1], nodes.target, ids=["index-0"], names=[])


def test_name_for_index_directive(app):
    text = (".. index:: keyword\n"
            "   pair: Sphinx; document\n"
            "   :name: mykwd")
    doctree = restructuredtext.parse(app, text)
    assert_node(doctree, (addnodes.index,
                          nodes.target))
    assert_node(doctree[0], addnodes.index,
                entries=[("single", "keyword", "index-0", "", None),
                         ("pair", "Sphinx; document", "index-0", "", None)])
    assert_node(doctree[1], nodes.target, ids=["index-0"], names=["mykwd"])
