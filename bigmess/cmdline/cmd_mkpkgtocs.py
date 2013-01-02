
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
from os.path import join as opj
from bigmess import cfg
from .helpers import parser_add_common_args
from ..utils import load_db
import logging
import codecs
from jinja2 import Environment as JinjaEnvironment
from jinja2 import PackageLoader as JinjaPackageLoader
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
    lgr.debug("using package DB at '%s'" % args.pkgdb)
    # read entire DB
    db = load_db(args.pkgdb)
    bindb = db['bin']
    srcdb = db['src']
    by_suite = {}
    by_maintainer = {}
    maintainer_name = {}
    by_field = {}
    for pname, pkg in db['bin'].iteritems():
        for suite in pkg['in_suite']:
            by_suite[suite] = by_suite.get(suite, list()) + [pname]
        src_name = pkg['src_name']
        if 'upstream' in srcdb[src_name] and 'Tags' in srcdb[src_name]['upstream']:
            # we have some tags
            for tag in srcdb[src_name]['upstream']['Tags']:
                if tag.startswith('field::'):
                    field = tag[7:]
                    by_field[field] = by_field.get(field, list()) + [pname]
        maintainer = srcdb[pkg['src_name']]['maintainer']
        uploaders = [u.strip() for u in srcdb[src_name]['uploaders'].split(',')]
        for maint in uploaders + [maintainer]:
            if not len(maint.strip()):
                continue
            try:
                mname, memail = re.match(r'(.*) <(.*)>', maint).groups()
            except AttributeError:
                lgr.warning('malformed maintainer listing for %s: %s' %(pname, maint))
                mname = memail = maint
            # normalize
            memail = memail.lower()
            maintainer_name[memail] = mname
            by_maintainer[memail] = by_maintainer.get(memail, set()).union((src_name,))
        # XXX extend when blend is ready

    # write TOCs for all suites
    jinja_env = JinjaEnvironment(loader=JinjaPackageLoader('bigmess'))
    bintoc_template = jinja_env.get_template('binpkg_toc.rst')
    toctoc = {'suite': {}, 'maintainer': {}, 'field': {}}
    suite_tocs = toctoc['suite']
    for suite_name, suite_content in by_suite.iteritems():
        label = 'toc_pkgs_for_suite_%s' % suite_name
        title = 'Packages for %s' % cfg.get('release names', suite_name)
        suite_tocs[label] = title
        page = bintoc_template.render(
                label=label,
                title=title,
                pkgs=suite_content,
                db=bindb) 
        _write_page(page, args.dest_dir, label)
    field_tocs = toctoc['field']
    for field_name, field_content in by_field.iteritems():
        label = 'toc_pkgs_for_field_%s' % field_name
        title = 'Packages for %s' % field_name
        field_tocs[label] = title
        page = bintoc_template.render(
                label=label,
                title=title,
                pkgs=field_content,
                db=bindb) 
        _write_page(page, args.dest_dir, label)
    # full TOC
    _write_page(bintoc_template.render(
                    label='toc_all_pkgs',
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
