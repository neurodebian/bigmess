# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the bigmess package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Update a build environment

This is essentially a frontend to (p|cow)builder's --update mode.

Examples:

Update all known build environments and architectures

  % bigmess update_buildenv

"""

__docformat__ = 'restructuredtext'

# magic line for manpage summary
# man: -*- % update a build environment for a distribution

import argparse
import sys
import xdg
import subprocess
import os
from os.path import join as opj
from bigmess import cfg
from .helpers import parser_add_common_args, get_dir_cfg, get_path_cfg
import logging
lgr = logging.getLogger(__name__)

parser_args = dict(formatter_class=argparse.RawDescriptionHelpFormatter)


def setup_parser(parser):
    parser_add_common_args(parser,
                           opt=('environments', 'aptcache', 'chroot_basedir',
                                'architectures', 'builder'))

def _proc_env(family, codename, args):
    builder = args.builder
    if builder is None:
        builder = cfg.get('build', 'builder', default='pbuilder')
    lgr.debug("using '%s' for updating" % builder)
    chroot_basedir = get_dir_cfg('chroot basedir', args.chroot_basedir,
                                 family,
                                 default=opj(xdg.BaseDirectory.xdg_data_home,
                                            'bigmess', 'chroots'))
    lgr.debug("using chroot base directory at '%s'" % chroot_basedir)
    aptcache = args.aptcache
    if aptcache is None:
        aptcache = cfg.get('build', '%s aptcache' % family, default='')
    if aptcache:
        lgr.debug("using local apt cache at '%s'" % aptcache)
    else:
        lgr.debug("no local apt cache in use")

    cmd_opts = [
        '--update',
        '--aptcache', aptcache,
    ]

    keyring = get_path_cfg('keyring', None, family) 
    if not keyring is None:
        cmd_opts += ['--keyring', keyring]
    mirror = get_path_cfg('mirror', None, family) 
    if not mirror is None:
        cmd_opts += ['--mirror', mirror]
    othermirror = get_path_cfg('othermirror', None, family) 
    if not othermirror is None:
        cmd_opts += ['--othermirror', othermirror % dict(release=codename)]

    archs = args.arch
    if archs is None:
        if not cfg.has_option('build', '%s architectures' % family):
            raise ValueError("no architectures specified, use --arch or add to configuration file")
        archs = cfg.get('build', '%s architectures' % family).split()

    for arch in archs:
        lgr.debug("started updating architecture '%s'" % arch)
        chroot_target = opj(chroot_basedir,
                            '%s-%s-%s' % (family, codename, arch))
        if builder == 'pbuilder':
            cmd_opts += ['--basetgz', '%s.tar.gz' % chroot_target]
        elif builder == 'cowbuilder':
            cmd_opts += ['--basepath', chroot_target]
        else:
            raise ValueError("unknown builder '%s'" % builder)
        ret = subprocess.call(['sudo', builder] + cmd_opts) 
        if ret:
            raise RuntimeError("updating failed (cmd: '%s'; exit code: %s)"
                               % ('%s %s' % (builder, ' '.join(cmd_opts)),
                                  ret))
        lgr.debug("finished updating architecture '%s'" % arch)

def run(args):
    if args.env is None:
        args.env = [env.split('-')
                        for env in cfg.get('build',
                                           'environments',
                                           default='').split()]
    lgr.debug("attempting to update %i environments: %s"
              % (len(args.env), args.env))
    for env in args.env:
        lgr.debug("started updating environment '%s'" % env)
        family, codename = env
        _proc_env(family, codename, args)
        lgr.debug("finished updating environment '%s'" % env)
