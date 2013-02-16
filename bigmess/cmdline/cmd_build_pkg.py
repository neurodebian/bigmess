# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the bigmess package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Update a build environment for a distribution.

This is essentially a frontend to (p|cow)builder's --build mode. However it has
one important additional feature: automatic backporting.

Examples:


"""

__docformat__ = 'restructuredtext'

# magic line for manpage summary
# man: -*- % build a package in one or more environments

import argparse
import sys
import xdg
import time
from debian import deb822
import subprocess
import os
from os.path import join as opj
from bigmess import cfg
from .helpers import parser_add_common_args, get_build_option
import logging
lgr = logging.getLogger(__name__)

parser_args = dict(formatter_class=argparse.RawDescriptionHelpFormatter)


def setup_parser(parser):
    parser_add_common_args(parser,
                           opt=('environments', 'aptcache', 'chroot_basedir',
                                'architectures', 'builder'))
    parser.add_argument('--build-basedir', metavar='PATH',
            help="""base directory for running build environments""")
    parser.add_argument('--result-dir', metavar='PATH',
            help="""directory to place build results into""")
    parser.add_argument('--arch-all-arch', metavar='ARCH',
            help="""environment architecture to be used for building arch 'all'
            packages. Default: 'amd64'""")
    parser.add_argument('--debbuild-options',
            help="""options to be pass onto dpkg-buildpackage""")
    parser.add_argument('--backport', action='store_true',
            help="""if enabled source packages will be automatically backported
            via backport-dsc, which is using the code name of a corresponding
            build environment as '--target-distribution'. See the manpage of
            backport-dsc for details on backporting""")
    parser.add_argument('--bp-maintainer', nargs=2, metavar='VALUE',
            help="""specify a maintainer for a backported source package. The
            maintainer needs to be specified in 'name <email>' format.""")
    parser.add_argument('--bp-mod-control', metavar='SEDEXPR',
            help="""sed-like replacement expression that can be used to
            modify debian/control in backported source package, for example
            to adjust dependencies. more complex modification can be
            implemented as 'dsc-patch'es. See the manpage of backport-dsc
            for details""")
    parser.add_argument('dsc')

def _get_arch_from_dsc(fname):
    for line in open(fname, 'r'):
        if line.startswith('Architecture:'):
            return line.split(':')[1].strip()

def _proc_env(family, codename, args):
    chroot_basedir = get_build_option('chroot basedir',
                                      args.chroot_basedir,
                                      family,
                                      default=opj(xdg.BaseDirectory.xdg_data_home,
                                                  'bigmess', 'chroots'))
    lgr.debug("using chroot base directory at '%s'" % chroot_basedir)
    builder = get_build_option('builder', args.builder, family, default='pbuilder')
    lgr.debug("using '%s' for building" % builder)

    aptcache = get_build_option('aptcache', args.aptcache, family)
    if aptcache:
        lgr.debug("using local apt cache at '%s'" % aptcache)
    else:
        aptcache = ''
        lgr.debug("no local apt cache in use")

    cmd_opts = [
        '--build',
        '--aptcache', aptcache,
    ]

    build_basedir = get_build_option('build basedir', args.build_basedir, family)
    if not build_basedir is None:
        cmd_opts += ['--buildplace', build_basedir]
        if not os.path.exists(build_basedir):
            os.makedirs(build_basedir)

    result_dir = get_build_option('result directory', args.result_dir, family)
    if not result_dir is None:
        cmd_opts += ['--buildresult', result_dir]
        lgr.debug("placing build results in '%s'" % result_dir)
        if not os.path.exists(result_dir):
            os.makedirs(result_dir)

    debbuild_options = get_build_option('debbuild options', args.debbuild_options, family)
    if not debbuild_options is None:
        cmd_opts += ['--debbuildopts', debbuild_options]
        lgr.debug("using additional debbuild options '%s'" % debbuild_options)

    # backport
    if args.backport:
        # assemble backport-dsc call
        bp_args = ['--target-distribution', codename]
        bp_mod_control = get_build_option('backport modify control',
                                          args.bp_mod_control,
                                          family)
        if not bp_mod_control is None:
            bp_args += ['--mod-control', bp_mod_control]
        bp_maintainer = get_build_option('backport maintainer',
                                         args.bp_maintainer,
                                         family)
        if not bp_maintainer is None:
            bp_args += [
                '--maint-name', bp_maintainer.split('<')[0].strip(),
                '--maint-email', bp_maintainer.split('<')[1].strip()[:-1],
            ]
        if cfg.has_option('codename backport ids', codename):
            bp_args += ['--version-suffix',
                        cfg.get('codename backport ids', codename)]
        lgr.debug('attempting to backport source package')
        bp_success = False
        bp_cmd = ['backport-dsc'] + bp_args + [args.dsc]
        lgr.debug("calling: '%s'" % ' '.join(bp_cmd))
        # use check_output() with 2.7+
        bp_proc = subprocess.Popen(bp_cmd, stdout=subprocess.PIPE)
        output, unused_err = bp_proc.communicate()
        retcode = bp_proc.poll()
        if retcode:
            raise RuntimeError("failed to run 'backport-dsc'")
        for line in output.split('\n'):
            if line.endswith('.dsc'):
                backported_dsc = line.split()[-1]
                bp_success = True
        if not bp_success:
            raise RuntimeError("failure to parse output of 'backport-dsc'")

    archs = get_build_option('architectures', args.arch, family)
    if not archs is None:
        archs = archs.split()

    if _get_arch_from_dsc(args.dsc) == 'all':
        # where to build arch:all packages
        archs = [get_build_option('archall architecture', args.arch_all_arch, family,
                                  default='amd64')]
    if archs is None:
        raise ValueError("no architectures specified, use --arch or add to configuration file")

    for arch in archs:
        lgr.debug("started building for architecture '%s'" % arch)
        chroot_target = opj(chroot_basedir,
                            '%s-%s-%s' % (family, codename, arch))
        if builder == 'pbuilder':
            cmd_opts += ['--basetgz', '%s.tar.gz' % chroot_target]
        elif builder == 'cowbuilder':
            cmd_opts += ['--basepath', chroot_target]
        else:
            raise ValueError("unknown builder '%s'" % builder)
        if args.backport:
            sp_args = ['sudo', builder] + cmd_opts + [backported_dsc]
        else:
            sp_args = ['sudo', builder] + cmd_opts + [args.dsc] 
        # make log file
        dsc = deb822.Dsc(open(sp_args[-1]))
        dsc.update({'buildtime': int(time.time()), 'arch': arch})
        with open(opj(result_dir,
                      '%(Source)s_%(Version)s_%(arch)s_%(buildtime)s.build' % dsc),
                  'w') as logfile:
            lgr.info("build log at '%s'" % logfile.name)
            ret = subprocess.call(sp_args,
                                  stderr=subprocess.STDOUT,
                                  stdout=logfile) 
            summaryline = '%s %s ' % (family, codename)
            summaryline += '%(arch)s %(Source)s %(Version)s %(buildtime)s ' % dsc
            with open(opj(result_dir, 'build_summary.log'), 'a+') \
                    as summary_file:
                if ret:
                    summaryline += 'FAILED\n'
                    summary_file.write(summaryline)
                    raise RuntimeError("building failed (cmd: '%s'; exit code: %s)"
                                       % ('%s %s' % (builder, ' '.join(cmd_opts)),
                                          ret))
                summaryline += 'OK\n'
                summary_file.write(summaryline)
        lgr.debug("finished building for architecture '%s'" % arch)

def run(args):
    if args.env is None:
        args.env = [env.split('-') for env in cfg.get('build', 'environments', default='').split()]
    lgr.debug("attempting to build in %i environments: %s" % (len(args.env), args.env))
    for family, codename in args.env:
        lgr.debug("started building in environment '%s-%s'" % (family, codename))
        _proc_env(family, codename, args)
        lgr.debug("finished building in environment '%s-%s'" % (family, codename))

