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
from .helpers import parser_add_common_args, get_build_option, arg2bool
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
    parser.add_argument('--source-include', type=arg2bool,
            help="""if true, equivalent to option -sa for dpkg-buildpackage,
            but is only in effect once for each source package in a batch build
            """)
    parser.add_argument('--debbuild-options',
            help="""options to be pass onto dpkg-buildpackage, don't use this
            for: -sa, -B and friends. Look at --source-include instead. To
            prevent problems while parsing the command line, put the argument
            in quotes and add a space to the front, e.g. ' -d'.""")
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


def _backport_dsc(dsc, codename, family, args):
    dsc_dict = deb822.Dsc(open(dsc))
    # assemble backport-dsc call
    bp_args = ['--target-distribution', codename]
    bp_mod_control = get_build_option('backport modify control',
                                      args.bp_mod_control,
                                      family)
    modcontrol_blacklist = get_build_option('backport modify control blacklist',
                                            family=family,
                                            default='').split()
    # if blacklisted for this source package: reset
    if dsc_dict['Source'] in modcontrol_blacklist:
        lgr.debug("source package '%s' is blacklisted for control file modification"
                  % dsc_dict['Source'])
        bp_mod_control = None
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
    if cfg.has_option('release backport ids', codename):
        bp_args += ['--version-suffix',
                    cfg.get('release backport ids', codename)]
    lgr.debug('attempting to backport source package')
    bp_success = False
    bp_cmd = ['backport-dsc'] + bp_args + [dsc]
    lgr.debug("calling: %s" % bp_cmd)
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
    return backported_dsc

def _get_chroot_base(family, codename, arch, args):
    chroot_basedir = get_build_option('chroot basedir',
                                      args.chroot_basedir,
                                      family,
                                      default=opj(xdg.BaseDirectory.xdg_data_home,
                                                  'bigmess', 'chroots'))
    lgr.debug("using chroot base directory at '%s'" % chroot_basedir)
    chroot_target = opj(chroot_basedir,
                        '%s-%s-%s' % (family, codename, arch))
    return chroot_target


def _get_arch_from_dsc(fname):
    for line in open(fname, 'r'):
        if line.startswith('Architecture:'):
            return line.split(':')[1].strip()

def _proc_env(family, codename, args, source_include):
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
    if result_dir is None:
        result_dir = os.path.abspath(os.curdir)
    cmd_opts += ['--buildresult', result_dir]
    lgr.debug("placing build results in '%s'" % result_dir)
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)

    # backport
    if args.backport:
        backported_dsc = _backport_dsc(args.dsc, codename, family, args)

    archs = get_build_option('architectures', args.arch, family)
    if not archs is None:
        if not isinstance(archs, list):
            archs = archs.split()

    if _get_arch_from_dsc(args.dsc) == 'all':
        # where to build arch:all packages
        archs = [get_build_option('archall architecture', args.arch_all_arch, family,
                                  default='amd64')]
    if archs is None:
        raise ValueError("no architectures specified, use --arch or add to configuration file")

    had_failures = False
    first_arch = True
    for arch in archs:
        # source include?
        debbuild_options = get_build_option('debbuild options', args.debbuild_options, family)
        # what kind of build are we aiming for
        if first_arch:
            # first round
            if source_include == True:
                # we source include in first round
                buildtype_opt = ' -sa'
            elif source_include == False:
                buildtype_opt = ' -b'
            else:
                # leave default
                buildtype_opt = ''
        else:
            # except for the first one all others are binary only
            buildtype_opt += ' -B'
        if not debbuild_options is None:
            debbuild_options += buildtype_opt
        else:
            debbuild_options = buildtype_opt
        cmd_opts += ['--debbuildopts', debbuild_options]
        lgr.debug("using additional debbuild options '%s'" % debbuild_options)

        lgr.debug("started building for architecture '%s'" % arch)
        chroot_target = _get_chroot_base(family, codename, arch, args)
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
        dsc = dict(deb822.Dsc(open(sp_args[-1])))
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
            if ret:
                summaryline += 'FAILED\n'
                had_failures = True
                lgr.warning("building failed (cmd: '%s'; exit code: %s)"
                                   % (sp_args, ret))
            else:
                summaryline += 'OK\n'
            logfile.write(summaryline)
        lgr.debug("finished building for architecture '%s'" % arch)
        first_arch = False
    return had_failures

def run(args):
    if args.env is None:
        args.env = [env.split('-') for env in cfg.get('build', 'environments', default='').split()]
    lgr.debug("attempting to build in %i environments: %s" % (len(args.env), args.env))
    had_failures = False
    source_include = args.source_include
    for family, codename in args.env:
        lgr.debug("started building in environment '%s-%s'" % (family, codename))
        if args.backport:
            # start with default for each backport run, i.e. source package version
            source_include = args.source_include
        if source_include is None:
            # any configure source include strategy?
            source_include = cfg.get('build', 'source include', default=False)
        if _proc_env(family, codename, args, source_include):
            had_failures = True
        # don't include more than once per source package version - will cause
        # problem as parts of the source packages get regenerated and original
        # checksums no longer match
        source_include = False
        lgr.debug("finished building in environment '%s-%s'" % (family, codename))
    if had_failures:
        raise RuntimeError("some builds failed")
