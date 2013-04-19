# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the bigmess package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Cache package information.
"""

__docformat__ = 'restructuredtext'

# magic line for manpage summary
# man: -*- % cache all files required to generate the portal

import argparse
import os
import urllib2
import codecs
import gzip
import logging

from debian import deb822
from os.path import join as opj

from bigmess import cfg
from .helpers import parser_add_common_args

lgr = logging.getLogger(__name__)
parser_args = dict(formatter_class=argparse.RawDescriptionHelpFormatter)


def setup_parser(parser):
    parser_add_common_args(parser, opt=('filecache',))
    parser.add_argument('-f', '--force-update', action='store_true',
                        help="force updating files already present in the cache")


def _proc_release_file(release_filename, baseurl):  # baseurl unused ???
    rp = deb822.Release(codecs.open(release_filename, 'r', 'utf-8'))
    return rp['Components'].split(), rp['Architectures'].split()


def _download_file(url, dst, force_update=False, ignore_missing=False):
    if os.path.isfile(dst) and not force_update:
        lgr.debug("skip '%s'->'%s' (file exists)" % (url, dst))
        return True
    try:
        urip = urllib2.urlopen(url)
        fp = open(dst, 'wb')
        lgr.debug("download '%s'->'%s'" % (url, dst))
        fp.write(urip.read())
        fp.close()
        return True
    except urllib2.HTTPError:
        if not ignore_missing:
            lgr.warning("cannot find '%s'" % url)
        return False
    except urllib2.URLError:
        lgr.warning("cannot connect to '%s'" % url)
        return False


def _url2filename(cache, url):
    return opj(cache, url.replace('/', '_').replace(':', '_'))


def run(args):
    lgr.debug("using file cache at '%s'" % args.filecache)
    # get all metadata files from the repo
    meta_baseurl = cfg.get('metadata', 'source extracts baseurl',
                           default=None)
    meta_filenames = cfg.get('metadata', 'source extracts filenames',
                             default='').split()
    releases = cfg.options('release files')
    # for preventing unnecessary queries
    lookupcache = {}
    # ensure the cache is there
    if not os.path.exists(args.filecache):
        os.makedirs(args.filecache)
    for release in releases:
        rurl = cfg.get('release files', release)
        # first get 'Release' files
        dst_path = _url2filename(args.filecache, rurl)
        if not _download_file(rurl, dst_path, args.force_update):
            continue
        baseurl = '/'.join(rurl.split('/')[:-1])
        comps, archs = _proc_release_file(dst_path, baseurl)
        for comp in comps:
            for arch in archs:
                # also get 'Packages.gz' for each component and architecture
                purl = '/'.join((baseurl, comp,
                                 'binary-%s' % arch, 'Packages.gz'))
                dst_path = _url2filename(args.filecache, purl)
                if not _download_file(purl, dst_path, args.force_update):
                    continue
            # also get 'Sources.gz' for each component
            surl = '/'.join((baseurl, comp, 'source', 'Sources.gz'))
            dst_path = _url2filename(args.filecache, surl)
            if not _download_file(surl, dst_path, args.force_update):
                continue
            # TODO go through the source file and try getting 'debian/upstream'
            # from the referenced repo
            for spkg in deb822.Sources.iter_paragraphs(gzip.open(dst_path)):
                # TODO pull stuff directly form VCS
                #vcsurl = spkg.get('Vcs-Browser', None)
                #if vcsurl is None:
                #    lgr.warning("no VCS URL for '%s'" % spkg['Package'])
                #    continue
                #print vcsurl
                #http://github.com/yarikoptic/vowpal_wabbit
                #->
                #http://raw.github.com/yarikoptic/vowpal_wabbit/debian/debian/compat
                src_name = spkg['Package']
                if not len(meta_filenames) or meta_baseurl is None:
                    continue
                lgr.debug("query metadata for source package '%s'" % src_name)
                for mfn in meta_filenames:
                    mfurl = '/'.join((meta_baseurl, src_name, mfn))
                    dst_path = _url2filename(args.filecache, mfurl)
                    if dst_path in lookupcache:
                        continue
                    _download_file(mfurl, dst_path, args.force_update,
                                   ignore_missing=True)
                    lookupcache[dst_path] = None
    tasks = cfg.options('task files')
    for task in tasks:
        rurl = cfg.get('task files', task)
        dst_path = opj(args.filecache, 'task_%s' % task)
        if not _download_file(rurl, dst_path, args.force_update):
            continue
