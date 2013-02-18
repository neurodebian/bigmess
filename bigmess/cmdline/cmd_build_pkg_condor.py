# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the bigmess package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Just like build_pkg, but submits builds to a Condor pool.

This command performs the same actions as ``build_pkg``, but instead of
processing in a serial fashion, builds for all desired environments are
submitted individually to a Condor pool.

Currently the implmentation is as follows:

1. The source package is sent/copied to the respective execute node.
2. ``build_pkg`` is called locally on the execute machine and does any
   backporting and the actual building locally. This means that the
   ``chroot-basedir`` needs to be accessible on the execute node.
3. Build results are placed into the ``result-dir`` by ``build_pkg``
   running on the execute node, hence the specified locations have to be
   writable by the user under which the Condor job is running on the execute
   node.

For Condor pools with shared filesystems it is best to specify all file location
using absolute paths.

This implementation is experimental. A number of yet to be implemented features
will make the processing more robust. For example, per-package resource limits
for build processes.

TODO: Make an option to send the basetgz to the build node

"""

__docformat__ = 'restructuredtext'

# magic line for manpage summary
# man: -*- % just like build_pkg, but submits a build to a Condor pool

import argparse
import subprocess
from debian import deb822
import os
import sys
from os.path import join as opj
from bigmess import cfg
from .helpers import parser_add_common_args, get_build_option
import logging
lgr = logging.getLogger(__name__)

parser_args = dict(formatter_class=argparse.RawDescriptionHelpFormatter)

def setup_parser(parser):
    from .cmd_build_pkg import setup_parser as slave_setup
    slave_setup(parser)
    parser.add_argument('--condor-request-memory', type=int, default=1000,
            help="""Memory resource limit for build jobs -- in megabyte.
            Default: 1000M""")
    parser.add_argument('--condor-nice-user', choices=('yes', 'no'),
            default='yes',
            help="""By default build jobs are submitted with the ``nice_user``
            flag, meaning they have lowest priority in the pool queue. Setting
            this to ``no`` will remove this flag and cause build jobs to have
            standard priority.""")
    parser.add_argument('--condor-logdir', metavar='PATH',
            help="""path to store Condor logfiles on the submit machine""")

def run(args):
    if args.env is None:
        args.env = [env.split('-') for env in cfg.get('build', 'environments', default='').split()]
    lgr.debug("attempting to build in %i environments: %s" % (len(args.env), args.env))
    # post process argv
    argv = []
    i = 0
    while i < len(sys.argv):
        av = sys.argv[i]
        if av == '--env':
            i += 2
        elif av == '--arch':
            while i < len(sys.argv) - 1 and not sys.argv[i+1].startswith('-'):
                i += 1
        elif av == '--':
            pass
        elif av.startswith('--condor-'):
            i += 1
        elif av.startswith('--build-basedir'):
            i += 1
        elif av == 'build_pkg_condor':
            argv.append('build_pkg')
        else:
            argv.append(av)
        i += 1
    dsc = deb822.Dsc(open(argv[-1]))
    dsc_dir = os.path.dirname(argv[-1])
    settings = {
        'niceuser': args.condor_nice_user,
        'request_memory': args.condor_request_memory,
        'files': ','.join([argv[-1]] + [opj(dsc_dir, f['name']) for f in dsc['Files']]),
        'src_name': dsc['Source'],
        'src_version': dsc['Version']
    }
    submit = """
universe = vanilla
should_transfer_files = YES
getenv = True
notification = Never
transfer_executable = FALSE
transfer_input_files = %(files)s
request_memory = %(request_memory)i
nice_user = %(niceuser)s
""" % settings


    for family, codename in args.env:
        # logfile destination?
        logdir = get_build_option('condor logdir', args.condor_logdir, family, default=os.curdir)
        if not os.path.exists(logdir):
            os.makedirs(logdir)
        archs = get_build_option('architectures', args.arch, family)
        if isinstance(archs, basestring):
            archs = archs.split()
        for arch in archs:
            arch_settings = {
                'condorlog': os.path.abspath(logdir),
                'arch': arch,
                'executable': argv[0],
                'arguments': ' '.join(argv[1:-1]
                                      + ['--env', family, codename,
                                         '--build-basedir', 'buildbase',
                                         '--arch', arch,
                                         '--']
                                      + [os.path.basename(argv[-1])]),
            }
            arch_settings.update(settings)
            submit += """
executable = %(executable)s
arguments = %(arguments)s
error = %(condorlog)s/%(src_name)s_%(src_version)s_%(arch)s.$(Cluster).$(Process).err
output = %(condorlog)s/%(src_name)s_%(src_version)s_%(arch)s.$(Cluster).$(Process).out
log = %(condorlog)s/%(src_name)s_%(src_version)s_%(arch)s.$(Cluster).$(Process).log
queue

""" % arch_settings
    # store submit file
    condor_submit = subprocess.Popen(['condor_submit'], stdin=subprocess.PIPE)
    condor_submit.communicate(input=submit)
    if condor_submit.wait():
        print argv
        raise RuntimeError("could not submit build; SPEC follows\n---\n%s---\n)" % submit)
