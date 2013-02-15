# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the bigmess package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Run a build environment

This command can be used to log into a build environment, or to execute a script
in a build environment. It is basically a frontend to (p|cow)builder's --login
and --execute modes.

Examples:

Start an interactive session in a build environment using the default
architecture 'amd64' and with mounting the /home directory inside the
environment.

  % bigmess run_build_env --env debian squeeze --mount /home

Run a script in a build environment

  % bigmess run_build_env --env debian squeeze -- myscript.sh

"""

__docformat__ = 'restructuredtext'

# magic line for manpage summary
# man: -*- % run a build environment

import argparse
import sys
import xdg
import subprocess
import os
from os.path import join as opj
from bigmess import cfg
from .helpers import parser_add_common_args
import logging
lgr = logging.getLogger(__name__)

parser_args = dict(formatter_class=argparse.RawDescriptionHelpFormatter)

def setup_parser(parser):
    parser.add_argument('--env', nargs=2, required=True,
            help="""build environment to run. This first argument must be a known
            environment family name, while the second argument is a codename for
            a particular suite, for example: 'debian' 'wheezy'""")
    parser.add_argument('--arch', required=True, default='amd64',
            help="""architecture of the build environment to run (default:
            'amd64')""")
    parser.add_argument('--mount', nargs='+', metavar='PATH',
            help="""path(s) to bindmount within the build environment""")
    parser.add_argument('script', nargs='*')
    parser_add_common_args(parser, opt=('chroot_basedir', 'builder'))

def run(args):
    if args.chroot_basedir is None:
        args.chroot_basedir = cfg.get('build', 'chroot basedir',
                                      default=opj(xdg.BaseDirectory.xdg_data_home,
                                                  'bigmess', 'chroots'))
        lgr.debug("using chroot base directory at '%s'" % args.chroot_basedir)
    if args.builder is None:
        args.builder = cfg.get('build', 'builder', default='pbuilder')
        lgr.debug("using '%s' for updating" % args.builder)

    family, codename = args.env
    cmd_opts = [] 

    if not args.mount is None:
        cmd_opts += ['--bindmounts'] + args.mount
    chroot_target = opj(args.chroot_basedir,
                       '%s-%s-%s' % (family, codename, args.arch))
    if args.builder == 'pbuilder':
        cmd_opts += ['--basetgz', '%s.tar.gz' % chroot_target]
    elif args.builder == 'cowbuilder':
        cmd_opts += ['--basepath', chroot_target]
    else:
        raise ValueError("unknown builder '%s'" % args.builder)

    if not args.script is None and len(args.script): 
        cmd_opts = ['--execute'] + cmd_opts + ['--'] + args.script
    else:
        cmd_opts = ['--login'] + cmd_opts

    ret = subprocess.call(['sudo', args.builder] + cmd_opts) 
    if ret:
        raise RuntimeError("running failed (cmd: '%s'; exit code: %s)"
                           % ('%s %s' % (args.builder, ' '.join(cmd_opts)),
                              ret))
