# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the bigmess package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Generate APT sources lists for all configured mirrors.

"""

__docformat__ = 'restructuredtext'

# magic line for manpage summary
# man: -*- % generate APT sources lists

import argparse
import os
import logging

from os.path import join as opj

from bigmess import cfg

lgr = logging.getLogger(__name__)
parser_args = dict(formatter_class=argparse.RawDescriptionHelpFormatter)


def setup_parser(parser):
    parser.add_argument('-d', '--dest-dir', default=os.curdir,
                        help="""target directory for storing the generated lists""")


def run(args):
    for release in cfg.options('release names'):
        if release == 'data':
            # no seperate list for the data archive
            continue
        for mirror in cfg.options('mirrors'):
            for suites, tag in (('main contrib non-free', 'full'),
                                ('main', 'libre')):
                listname = '%s.%s.%s' % (release, mirror, tag)
                lf = open(opj(args.dest_dir, listname), 'w')
                for rel in ('data', release):
                    aptcfg = '%s %s %s\n' % (cfg.get('mirrors', mirror),
                                             rel,
                                             suites)
                lf.write('deb %s' % aptcfg)
                lf.write('#deb-src %s' % aptcfg)
                lf.close()
