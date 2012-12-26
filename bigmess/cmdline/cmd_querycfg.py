# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the bigmess package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Query the configuration.

"""

__docformat__ = 'restructuredtext'

# magic line for manpage summary
# man: -*- % query the configuration sections and options

import argparse
import sys
from bigmess import cfg

parser_args = dict(formatter_class=argparse.RawDescriptionHelpFormatter)

def setup_parser(parser):
    parser.add_argument('query', nargs='*', metavar='QUERY')

def run(args):
    query = args.query
    if len(query) < 1:
        # print the whole thing
        cfg.write(sys.stdout)
    elif len(query) < 2:
        # print an entire section
        for item in cfg.items(query[0]):
            print '%s = %s' % item
    else:
        # print just one item
        print cfg.get(query[0], query[1])
