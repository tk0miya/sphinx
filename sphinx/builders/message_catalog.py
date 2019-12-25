from os import path
from typing import List, Set

from sphinx.builders import Builder
from sphinx.locale import __
from sphinx.util import logging
from sphinx.util import SEP, status_iterator
from sphinx.util.console import bold
from sphinx.util.i18n import CatalogInfo, CatalogRepository, docname_to_domain
from sphinx.util.osutil import relpath


logger = logging.getLogger(__name__)


class MessageCatalogCompiler(Builder):
    """Compile message catalogs (.po files) to binary form (.mo files) on building document.

    This class behaves like a "Builder".
    """
    def compile_catalogs(self, catalogs: Set[CatalogInfo], message: str) -> None:
        if not self.config.gettext_auto_build:
            return

        def cat2relpath(cat: CatalogInfo) -> str:
            return relpath(cat.mo_path, self.env.srcdir).replace(path.sep, SEP)

        logger.info(bold(__('building [mo]: ')) + message)
        for catalog in status_iterator(catalogs, __('writing output... '), "darkgreen",
                                       len(catalogs), self.app.verbosity,
                                       stringify_func=cat2relpath):
            catalog.write_mo(self.config.language)

    def build_all(self) -> None:
        repo = CatalogRepository(self.srcdir, self.config.locale_dirs,
                                 self.config.language, self.config.source_encoding)
        message = __('all of %d po files') % len(list(repo.catalogs))
        self.compile_catalogs(set(repo.catalogs), message)

    def build_specific(self, filenames: List[str]) -> None:
        def to_domain(fpath: str) -> str:
            docname = self.env.path2doc(path.abspath(fpath))
            if docname:
                return docname_to_domain(docname, self.config.gettext_compact)
            else:
                return None

        catalogs = set()
        domains = set(map(to_domain, filenames))
        repo = CatalogRepository(self.srcdir, self.config.locale_dirs,
                                 self.config.language, self.config.source_encoding)
        for catalog in repo.catalogs:
            if catalog.domain in domains and catalog.is_outdated():
                catalogs.add(catalog)
        message = __('targets for %d po files that are specified') % len(catalogs)
        self.compile_catalogs(catalogs, message)

    def build_update(self) -> None:
        repo = CatalogRepository(self.srcdir, self.config.locale_dirs,
                                 self.config.language, self.config.source_encoding)
        catalogs = {c for c in repo.catalogs if c.is_outdated()}
        message = __('targets for %d po files that are out of date') % len(catalogs)
        self.compile_catalogs(catalogs, message)
