# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the bigmess package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Generate repository configuration helpers from a template.

This command can be used to, for example, generate HTML forms to allow for
selection from various possible repository configurations (e.g. multiple
suites, and multiple mirrors).

A Jinja template is used to generate output in arbitrary formats. The template
renderer is provided with three dictionary containing all relevant information:

``code2name``
  Mapping of repository release codenames to human readable names (e.g. full
  release names)

``mirror2name``
  Mapping of mirror code names to human readable names. If no mirrors are
  configured, this is an empty dictionary

``mirror2url``
  Mapping of mirror code names to their respective repository URLs. If no
  mirrors are configured, this is an empty dictionary

The rendered template is written to stdout.
"""

__docformat__ = 'restructuredtext'

# magic line for manpage summary
# man: -*- % generate mirror selection HTML snippet

import argparse
import os
import codecs
import logging

from bigmess import cfg

lgr = logging.getLogger(__name__)
parser_args = dict(formatter_class=argparse.RawDescriptionHelpFormatter)


def setup_parser(parser):
    parser.add_argument('-t', '--template',
                        help="""Path to a custom template file""")


def run(args):
    from jinja2 import Environment, PackageLoader, FileSystemLoader

    mirror2name = {}
    mirror2url = {}
    code2relname = dict([(r, cfg.get('release names', r))
                         for r in cfg.options('release files')
                         if not r == 'data'])
    if cfg.has_section('mirror names'):
        mirror2name = dict([(m, cfg.get('mirror names', m))
                            for m in cfg.options('mirrors')])
    if cfg.has_section('mirrors'):
        mirror2url = dict([(m, cfg.get('mirrors', m))
                           for m in cfg.options('mirrors')])
    if not args.template is None:
        templ_dir = os.path.dirname(args.template)
        templ_basename = os.path.basename(args.template)
        jinja_env = Environment(loader=FileSystemLoader(templ_dir))
        srclist_template = jinja_env.get_template(templ_basename)
    else:
        jinja_env = Environment(loader=PackageLoader('bigmess'))
        srclist_template = jinja_env.get_template('sources_lists.rst')
    print(
        srclist_template.render(code2name=code2relname,
                                mirror2name=mirror2name,
                                mirror2url=mirror2url))
