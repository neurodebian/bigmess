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
import gzip
import apt_pkg
import logging

from debian import deb822
from os.path import join as opj

from bigmess import cfg
from ..utils import load_db, save_db
from .helpers import parser_add_common_args

apt_pkg.init_system()
lgr = logging.getLogger(__name__)
parser_args = dict(formatter_class=argparse.RawDescriptionHelpFormatter)


def setup_parser(parser):
    parser_add_common_args(parser, opt=('filecache', 'pkgdb'))
    parser.add_argument('--init-db',
                        help="""inital DB""")


def _proc_release_file(release_filename, baseurl):
    rp = deb822.Release(codecs.open(release_filename, 'r', 'utf-8'))
    return rp['Codename'], rp['Components'].split(), rp['Architectures'].split()


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
        db = {'src': {}, 'bin': {}, 'task': {}}
    else:
        db = load_db(args.init_db)
    srcdb = db['src']
    bindb = db['bin']
    taskdb = db['task']
    releases = cfg.options('release files')
    for release in releases:
        rurl = cfg.get('release files', release)
        # first 'Release' files
        relf_path = _url2filename(args.filecache, rurl)
        baseurl = '/'.join(rurl.split('/')[:-1])
        codename, comps, archs = _proc_release_file(relf_path, baseurl)
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
                        bindb[b] = {'in_release': {codename: {src_version: []}},
                                    'src_name': src_name,
                                    'latest_version': src_version}
                    else:
                        bindb[b]['in_release'][codename] = {src_version: []}
                        if apt_pkg.version_compare(
                                src_version,  bindb[b].get('latest_version', '')) > 0:
                            bindb[b]['src_name'] = src_name
                            bindb[b]['latest_version'] = src_version
                if 'upstream' in meta_filenames and not meta_baseurl is None:
                    import yaml
                    mfn = 'upstream'
                    mfurl = '/'.join((meta_baseurl, src_name, mfn))
                    mfpath = _url2filename(args.filecache, mfurl)
                    if os.path.exists(mfpath):
                        lgr.debug("import metadata for source package '%s'"
                                  % src_name)
                        try:
                            upstream = yaml.safe_load(open(mfpath))
                        except yaml.scanner.ScannerError, e:
                            lgr.warning("Malformed upstream YAML data for '%s'"
                                        % src_name)
                            lgr.debug("Caught exception was: %s" % (e,))
                        # uniformize structure
                        if 'Reference' in upstream and not isinstance(upstream['Reference'], list):
                            upstream['Reference'] = [upstream['Reference']]
                        sdb['upstream'] = upstream
                sdb['component'] = comp
                for mf in meta_filenames:
                    if os.path.exists(_url2filename(args.filecache,
                                                    '/'.join((meta_baseurl,
                                                              src_name,
                                                              mf)))):
                        sdb['havemeta_%s' % mf.replace('.', '_').replace('-', '_')] = True
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
                        bin_srcname = bin_name  # unused bin_srcname ???
                    if not bin_name in bindb:
                        lgr.warning("No corresponding source package for "
                                    "binary package '%s' in [%s, %s, %s]"
                                    % (bin_name, codename, comp, arch))
                        continue
                    try:
                        bindb[bin_name]['in_release'][codename][bin_version].append(arch)
                    except KeyError:
                        if not codename in bindb[bin_name]['in_release']:
                            # package not listed in this release?
                            bindb[bin_name]['in_release'][codename] = {bin_version: [arch]}
                        elif not bin_version in bindb[bin_name]['in_release'][codename]:
                            # package version not listed in this release?
                            bindb[bin_name]['in_release'][codename][bin_version] = [arch]
                        else:
                            raise
                    if apt_pkg.version_compare(
                            bin_version,
                            bindb[bin_name]['latest_version']) >= 0:
                        # most recent -> store description
                        descr = bpkg['Description'].split('\n')

                        bindb[bin_name]['short_description'] = descr[0].strip()
                        bindb[bin_name]['long_description'] = descr[1:]

    # Review availability of (source) packages in the base
    # releases.  Since we might not have something already
    # available in the base release, we do it in a separate loop,
    # after we got information on all packages which we do have in
    # some release in our repository
    for release in releases:
        rurl = cfg.get('release files', release)
        rname = cfg.get('release names', release)
        if not rname:
            continue

        rorigin = rname.split()[0].lower()   # debian or ubuntu
        omirror = cfg.get('release bases', rorigin)
        if not omirror:
            continue

        bbaseurl = '%s/%s' % (omirror, '/'.join(rurl.split('/')[-3:-1]))
        brurl = '%s/Release' % bbaseurl

        # first 'Release' files
        brelf_path = _url2filename(args.filecache, brurl)
        codename, comps, archs = _proc_release_file(brelf_path, bbaseurl)
        for comp in comps:
            # also get 'Sources.gz' for each component
            surl = '/'.join((bbaseurl, comp, 'source', 'Sources.gz'))
            srcf_path = _url2filename(args.filecache, surl)
            for spkg in deb822.Sources.iter_paragraphs(gzip.open(srcf_path)):
                sdb = srcdb.get(spkg['Package'], None)
                if not sdb:
                    continue
                src_version = spkg['Version']
                if not 'in_base_release' in sdb:
                    sdb['in_base_release'] = {}
                sdb['in_base_release'][codename] = src_version

    tasks = cfg.options('task files')
    for task in tasks:
        srcf_path = opj(args.filecache, 'task_%s' % task)
        for st in deb822.Packages.iter_paragraphs(open(srcf_path)):
            if st.has_key('Task'):
                taskdb[task] = st['Task']
                continue
            elif st.has_key('Depends'):
                pkg = st['Depends']
            elif st.has_key('Recommends'):
                pkg = st['Recommends']
            elif st.has_key('Suggests'):
                pkg = st['Suggests']
            else:
                lgr.warning("Ignoring unkown stanza in taskfile: %s" % st)
                continue

            # take care of pkg lists
            for p in pkg.split(', '):
                if not p in bindb:
                    lgr.info("Ignoring package '%s' (listed in task '%s', but not in repository)"
                             % (p, task))
                    continue
                pgdb = srcdb[bindb[p]['src_name']]
                if not 'upstream' in pgdb:
                    pgdb['upstream'] = {}
                udb = pgdb['upstream']
                taglist = udb.setdefault('Tags', [])
                taglist.append('task::%s' % task)
                udb['Tags'] = taglist
                # Publications
                if st.has_key('Published-Title') and not 'Reference' in udb:
                    title = st['Published-Title']
                    if title[-1] == '.':
                        # trip trailing dot -- added later
                        pub = {'Title': title[:-1]}
                    else:
                        pub = {'Title': title}
                    if st.has_key('Published-Authors'):
                        pub['Author'] = st['Published-Authors']
                    if st.has_key('Published-Year'):
                        pub['Year'] = st['Published-Year']
                    if st.has_key('Published-In'):
                        pub['Journal'] = st['Published-In']
                    if st.has_key('Published-URL'):
                        pub['URL'] = st['Published-URL']
                    if st.has_key('Published-DOI'):
                        pub['DOI'] = st['Published-DOI']
                        # need at least one URL
                        if not pub.has_key('url'):
                            pub['URL'] = "http://dx.doi.org/%s" % st['Published-DOI']
                    udb['Reference'] = [pub]
                # Registration
                if st.has_key('Registration') and not 'Registration' in udb:
                    udb['Registration'] = st['Registration']
                # Remarks
                if st.has_key('Remark') and not 'Remark' in udb:
                    udb['Remark'] = st['Remark']
    # store the full DB
    save_db(db, args.pkgdb)
