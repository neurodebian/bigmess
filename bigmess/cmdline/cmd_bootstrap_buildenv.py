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
import subprocess
import os
from os.path import join as opj
from bigmess import cfg
from .helpers import parser_add_common_args
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
    aptcache = args.aptcache
    if aptcache is None:
        aptcache = cfg.get('build', '%s aptcache' % family,
                           default='')
    if aptcache:
        lgr.debug("using local apt cache at '%s'" % aptcache)
    else:
        lgr.debug("no local apt cache in use")
    components = args.components
    if components is None:
        components = cfg.get('build', '%s components' % family,
                             default='main').split()
    lgr.debug("enabling components %s" % components)

    cmd_opts = [
        '--create',
        '--distribution', codename,
        '--debootstrap', 'debootstrap', # make me an option
        '--aptcache', aptcache,
        '--components', ' '.join(components), 
    ]

    if cfg.has_option('build', '%s bootstrap keyring' % family):
        cmd_opts += ['--debootstrapopts',
                     '--keyring=%s' % cfg.get('build', '%s bootstrap keyring' % family)]
    if cfg.has_option('build', '%s keyring' % family):
        cmd_opts += ['--keyring', cfg.get('build', '%s keyring' % family)]
    if cfg.has_option('build', '%s mirror' % family):
        cmd_opts += ['--mirror', cfg.get('build', '%s mirror' % family)]
    if cfg.has_option('build', '%s othermirror' % family):
        cmd_opts += ['--othermirror', cfg.get('build', '%s othermirror' % family) % codename]

    if not os.path.exists(args.chroot_basedir):
        os.makedirs(args.chroot_basedir)

    archs = args.arch
    if archs is None:
        if not cfg.has_option('build', '%s architectures' % family):
            raise ValueError("no architectures specified, use --arch or add to configuration file")
        archs = cfg.get('build', '%s architectures' % family).split()

    for arch in archs:
        lgr.debug("started bootstrapping architecture '%s'" % arch)
        chroot_targetdir = opj(args.chroot_basedir,
                               '%s-%s-%s' % (family, codename, arch))
        if os.path.exists(chroot_targetdir):
            lgr.warning("'%s' exists -- ignoring architecture '%s'" % (chroot_targetdir, arch))
            continue
        if args.builder == 'pbuilder':
            cmd_opts += ['--basetgz', '%s.tar.gz' % chroot_targetdir]
        elif args.builder == 'cowbuilder':
            cmd_opts += ['--basepath', chroot_targetdir]
        else:
            raise ValueError("unknown builder '%s'" % args.builder)
        cmd_opts += ['--debootstrapopts', '--arch=%s' % arch ]
        ret = subprocess.call(['sudo', args.builder] + cmd_opts) 
        if ret:
            raise RuntimeError("bootstrapping failed (cmd: '%s'; exit code: %s)"
                               % ('%s %s' % (args.builder, ' '.join(cmd_opts)),
                                  ret))
        lgr.debug("finished bootstrapping architecture '%s'" % arch)

def run(args):
    if args.env is None:
        args.env = [env.split('-') for env in cfg.get('build', 'environments', default='').split()]
    lgr.debug("attempting to bootstrap %i environments: %s" % (len(args.env), args.env))
    if args.chroot_basedir is None:
        args.chroot_basedir = cfg.get('build', 'chroot basedir',
                                      default=opj(xdg.BaseDirectory.xdg_data_home,
                                                  'bigmess', 'chroots'))
        lgr.debug("using chroot base directory at '%s'" % args.chroot_basedir)
    if args.builder is None:
        args.builder = cfg.get('build', 'builder', default='pbuilder')
        lgr.debug("using '%s' for bootstrapping" % args.builder)

    for env in args.env:
        lgr.debug("started bootstrapping environment '%s'" % env)
        family, codename = env
        _proc_env(family, codename, args)
        lgr.debug("finished bootstrapping environment '%s'" % env)
