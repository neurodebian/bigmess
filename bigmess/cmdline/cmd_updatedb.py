# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the bigmess package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Update package info DB.

"""

__docformat__ = 'restructuredtext'

# magic line for manpage summary
# man: -*- % re-generate package info DB

import argparse
import os
import codecs
import yaml
import gzip
from debian import deb822
import apt_pkg
apt_pkg.init_system()
from os.path import join as opj
from bigmess import cfg
from pprint import PrettyPrinter
from ..utils import load_db, save_db
from .helpers import parser_add_common_args
import logging
lgr = logging.getLogger(__name__)

parser_args = dict(formatter_class=argparse.RawDescriptionHelpFormatter)

def setup_parser(parser):
    parser_add_common_args(parser, opt=('filecache', 'pkgdb'))
    parser.add_argument('--init-db',
                        help="""inital DB""")

def _proc_release_file(release_filename, baseurl):
    rp = deb822.Release(codecs.open(release_filename, 'r', 'utf-8'))
    return rp['Suite'], rp['Components'].split(), rp['Architectures'].split()

def _url2filename(cache, url):
    return opj(cache, url.replace('/', '_').replace(':', '_'))

def run(args):
    lgr.debug("using file cache at '%s'" % args.filecache)
    # get all metadata files from the repo
    meta_baseurl = cfg.get('metadata', 'source extracts baseurl',
                           default=None)
    meta_filenames = cfg.get('metadata', 'source extracts filenames',
                             default='').split()
    rurls = cfg.get('release files', 'urls', default='').split()
    if args.init_db is None:
        db = {'src':{}, 'bin': {}}
    else:
        db = load_db(args.init_db)
    srcdb = db['src']
    bindb = db['bin']
    releases = cfg.options('release files')
    for release in releases:
        rurl = cfg.get('release files', release)
        # first 'Release' files
        relf_path = _url2filename(args.filecache, rurl)
        baseurl = '/'.join(rurl.split('/')[:-1])
        suite, comps, archs = _proc_release_file(relf_path, baseurl)
        for comp in comps:
            # also get 'Sources.gz' for each component
            surl = '/'.join((baseurl, comp, 'source', 'Sources.gz'))
            srcf_path = _url2filename(args.filecache, surl)
            for spkg in deb822.Sources.iter_paragraphs(gzip.open(srcf_path)):
                src_name = spkg['Package']
                sdb = srcdb.get(src_name, {})
                src_version = spkg['Version']
                if apt_pkg.version_compare(src_version,
                                           sdb.get('latest_version', '')) > 0:
                    # this is a more recent version, so let's update all info
                    sdb['latest_version'] = src_version
                    for field in ('Homepage', 'Vcs-Browser', 'Maintainer',
                                  'Uploaders'):
                        sdb[field.lower().replace('-', '_')] = spkg.get(field, '')
                # record all binary packages
                bins = [s.strip() for s in spkg.get('Binary', '').split(',')]
                sdb['binary'] = bins
                for b in bins:
                    if not b in bindb:
                        bindb[b] = {'in_suite': {suite: {src_version: []}},
                                    'src_name': src_name,
                                    'latest_version': src_version}
                    else:
                        bindb[b]['in_suite'][suite] = {src_version: []}
                        if apt_pkg.version_compare(
                                src_version,  bindb[b].get('latest_version', '')) > 0:
                            bindb[b]['src_name'] = src_name
                            bindb[b]['latest_version'] = src_version
                if len(meta_filenames) and not meta_baseurl is None:
                    for mfn in meta_filenames:
                        mfurl = '/'.join((meta_baseurl, src_name, mfn))
                        mfpath = _url2filename(args.filecache, mfurl)
                        if os.path.exists(mfpath):
                            lgr.debug("import metadata for source package '%s'"
                                      % src_name)
                            try:
                                sdb['upstream'] = yaml.safe_load(open(mfpath))
                            except yaml.scanner.ScannerError:
                                lgr.warning("Malformed upstream YAML data for '%s'"
                                            % src_name)
                srcdb[src_name] = sdb
            for arch in archs:
                # next 'Packages.gz' for each component and architecture
                purl = '/'.join((baseurl, comp, 'binary-%s' % arch, 'Packages.gz'))
                pkgf_path = _url2filename(args.filecache, purl)
                for bpkg in deb822.Packages.iter_paragraphs(gzip.open(pkgf_path)):
                    bin_name = bpkg['Package']
                    bin_version = bpkg['Version']
                    try:
                        bin_srcname = bpkg['Source']
                    except KeyError:
                        # if a package has no source name, let's hope it is the
                        # same as the binary name
                        bin_srcname = bin_name
                    if not bin_name in bindb:
                        lgr.warning("No corresponding source package for "
                                    "binary package '%s' in [%s, %s, %s]"
                                    % (bin_name, suite, comp, arch))
                        continue
                    try:
                        bindb[bin_name]['in_suite'][suite][bin_version].append(arch)
                    except KeyError:
                        if not suite in  bindb[bin_name]['in_suite']:
                            # package not listed in this suite?
                            bindb[bin_name]['in_suite'][suite] = {bin_version: [arch]}
                        elif not bin_version in bindb[bin_name]['in_suite'][suite]:
                            # package version not listed in this suite?
                            bindb[bin_name]['in_suite'][suite][bin_version] = [arch]
                        else:
                            raise
                    if apt_pkg.version_compare(
                            bin_version,
                            bindb[bin_name]['latest_version']) >= 0:
                        # most recent -> store description
                        descr = bpkg['Description'].split('\n')

                        bindb[bin_name]['short_description'] = descr[0].strip()
                        bindb[bin_name]['long_description'] = descr[1:]
    # store the full DB
    save_db(db, args.pkgdb)
