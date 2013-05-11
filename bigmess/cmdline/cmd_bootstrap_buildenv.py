# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the bigmess package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Bootstrap a build environment

This is a frontend to (p|cow)builder's --create mode to facilitate
bootstrapping of build environments needed for a particular repository
setup. Information on necessary environments is read from the bigmess
configuration, but can be overriden by command line arguments.

Examples:

Bootstrap all configured environments

  % bigmess bootstrap_buildenv

Bootstrap a particular environment

  % bigmess bootstrap_buildenv --env debian wheezy --arch i386

"""

__docformat__ = 'restructuredtext'

# magic line for manpage summary
# man: -*- % bootstrap a build environment for a distribution

import argparse
import sys
import xdg
from copy import deepcopy
import subprocess
import os
from os.path import join as opj
from bigmess import cfg
from .helpers import parser_add_common_args, get_dir_cfg, get_build_option
import logging
lgr = logging.getLogger(__name__)

parser_args = dict(formatter_class=argparse.RawDescriptionHelpFormatter)

def setup_parser(parser):
    parser_add_common_args(parser,
                           opt=('environments', 'aptcache', 'chroot_basedir',
                                'architectures', 'builder'))
    parser.add_argument('--components', nargs='+',
            help="""list of archive components to enable in the build
            environment. For example: main contrib non-free""")

def _proc_env(family, codename, args):
    aptcache = get_dir_cfg('aptcache', args.aptcache, family,
                           ensure_exists=False)
    components = get_build_option('components', args.components, family,
                                  default='main').split()
    lgr.debug("enabling components %s" % components)

    cmd_opts_prefix = [
        '--create',
        '--distribution', codename,
        '--debootstrap', 'debootstrap', # make me an option
        '--aptcache', aptcache,
        '--components', ' '.join(components), 
    ]

    bootstrap_keyring = get_dir_cfg('bootstrap keyring', None, family,
                           ensure_exists=False)
    if not bootstrap_keyring is None:
        cmd_opts_prefix += ['--debootstrapopts', '--keyring=%s' % bootstrap_keyring]
    keyring = get_dir_cfg('keyring', None, family, ensure_exists=False)
    if not keyring is None:
        cmd_opts_prefix += ['--keyring', keyring]
    mirror = get_build_option('mirror', None, family)
    if not mirror is None:
        cmd_opts_prefix += ['--mirror', mirror]
    othermirror = get_build_option('othermirror', None, family)
    if not othermirror is None:
        cmd_opts_prefix += ['--othermirror',
                            othermirror % {'release': codename}]
    chroot_basedir = get_dir_cfg('chroot basedir', args.chroot_basedir, family,
                                 ensure_exists=False,
                                 default=opj(xdg.BaseDirectory.xdg_data_home,
                                             'bigmess', 'chroots'))

    builder = get_build_option('builder', args.builder, family, default='pbuilder')
    lgr.debug("using '%s' for building" % builder)

    archs = get_build_option('architectures', args.arch, family, default=None)
    if archs is None:
        raise ValueError("no architectures specified, use --arch or add to configuration file")
    if not isinstance(archs, list):
        archs = archs.split()

    for arch in archs:
        cmd_opts = deepcopy(cmd_opts_prefix)
        lgr.debug("started bootstrapping architecture '%s'" % arch)
        chroot_targetdir = opj(chroot_basedir,
                               '%s-%s-%s' % (family, codename, arch))
        if os.path.exists(chroot_targetdir):
            lgr.warning("'%s' exists -- ignoring architecture '%s'" % (chroot_targetdir, arch))
            continue
        if builder == 'pbuilder':
            cmd_opts += ['--basetgz', '%s.tar.gz' % chroot_targetdir]
        elif builder == 'cowbuilder':
            cmd_opts += ['--basepath', chroot_targetdir]
        else:
            raise ValueError("unknown builder '%s'" % builder)
        cmd_opts += ['--debootstrapopts', '--arch=%s' % arch ]
        ret = subprocess.call(['sudo', builder] + cmd_opts) 
        if ret:
            raise RuntimeError("bootstrapping failed (cmd: '%s'; exit code: %s)"
                               % ('%s %s' % (builder, ' '.join(cmd_opts)),
                                  ret))
        lgr.debug("finished bootstrapping architecture '%s'" % arch)

def run(args):
    if args.env is None:
        args.env = [env.split('-') for env in cfg.get('build',
                                                      'environments',
                                                      default='').split()]
    lgr.debug("attempting to bootstrap %i environments: %s"
              % (len(args.env), args.env))

    for env in args.env:
        lgr.debug("started bootstrapping environment '%s'" % env)
        family, codename = env
        _proc_env(family, codename, args)
        lgr.debug("finished bootstrapping environment '%s'" % env)
