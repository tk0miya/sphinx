# -*- coding: utf-8 -*-
"""
    test_ext_autodoc_inspector
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Test the autodoc extension.

    :copyright: Copyright 2007-2017 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import sys

import pytest

from sphinx.ext.autodoc.inspector import import_module


@pytest.fixture(scope='function')
def setup_sys_path(rootdir):
    try:
        sys.path.append(rootdir / 'test-ext-autodoc-inspector')
        yield
    finally:
        sys.path.pop()


def test_import_module():
    env = import_module('sphinx.environment')
    assert env
    assert env.parent is None
    assert env.name == 'sphinx.environment'
    assert env.fullname == 'sphinx.environment'
    assert env.type == 'module'
    assert env.module == env

    default_settings = env.get_members().get('default_settings')
    assert default_settings
    assert default_settings.parent == env
    assert default_settings.name == 'default_settings'
    assert default_settings.fullname == 'sphinx.environment.default_settings'
    assert default_settings.type == 'attribute'
    assert default_settings.get_members() == {}
    assert default_settings.module == env

    logging = env.get_members().get('logging')
    assert logging
    assert logging.parent == env
    assert logging.name == 'logging'
    assert logging.fullname == 'sphinx.environment.logging'
    assert logging.type == 'module'
    assert logging.module == logging

    BuildEnvironment = env.get_members().get('BuildEnvironment')
    assert BuildEnvironment
    assert BuildEnvironment.parent == env
    assert BuildEnvironment.name == 'BuildEnvironment'
    assert BuildEnvironment.fullname == 'sphinx.environment.BuildEnvironment'
    assert BuildEnvironment.type == 'class'
    assert BuildEnvironment.module == env

    # class variable
    domains = BuildEnvironment.get_members().get('domains')
    assert domains
    assert domains.parent == BuildEnvironment
    assert domains.name == 'domains'
    assert domains.fullname == 'sphinx.environment.BuildEnvironment.domains'
    assert domains.type == 'attribute'
    assert domains.get_members() == {}
    assert domains.module == env

    # instance variable
    app = BuildEnvironment.get_members().get('app')
    assert app
    assert app.parent == BuildEnvironment
    assert app.name == 'app'
    assert app.fullname == 'sphinx.environment.BuildEnvironment.app'
    assert app.type == 'attribute'
    assert app.get_members() == {}
    assert app.module == env

    # method
    update = BuildEnvironment.get_members().get('update')
    assert update
    assert update.parent == BuildEnvironment
    assert update.name == 'update'
    assert update.fullname == 'sphinx.environment.BuildEnvironment.update'
    assert update.type == 'method'
    assert update.get_members() == {}
    assert update.module == env


def test_import_shared_library():
    io = import_module('_io')
    assert io
    assert io.parent is None
    assert io.name == '_io'
    assert io.fullname == '_io'
    assert io.type == 'module'

    StringIO = io.get_members().get('StringIO')
    assert StringIO
    assert StringIO.parent == io
    assert StringIO.name == 'StringIO'
    assert StringIO.fullname == '_io.StringIO'
    assert StringIO.type == 'class'

    read = StringIO.get_members().get('read')
    assert read
    assert read.parent == StringIO
    assert read.name == 'read'
    assert read.fullname == '_io.StringIO.read'
    assert read.type == 'method'
    assert read.get_members() == {}


@pytest.mark.usefixtures('setup_sys_path')
def test_invalid_all_definition(app, status, warning):
    module = import_module('invalid_all')

    Foo = module.get_members().get('Foo')
    assert Foo
    assert Foo.is_public

    bar = module.get_members().get('bar')
    assert bar
    assert bar.is_public

    assert '__all__ should be a list of strings, not True' in warning.getvalue()


@pytest.mark.usefixtures('setup_sys_path')
def test_all_definition():
    module = import_module('all')

    Foo = module.get_members().get('Foo')
    assert Foo
    assert Foo.is_public

    bar = module.get_members().get('bar')
    assert bar
    assert not bar.is_public


@pytest.mark.usefixtures('setup_sys_path')
def test_method_types():
    module = import_module('method_types')

    Foo = module.get_members().get('Foo')
    assert Foo
    assert Foo.type == 'class'

    class_method = Foo.get_members().get('class_method')
    assert class_method
    assert class_method.type == 'method'
    assert class_method.method_type == 'classmethod'

    static_method = Foo.get_members().get('static_method')
    assert static_method
    assert static_method.type == 'method'
    assert static_method.method_type == 'staticmethod'

    method = Foo.get_members().get('method')
    assert method
    assert method.type == 'method'
    assert method.method_type == 'method'


@pytest.mark.usefixtures('setup_sys_path')
def test_enum():
    module = import_module('enums')

    Color = module.get_members().get('Color')
    assert Color
    assert Color.type == 'class'

    RED = Color.get_members().get('RED')
    assert RED
    assert RED.type == 'attribute'
    assert RED.inherited_member is False


@pytest.mark.usefixtures('setup_sys_path')
def test_inherited():
    module = import_module('inherited')

    Bar = module.get_members().get('Bar')
    assert Bar
    assert Bar.type == 'class'

    __init__ = Bar.get_members().get('__init__')
    assert __init__
    assert __init__.type == 'method'
    assert __init__.inherited_member is True

    say = Bar.get_members().get('say')
    assert say
    assert say.type == 'method'
    assert say.inherited_member is True

    hello = Bar.get_members().get('hello')
    assert hello
    assert hello.type == 'method'
    assert hello.inherited_member is False

    world = Bar.get_members().get('world')
    assert world
    assert world.type == 'method'
    assert world.inherited_member is False
