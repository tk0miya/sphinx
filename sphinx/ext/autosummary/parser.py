"""
    sphinx.ext.autosummary.parser
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import functools
from collections import defaultdict
from types import ModuleType
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

from docutils import nodes
from docutils.core import publish_doctree
from docutils.nodes import Node, system_message
from docutils.parsers.rst import Parser
from docutils.parsers.rst import Directive, directives, roles
from docutils.readers import Reader
from docutils.transforms import Transform
from docutils.utils import Reporter

from sphinx.util.docutils import SphinxRole
from sphinx.util.typing import RoleFunction


class Autosummary(Directive):
    def run(self) -> List[Node]:
        print(self.content)
        print(self.options)
        return []


class Automodule(Directive):
    pass


class Currentmodule(Directive):
    pass


class NoopDirective(Directive):
    optional_arguments = 999

    def run(self) -> List[Node]:
        print(self.name)
        print(self.content)
        print(self.options)
        print(self.arguments)
        return []


class NoopRole(SphinxRole):
    def run(self) -> Tuple[List[Node], List[system_message]]:
        return [], []


class autosummary_directives:
    """Monkey-patch directive and role dispatch, so that domain-specific
    markup takes precedence.
    """
    directives = defaultdict(lambda: NoopDirective,
                             autosummary=Autosummary,
                             autodmodule=Automodule,
                             currentmodule=Currentmodule,
                             module=Currentmodule)  # type: Dict[str, Type[Directive]]

    def __init__(self) -> None:
        self.original_directive = None  # type: Callable
        self.original_role = None  # type: Callable

    def __enter__(self) -> None:
        self.enable()

    def __exit__(self, exc_type: Type[Exception], exc_value: Exception, traceback: Any) -> bool:  # NOQA
        self.disable()
        return True

    def __call__(self, f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            with self:
                return f(*args, **kwargs)

        return wrapper

    def enable(self) -> None:
        self.original_directive = directives.directive
        self.original_role = roles.role

        directives.directive = self.directive
        roles.role = self.role

    def disable(self) -> None:
        directives.directive = self.original_directive
        roles.role = self.original_role

    def directive(self, directive_name: str, language_module: ModuleType, document: nodes.document) -> Tuple[Optional[Type[Directive]], List[system_message]]:  # NOQA
        return NoopDirective(), []

    def role(self, role_name: str, language_module: ModuleType, lineno: int, reporter: Reporter) -> Tuple[RoleFunction, List[system_message]]:  # NOQA
        return NoopRole(), []


class AutosummaryReader(Reader):
    def get_transforms(self) -> List[Type[Transform]]:
        return []


class AutosummaryParser(Parser):
    def get_transforms(self) -> List[Type[Transform]]:
        return []

    @autosummary_directives()
    def parse(self, inputstring: str, document: nodes.document) -> None:
        super().parse(inputstring, document)
        print(document)


def parse(s: str, filename: str) -> nodes.document:
    return publish_doctree(s, filename, reader=AutosummaryReader(), parser=AutosummaryParser())
