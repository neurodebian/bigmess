# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the bigmess package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
""" """

__docformat__ = 'restructuredtext'

# argument spec template
#<name> = (
#    <id_as_positional>, <id_as_option>
#    {<ArgusmentParser.add_arguments_kwargs>}
#)

from os.path import join as opj

from ..cmdline.helpers import HelpAction
from ..utils import get_cache_dir

help = (  # builtin redefined ???
    'help', ('-h', '--help', '--help-np'),
    dict(nargs=0, action=HelpAction,
         help="""show this help message and exit. --help-np forcefully disables
                 the use of a pager for displaying the help.""")
    )

version = (
    'version', ('--version',),
    dict(action='version',
         help="show program's version and license information and exit")
)

filecache = (
    'filecache', ('-c', '--filecache'),
    dict(default=opj(get_cache_dir(), 'files'),
         help="""path to the file cache. By default the cache is located
              at ~/.cache/bigmess/files. A XDG_CACHE_HOME variable
              will also be honored when determining the default.""")
)

pkgdb = (
    'pkgdb', ('-p', '--pkgdb'),
    dict(default=opj(get_cache_dir(), 'pkgdb.gz'),
         help="""path to the package database. By default the database is
              located at ~/.cache/bigmess/pkgdb.gz. A XDG_CACHE_HOME variable
              will also be honored when determining the default.""")
)


environments = (
    'env', ('--env',),
    dict(nargs=2, action='append',
         help="""build environments to limit processing to. This first
         argument must be a known environment family name, while the second
         argument is a codename for a particular suite, for example:
         'debian' 'wheezy'. If this option is not given, all known/configured
         environments are going to be processed""")
)

aptcache = (
    'aptcache', ('--aptcache',),
    dict(metavar='PATH',
         help="""override cache location for APT, setting this to an empty
         string disables local caching entirely""")
)

chroot_basedir = (
    'chroot-basedir', ('--chroot-basedir',),
    dict(metavar='PATH',
         help="""override configured base directory for stored build
         environments (chroots, basetgz)""")
)

architectures = (
    'arch', ('--arch',),
    dict(nargs='+',
         help="""list of architectures to process""")
)

builder = (
    'builder', ('--builder',),
    dict(choices=('cowbuilder', 'pbuilder'),
         help="""select tool for carrying out the work""")
)


