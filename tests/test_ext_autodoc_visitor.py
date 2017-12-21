# -*- coding: utf-8 -*-
"""
    test_ext_autodoc_visitor
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Test the autodoc extension.

    :copyright: Copyright 2007-2017 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import sys

import pytest

from sphinx.ext.autodoc.inspector import import_module
from sphinx.ext.autodoc.visitor import AutodocVisitor


@pytest.fixture(scope='function')
def setup_sys_path(rootdir):
    try:
        sys.path.append(rootdir / 'test-ext-autodoc-inspector')
        yield
    finally:
        sys.path.pop()


@pytest.mark.usefixtures('setup_sys_path')
def test_AutodocVisitor_function():
    visitor = AutodocVisitor()
    module = import_module('all')
    func = module.get_members().get('bar')
    func.walk(visitor)
    assert visitor.result.data == ['',
                                   '.. py:function:: bar(name)',
                                   '']


@pytest.mark.usefixtures('setup_sys_path')
def test_AutodocVisitor_class():
    visitor = AutodocVisitor()
    module = import_module('all')
    func = module.get_members().get('Foo')
    func.walk(visitor)
    assert '.. py:class:: Foo' in visitor.result.data

    # in this test, we picked up only few methods and attributes
    # because they are different between py2 and py3.
    assert '   .. py:method:: __hash__()' in visitor.result.data
    assert '   .. py:attribute:: __module__' in visitor.result.data
    assert '   .. py:class:: __class__' in visitor.result.data
    assert '      alias of :class:`type`' in visitor.result.data
