import argparse
import sys
from bump_version import parse_version, stringify_version


def parse_options(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('version', help='A version number (cf. 1.6b0)')
    parser.add_argument('--in-develop', action='store_true')
    parser.add_argument('--beta', action='store_true')
    options = parser.parse_args(argv)
    options.version = parse_version(options.version)
    return options


def main():
    options = parse_options(sys.argv[1:])

    context = {'version': stringify_version(options.version)}
    if options.beta and options.version[4] == 1:  # ex. 2.0.0b1
        context['first_beta'] = True
        context['current_branch'] = 'master'
        context['release_branch'] = '%d.0'
    else:
        context['current_branch'] = '%d.0' % options.version[0]
        context['release_branch'] = context['current_branch']


"""
version = X.Y.Z | X.Y.0b1
version_human = X.Y.Z final | X.Y.0 beta1
next_version = X.Y.Zb0 | X.Y.0b2
next_major_version = X.Y.0b0
"""

"""
* open https://travis-ci.org/sphinx-doc/sphinx/branches and check **{{ current_branch }}** branch is green
* Run ``git fetch; git status`` and check nothing changed
{% if first_beta -%}
* Run ``python setup.py extract_messages``
* Run ``(cd sphinx/locale; tx push -s)``
{% endif -%}
{% if major_release -%}
* Run ``(cd sphinx/locale; tx pull -a -f)``
* Run ``python setup.py compile_catalog``
* Run ``git add sphinx``
* Run ``git commit -am 'Update message catalogs'``
{% endif -%}
* ``python utils/bump_version.py {{ version }}``
* Check diff by ``git diff``
* Edit CHANGES if empty section exists
* ``git commit -am 'Bump to {{ version_human }}'``
* ``make clean``
* ``python setup.py release bdist_wheel sdist``
* ``twine check dist/Sphinx-{{ version }}*``
* ``twine upload dist/Sphinx-{{ version }}* --sign --identity [your GPG key]``
* open https://pypi.org/project/Sphinx/ and check there are no obvious errors
* ``git tag v{{ version }}``
* ``python utils/bump_version.py --in-develop {{ next_version }}``
* Check diff by ``git diff``
* ``git commit -am 'Bump version'``
{% if first_beta -%}
* ``git checkout -b {{ release_branch }}``
{% endif -%}
* ``git push origin {{ release_branch }} --tags``

* ``git checkout master``
* ``git merge {{ release_branch }}``
{% if first_beta -%}
* ``python utils/bump_version.py --in-develop {{ next_major_version }}``
* Check diff by ``git diff``
* ``git commit -am 'Bump version'``
{% endif -%}
* ``git push origin master``
* Add new version/milestone to tracker categories
{% if first_beta -%}
* open https://github.com/sphinx-doc/sphinx/settings/branches and make ``{{ release_branch }}`` branch protected
{% endif -%}
{% if major_release -%}
* open https://github.com/sphinx-doc/sphinx/settings/branches and make ``{{ oldstable_branch }}`` branch *not* protected
* ``git checkout {{ oldstable_branch }}``
* Run ``git tag {{ oldstable_branch }}`` to paste a tag instead branch
* Run ``git push origin :{{ oldstable_branch }} --tags`` to remove old stable branch
* open https://readthedocs.org/dashboard/sphinx/versions/ and enable the released version
{% endif -%}
* Write announcement and send to sphinx-dev, sphinx-users and python-announce
"""


if __name__ == '__main__':
    main()
