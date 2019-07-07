"""
    sphinx.domains.glossary
    ~~~~~~~~~~~~~~~~~~~~~~~

    The glossary domain.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from typing import Any, Dict, Iterable, List

from sphinx.domains import Domain
from sphinx.locale import __
from sphinx.util import logging

if False:
    # For type annotation
    from sphinx.application import Sphinx


logger = logging.getLogger(__name__)


class GlossaryDomain(Domain):
    """Glossary domain."""
    name = 'glossary'
    label = 'glossary'

    @property
    def terms(self) -> Dict[str, str]:
        return self.data.setdefault('terms', {})  # term -> docname

    def note_term(self, name: str, location: Any = None) -> None:
        if name in self.terms:
            other = self.equations[name]
            logger.warning(__('duplicate term of glossary %s, other instance in %s') %
                           (name, other), location=location)

        self.terms[name] = self.env.docname

    def clear_doc(self, docname: str) -> None:
        for name, doc in list(self.terms.items()):
            if doc == docname:
                del self.terms[name]

    def merge_domaindata(self, docnames: Iterable[str], otherdata: Dict) -> None:
        for name, doc in otherdata['terms'].items():
            if doc in docnames:
                self.terms[name] = doc

    def get_objects(self) -> List:
        return []


def setup(app: "Sphinx") -> Dict[str, Any]:
    app.add_domain(GlossaryDomain)

    return {
        'version': 'builtin',
        'env_version': 1,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
