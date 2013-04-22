
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the bigmess package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Generate table of contents pages for packages sort by various criteria.

"""

__docformat__ = 'restructuredtext'

# magic line for manpage summary
# man: -*- % generate package table of contents pages

import argparse
import os
import re
import logging
import codecs

from os.path import join as opj

from bigmess import cfg
from .helpers import parser_add_common_args
from ..utils import load_db

lgr = logging.getLogger(__name__)
parser_args = dict(formatter_class=argparse.RawDescriptionHelpFormatter)


def setup_parser(parser):
    parser_add_common_args(parser, opt=('pkgdb',))
    parser.add_argument('-d', '--dest-dir', default=os.curdir,
                        help="""target directory for storing the generated pages""")


def _write_page(page, destdir, fname):
    of = codecs.open(opj(destdir, '%s.rst' % fname), 'wb', 'utf-8')
    of.write(page)
    of.close()


def run(args):
    from jinja2 import Environment as JinjaEnvironment
    from jinja2 import PackageLoader as JinjaPackageLoader
    lgr.debug("using package DB at '%s'" % args.pkgdb)
    # read entire DB
    db = load_db(args.pkgdb)
    bindb = db['bin']
    srcdb = db['src']
    taskdb = db['task']
    by_release = {}
    by_maintainer = {}
    maintainer_name = {}
    by_task = {}
    for pname, pkg in db['bin'].iteritems():
        for release in pkg['in_release']:
            by_release[release] = by_release.get(release, list()) + [pname]
        src_name = pkg['src_name']
        if 'upstream' in srcdb[src_name] and 'Tags' in srcdb[src_name]['upstream']:
            # we have some tags
            for tag in srcdb[src_name]['upstream']['Tags']:
                if tag.startswith('task::'):
                    task = tag[6:]
                    by_task[task] = by_task.get(task, list()) + [pname]
        maintainer = srcdb[pkg['src_name']]['maintainer']
        uploaders = [u.strip() for u in srcdb[src_name]['uploaders'].split(',')]
        for maint in uploaders + [maintainer]:
            if not len(maint.strip()):
                continue
            try:
                mname, memail = re.match(r'(.*) <(.*)>', maint).groups()
            except AttributeError:
                lgr.warning('malformed maintainer listing for %s: %s' % (pname, maint))
                mname = memail = maint
            # normalize
            memail = memail.lower()
            maintainer_name[memail] = mname
            by_maintainer[memail] = by_maintainer.get(memail, set()).union((src_name,))
        # XXX extend when blend is ready

    # write TOCs for all releases
    jinja_env = JinjaEnvironment(loader=JinjaPackageLoader('bigmess'))
    bintoc_template = jinja_env.get_template('binpkg_toc.rst')
    toctoc = {'release': {}, 'maintainer': {}, 'field': {}}
    release_tocs = toctoc['release']
    for release_name, release_content in by_release.iteritems():
        label = 'toc_pkgs_for_release_%s' % release_name
        title = 'Packages for %s' % cfg.get('release names', release_name)
        release_tocs[label] = title
        page = bintoc_template.render(label=label,
                                      title=title,
                                      pkgs=release_content,
                                      db=bindb)
        _write_page(page, args.dest_dir, label)
    task_tocs = toctoc['field']
    for task_name, task_content in by_task.iteritems():
        label = 'toc_pkgs_for_field_%s' % task_name
        title = 'Packages for %s' % taskdb[task_name]
        task_tocs[label] = title
        page = bintoc_template.render(label=label,
                                      title=title,
                                      pkgs=set(task_content),
                                      db=bindb)
        _write_page(page, args.dest_dir, label)
    # full TOC
    _write_page(bintoc_template.render(label='toc_all_pkgs',
                                       title='Complete package list',
                                       pkgs=bindb.keys(),
                                       db=bindb),
                args.dest_dir,
                'toc_all_pkgs')
    # TOC by maintainer
    srctoc_template = jinja_env.get_template('srcpkg_toc.rst')
    maintainer_tocs = toctoc['maintainer']
    for memail, mpkgs in by_maintainer.iteritems():
        label = 'toc_pkgs_for_maintainer_%s' % memail.replace('@', '_at_')
        title = 'Packages made by %s <%s>' % (maintainer_name[memail], memail)
        maintainer_tocs[label] = title
        page = srctoc_template.render(
            label=label,
            title=title,
            pkgs=mpkgs,
            srcdb=srcdb,
            bindb=bindb)
        _write_page(page, args.dest_dir, label)

    # TOC of TOCs
    toctoc_template = jinja_env.get_template('pkg_tocs.rst')
    print codecs.encode(toctoc_template.render(toctoc=toctoc), 'utf-8')
