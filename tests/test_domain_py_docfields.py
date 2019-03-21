"""
    test_domain_py_docfields
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Tests the Python Domain

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from docutils import nodes

from sphinx import addnodes
from sphinx.addnodes import (
    desc, desc_content, desc_name, desc_parameterlist, desc_signature,
    literal_emphasis, literal_strong, pending_xref
)
from sphinx.testing import restructuredtext
from sphinx.testing.util import assert_node


def test_param_with_arg(app):
    text = (".. py:function:: hello()\n"
            "\n"
            "   :param name: your name")
    doctree = restructuredtext.parse(app, text)
    assert_node(doctree,
                (addnodes.index,
                 [desc, ([desc_signature, ([desc_name, "hello"],
                                           [desc_parameterlist, ()])],
                         [desc_content, nodes.field_list, nodes.field])]))
    assert_node(doctree[1][1][0][0],
                ([nodes.field_name, "Parameters"],
                 [nodes.field_body, nodes.paragraph, ([addnodes.literal_strong, "name"],
                                                      " -- ",
                                                      "your name")]))


def test_param_not_having_arg(app):
    text = (".. py:function:: hello()\n"
            "\n"
            "   :param: your name")
    doctree = restructuredtext.parse(app, text)
    assert_node(doctree,
                (addnodes.index,
                 [desc, ([desc_signature, ([desc_name, "hello"],
                                           [desc_parameterlist, ()])],
                         [desc_content, nodes.field_list, nodes.field])]))
    assert_node(doctree[1][1][0][0],
                ([nodes.field_name, "Param"],
                 [nodes.field_body, nodes.paragraph, "your name"]))


def test_type_with_arg(app):
    text = (".. py:function:: hello()\n"
            "\n"
            "   :type name: str")
    doctree = restructuredtext.parse(app, text)
    assert_node(doctree,
                (addnodes.index,
                 [desc, ([desc_signature, ([desc_name, "hello"],
                                           [desc_parameterlist, ()])],
                         [desc_content, nodes.field_list, ()])]))


def test_type_not_having_arg(app):
    text = (".. py:function:: hello()\n"
            "\n"
            "   :type: str")
    doctree = restructuredtext.parse(app, text)
    assert_node(doctree,
                (addnodes.index,
                 [desc, ([desc_signature, ([desc_name, "hello"],
                                           [desc_parameterlist, ()])],
                         [desc_content, nodes.field_list, nodes.field])]))
    assert_node(doctree[1][1][0][0],
                ([nodes.field_name, "Type"],
                 [nodes.field_body, nodes.paragraph, pending_xref, "str"]))


def test_param_and_type(app):
    text = (".. py:function:: hello()\n"
            "\n"
            "   :param name: your name\n"
            "   :type name: str")
    doctree = restructuredtext.parse(app, text)
    assert_node(doctree,
                (addnodes.index,
                 [desc, ([desc_signature, ([desc_name, "hello"],
                                           [desc_parameterlist, ()])],
                         [desc_content, nodes.field_list, nodes.field])]))
    assert_node(doctree[1][1][0][0],
                ([nodes.field_name, "Parameters"],
                 [nodes.field_body, nodes.paragraph, ([literal_strong, "name"],
                                                      " (",
                                                      [pending_xref, literal_emphasis, "str"],
                                                      ")",
                                                      " -- ",
                                                      "your name")]))


def test_unknown_field(app):
    text = (".. py:function:: hello()\n"
            "\n"
            "   :unknownValue: description for unknown parameter")
    doctree = restructuredtext.parse(app, text)
    assert_node(doctree,
                (addnodes.index,
                 [desc, ([desc_signature, ([desc_name, "hello"],
                                           [desc_parameterlist, ()])],
                         [desc_content, nodes.field_list, nodes.field])]))
    assert_node(doctree[1][1][0][0],
                ([nodes.field_name, "UnknownValue"],
                 [nodes.field_body, nodes.paragraph, "description for unknown parameter"]))
