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
import urllib.request, urllib.error, urllib.parse
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
        urip = urllib.request.urlopen(url)
        fp = open(dst, 'wb')
        lgr.debug("download '%s'->'%s'" % (url, dst))
        fp.write(urip.read())
        fp.close()
        return True
    except urllib.error.HTTPError:
        if not ignore_missing:
            lgr.warning("cannot find '%s'" % url)
        return False
    except urllib.error.URLError:
        lgr.warning("cannot connect to '%s'" % url)
        return False


def _url2filename(cache, url):
    return opj(cache, url.replace('/', '_').replace(':', '_'))

def _find_release_origin_archive(cfg, release):
    # available
    origins = []
    for origin in cfg.options('release bases'):
        archive = cfg.get('release bases', origin)
        if not archive:
            continue
        url = '%s/dists/%s/Release' % (archive, release)
        try:
            urip = urllib.request.urlopen(url)
            info = urip.info()
            origins.append(archive)
        except urllib.error.HTTPError:
            lgr.debug("No '%s'" % url)
        except urllib.error.URLError:
            lgr.debug("Can't connect to'%s'" % url)
    if len(origins) == 0:
        lgr.info("Found no origin for %r. Assuming it originates here."
                 % release)
        return None
    elif len(origins) > 1:
        lgr.warning("More than a single origin archive was found for %r: %s. "
                    "!Disambiguate (TODO)!" % (release, origins))
        return None
    return origins[0]

def run(args):
    lgr.debug("using file cache at '%s'" % args.filecache)
    # get all metadata files from the repo
    meta_baseurl = cfg.get('metadata', 'source extracts baseurl',
                           default=None)
    meta_filenames = cfg.get('metadata', 'source extracts filenames',
                             default='').split()

    #
    # Releases archives
    #
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
        # Fetch information on binary packages
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

        # Also fetch corresponding Release from the base distribution
        # Figure out the base distribution based on the release description
        rname = cfg.get('release names', release)
        if not rname:
            continue

        # Look-up release bases for the release among available bases
        oarchive = _find_release_origin_archive(cfg, release)
        if not oarchive:
            continue

        obaseurl = '%s/%s' % (oarchive, '/'.join(rurl.split('/')[-3:-1]))
        orurl = '%s/Release' % obaseurl
        # first get 'Release' files
        dst_path = _url2filename(args.filecache, orurl)
        if not _download_file(orurl, dst_path, args.force_update):
            continue

        comps, _ = _proc_release_file(dst_path, obaseurl)
        for comp in comps:
            # Fetch information on source packages -- we are not interested
            # to provide a thorough coverage -- just the version
            osurl = '/'.join((obaseurl, comp, 'source', 'Sources.gz'))
            dst_path = _url2filename(args.filecache, osurl)
            if not _download_file(osurl, dst_path, args.force_update):
                continue

    #
    # Tasks
    #
    tasks = cfg.options('task files')
    for task in tasks:
        rurl = cfg.get('task files', task)
        dst_path = opj(args.filecache, 'task_%s' % task)
        if not _download_file(rurl, dst_path, args.force_update):
            continue
