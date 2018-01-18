"""
    sphinx.project
    ~~~~~~~~~~~~~~

    Utility function and classes for Sphinx projects.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import os

from sphinx.locale import __
from sphinx.util import get_matching_files
from sphinx.util import logging
from sphinx.util import path_stabilize
from sphinx.util.matching import compile_matchers
from sphinx.util.osutil import SEP, relpath

if False:
    # For type annotation
    from typing import Dict, List, Set, Tuple  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA


logger = logging.getLogger(__name__)
EXCLUDE_PATHS = ['**/_sources', '.#*', '**/.#*', '*.lproj/**']


class Project:
    """A project is source code set of Sphinx document."""

    def __init__(self, srcdir, source_suffix):
        # type: (str, Dict[str, str]) -> None
        #: Source directory.
        self.srcdir = srcdir

        #: source_suffix. Same as :confval:`source_suffix`.
        self.source_suffix = source_suffix

        #: The name of documents belongs to this project.
        self.docnames = set()  # type: Set[str]

    def restore(self, other):
        # type: (Project) -> None
        """Take over a result of last build."""
        self.docnames = other.docnames

    def discover(self, exclude_paths=[]):
        # type: (List[str]) -> Set[str]
        """Find all document files in the source directory and put them in
        :attr:`docnames`.
        """
        self.docnames = set()
        excludes = compile_matchers(exclude_paths + EXCLUDE_PATHS)
        for filename in get_matching_files(self.srcdir, excludes):  # type: ignore
            docname = self.path2doc(filename)
            if docname:
                if os.access(os.path.join(self.srcdir, filename), os.R_OK):
                    self.docnames.add(docname)
                else:
                    logger.warning(__("document not readable. Ignored."), location=docname)

        return self.docnames

    def path2doc(self, filename):
        # type: (str) -> str
        """Return the docname for the filename if the file is document.

        *filename* should be absolute or relative to the source directory.
        """
        if filename.startswith(self.srcdir):
            filename = relpath(filename, self.srcdir)
        for suffix in self.source_suffix:
            if filename.endswith(suffix):
                filename = path_stabilize(filename)
                return filename[:-len(suffix)]

        # the file does not have docname
        return None

    def doc2path(self, docname, basedir=True):
        # type: (str, bool) -> str
        """Return the filename for the document name.

        If *basedir* is True, return as an absolute path.
        Else, return as a relative path to the source directory.
        """
        docname = docname.replace(SEP, os.path.sep)
        basename = os.path.join(self.srcdir, docname)
        for suffix in self.source_suffix:
            if os.path.isfile(basename + suffix):
                break
        else:
            # document does not exist
            suffix = list(self.source_suffix)[0]

        if basedir:
            return basename + suffix
        else:
            return docname + suffix

    def get_outdated_docs(self, env, force_update=False):
        # type: (BuildEnvironment, bool) -> Tuple[Set[str], Set[str], Set[str]]
        """Detect added, changed and removed documents since last build.

        Return (added, changed, removed) sets.
        """
        added = set()  # type: Set[str]
        changed = set()  # type: Set[str]
        removed = set(env.all_docs) - self.docnames

        if force_update:
            # On force update, all documents are considered as added.
            # (e.g. config values changed)
            added = self.docnames
        else:
            for docname in self.docnames:
                # new file
                if docname not in env.all_docs:
                    added.add(docname)
                    continue

                # if the doctree file is not there, rebuild
                doctree = os.path.join(env.doctreedir, docname + '.doctree')
                if not os.path.isfile(doctree):
                    changed.add(docname)
                    continue

                # check the "reread always" list
                if docname in env.reread_always:
                    changed.add(docname)
                    continue

                # check the mtime of the document
                mtime = env.all_docs[docname]
                newmtime = os.path.getmtime(self.doc2path(docname))
                if newmtime > mtime:
                    changed.add(docname)
                    continue

                # finally, check the mtime of dependencies
                for dep in env.dependencies[docname]:
                    try:
                        # this will do the right thing when dep is absolute too
                        deppath = os.path.join(self.srcdir, dep)
                        if not os.path.isfile(deppath):
                            changed.add(docname)
                            break

                        depmtime = os.path.getmtime(deppath)
                        if depmtime > mtime:
                            changed.add(docname)
                            break
                    except OSError:
                        # give it another chance
                        changed.add(docname)
                        break

        return added, changed, removed
