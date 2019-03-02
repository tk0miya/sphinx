"""
    test_directive_glossary
    ~~~~~~~~~~~~~~~~~~~~~~~

    Test the glossary directive.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import pytest
from docutils import nodes
from docutils.nodes import definition, definition_list, definition_list_item, term

from sphinx.addnodes import glossary, index
from sphinx.testing import restructuredtext
from sphinx.testing.util import assert_node


@pytest.mark.sphinx(testroot='basic')
def test_glossary(app):
    text = (".. glossary::\n"
            "\n"
            "   term1\n"
            "   term2\n"
            "       description\n"
            "\n"
            "   term3 : classifier\n"
            "       description\n"
            "       description\n"
            "\n"
            "   term4 : class1 : class2\n"
            "       description\n")

    # doctree
    doctree = restructuredtext.parse(app, text)
    assert_node(doctree, (
        [glossary, definition_list, ([definition_list_item, ([term, ("term1",
                                                                     index)],
                                                             [term, ("term2",
                                                                     index)],
                                                             definition)],
                                     [definition_list_item, ([term, ("term3",
                                                                     index)],
                                                             definition)],
                                     [definition_list_item, ([term, ("term4",
                                                                     index)],
                                                             definition)])],
    ))
    assert_node(doctree[0][0][0][0][1],
                entries=[("single", "term1", "term-term1", "main", None)])
    assert_node(doctree[0][0][0][1][1],
                entries=[("single", "term2", "term-term2", "main", None)])
    assert_node(doctree[0][0][0][2],
                [definition, nodes.paragraph, "description"])
    assert_node(doctree[0][0][1][0][1],
                entries=[("single", "term3", "term-term3", "main", "classifier")])
    assert_node(doctree[0][0][1][1],
                [definition, nodes.paragraph, ("description\n"
                                               "description")])
    assert_node(doctree[0][0][2][0][1],
                entries=[("single", "term4", "term-term4", "main", "class1")])
    assert_node(doctree[0][0][2][1],
                [definition, nodes.paragraph, "description"])

    # index
    objects = list(app.env.get_domain("std").get_objects())
    assert ("term1", "term1", "term", "index", "term-term1", -1) in objects
    assert ("term2", "term2", "term", "index", "term-term2", -1) in objects
    assert ("term3", "term3", "term", "index", "term-term3", -1) in objects
    assert ("term4", "term4", "term", "index", "term-term4", -1) in objects


@pytest.mark.sphinx(testroot='basic')
def test_glossary_warning(app, status, warning):
    # empty line between terms
    text = (".. glossary::\n"
            "\n"
            "   term1\n"
            "\n"
            "   term2\n")
    restructuredtext.parse(app, text, "case1")
    assert ("case1.rst:4: WARNING: glossary terms must not be separated by empty lines"
            in warning.getvalue())

    # glossary starts with indented item
    text = (".. glossary::\n"
            "\n"
            "       description\n"
            "   term\n")
    restructuredtext.parse(app, text, "case2")
    assert ("case2.rst:3: WARNING: glossary term must be preceded by empty line"
            in warning.getvalue())

    # empty line between terms
    text = (".. glossary::\n"
            "\n"
            "   term1\n"
            "       description\n"
            "   term2\n")
    restructuredtext.parse(app, text, "case3")
    assert ("case3.rst:4: WARNING: glossary term must be preceded by empty line"
            in warning.getvalue())


@pytest.mark.sphinx(testroot='basic')
def test_glossary_comment(app):
    text = (".. glossary::\n"
            "\n"
            "   term1\n"
            "       description\n"
            "   .. term2\n"
            "       description\n"
            "       description\n")
    doctree = restructuredtext.parse(app, text)
    assert_node(doctree, (
        [glossary, definition_list, definition_list_item, ([term, ("term1",
                                                                   index)],
                                                           definition)],
    ))
    assert_node(doctree[0][0][0][1],
                [definition, nodes.paragraph, "description"])


@pytest.mark.sphinx(testroot='basic')
def test_glossary_comment2(app):
    text = (".. glossary::\n"
            "\n"
            "   term1\n"
            "       description\n"
            "\n"
            "   .. term2\n"
            "   term3\n"
            "       description\n"
            "       description\n")
    doctree = restructuredtext.parse(app, text)
    assert_node(doctree, (
        [glossary, definition_list, ([definition_list_item, ([term, ("term1",
                                                                     index)],
                                                             definition)],
                                     [definition_list_item, ([term, ("term3",
                                                                     index)],
                                                             definition)])],
    ))
    assert_node(doctree[0][0][0][1],
                [definition, nodes.paragraph, "description"])
    assert_node(doctree[0][0][1][1],
                [definition, nodes.paragraph, ("description\n"
                                                     "description")])


@pytest.mark.sphinx(testroot='basic')
def test_glossary_sorted(app):
    text = (".. glossary::\n"
            "   :sorted:\n"
            "\n"
            "   term3\n"
            "       description\n"
            "\n"
            "   term2\n"
            "   term1\n"
            "       description\n")
    doctree = restructuredtext.parse(app, text)
    assert_node(doctree, (
        [glossary, definition_list, ([definition_list_item, ([term, ("term2",
                                                                     index)],
                                                             [term, ("term1",
                                                                     index)],
                                                             definition)],
                                     [definition_list_item, ([term, ("term3",
                                                                     index)],
                                                             definition)])],
    ))
    assert_node(doctree[0][0][0][2],
                [definition, nodes.paragraph, "description"])
    assert_node(doctree[0][0][1][1],
                [definition, nodes.paragraph, "description"])


@pytest.mark.sphinx(testroot='basic')
def test_glossary_alphanumeric(app):
    text = (".. glossary::\n"
            "\n"
            "   1\n"
            "   /\n")
    restructuredtext.parse(app, text)
    objects = list(app.env.get_domain("std").get_objects())
    assert ("1", "1", "term", "index", "term-1", -1) in objects
    assert ("/", "/", "term", "index", "term-0", -1) in objects


@pytest.mark.sphinx(testroot='basic')
def test_glossary_conflicted_labels(app):
    text = (".. _term-foo:\n"
            ".. glossary::\n"
            "\n"
            "   foo\n")
    restructuredtext.parse(app, text)
    objects = list(app.env.get_domain("std").get_objects())
    assert ("foo", "foo", "term", "index", "term-0", -1) in objects
