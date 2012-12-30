# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the bigmess package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Generate an HTML snippet for a mirror selection form.

"""

__docformat__ = 'restructuredtext'

# magic line for manpage summary
# man: -*- % generate mirror selection HTML snippet

import argparse
import os
from os.path import join as opj
from bigmess import cfg
from jinja2 import Environment as JinjaEnvironment
from jinja2 import PackageLoader as JinjaPackageLoader
import logging
lgr = logging.getLogger(__name__)

parser_args = dict(formatter_class=argparse.RawDescriptionHelpFormatter)

def setup_parser(parser):
    pass

def run(args):
    code2relname = dict([(r, cfg.get('release names', r))
                            for r in cfg.options('release names')
                                if not r == 'data'])
    mirror2name = dict([(m, cfg.get('mirror names', m))
                            for m in cfg.options('mirrors')])
    mirror2url = dict([(m, cfg.get('mirrors', m))
                            for m in cfg.options('mirrors')])

    jinja_env = JinjaEnvironment(loader=JinjaPackageLoader('bigmess'))
    srclist_template = jinja_env.get_template('sources_lists.rst')
    print srclist_template.render(code2relname=code2relname,
                                  mirror2name=mirror2name,
                                  mirror2url=mirror2url)


