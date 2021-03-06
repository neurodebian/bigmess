# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the bigmess package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
""" """

__docformat__ = 'restructuredtext'

import os
import gzip
import codecs
import xdg.BaseDirectory
import logging

from pprint import PrettyPrinter
from os.path import join as opj

import bigmess

lgr = logging.getLogger(__name__)


def get_cache_dir():
    """Return the path to the cache.

    Implements XDG Base Directory Specification, hence allows overwriting the
    config setting with $XDG_CACHE_HOME.
    """
    cacheroot = xdg.BaseDirectory.xdg_cache_home
    if not os.path.isabs(cacheroot):
        lgr.debug("freedesktop.org standard dictates to ignore non-absolute "
                  "XDG_CACHE_HOME setting '%s'" % cacheroot)
        cacheroot = os.path.expanduser(opj('~', '.cache'))
    cachepath = os.path.expandvars(
        bigmess.cfg.get('cache', 'basedir',
                        default=opj(cacheroot, 'bigmess')))
    return cachepath


def load_db(filename):
    """Load the package DB from file"""
    gzf = gzip.open(filename, 'rb')
    utf_reader = codecs.getreader('utf-8')
    utf_contents = utf_reader(gzf)
    db = eval(utf_contents.read())
    gzf.close()
    return db


def save_db(db, filename):
    """Store a package DB as compressed text file"""
    pp = PrettyPrinter(indent=2)
    gzf = gzip.open(filename, 'wb')
    utf_writer = codecs.getwriter('utf-8')
    utf_contents = utf_writer(gzf)
    utf_contents.write(pp.pformat(db))
    gzf.close()


def underline_text(text, symbol):
    """Underline a string with a given symbol"""
    underline = symbol * len(text)
    return '%s\n%s\n' % (text, underline)
