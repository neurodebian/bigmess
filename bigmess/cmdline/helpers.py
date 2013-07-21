# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the testkraut package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
""" """

__docformat__ = 'restructuredtext'

import argparse
import re
import sys
import os
import logging
lgr = logging.getLogger(__name__)


class HelpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if option_string == '--help':
            # lets use the manpage on mature systems ...
            try:
                import subprocess
                subprocess.check_call(
                    'man %s 2> /dev/null' % parser.prog.replace(' ', '-'),
                    shell=True)
                sys.exit(0)
            except (subprocess.CalledProcessError, OSError):
                # ...but silently fall back if it doesn't work
                pass
        if option_string == '-h':
            helpstr = "%s\n%s" % \
                (parser.format_usage(),
                 "Use '--help' to get more comprehensive information.")
        else:
            helpstr = parser.format_help()
        # better for help2man
        helpstr = re.sub(r'optional arguments:', 'options:', helpstr)
        helpstr = re.sub(r'positional arguments:\n.*\n', '', helpstr)
        # convert all heading to have the first character uppercase
        headpat = re.compile(r'^([a-z])(.*):$', re.MULTILINE)
        helpstr = re.subn(headpat,
                          lambda match: r'{0}{1}:'.format(match.group(1).upper(),
                                                          match.group(2)),
                          helpstr)[0]
        # usage is on the same line
        helpstr = re.sub(r'^usage:', 'Usage:', helpstr)
        if option_string == '--help-np':
            usagestr = re.split(r'\n\n[A-Z]+', helpstr, maxsplit=1)[0]
            usage_length = len(usagestr)
            usagestr = re.subn(r'\s+', ' ', usagestr.replace('\n', ' '))[0]
            helpstr = '%s\n%s' % (usagestr, helpstr[usage_length:])
        print helpstr
        sys.exit(0)


def parser_add_common_args(parser, pos=None, opt=None, **kwargs):
    from . import common_args
    for i, args in enumerate((pos, opt)):
        if args is None:
            continue
        for arg in args:
            arg_tmpl = getattr(common_args, arg)
            arg_kwargs = arg_tmpl[2].copy()
            arg_kwargs.update(kwargs)
            if i:
                parser.add_argument(*arg_tmpl[i], **arg_kwargs)
            else:
                parser.add_argument(arg_tmpl[i], **arg_kwargs)


def parser_add_common_opt(parser, opt, names=None, **kwargs):
    from . import common_args
    opt_tmpl = getattr(common_args, opt)
    opt_kwargs = opt_tmpl[2].copy()
    opt_kwargs.update(kwargs)
    if names is None:
        parser.add_argument(*opt_tmpl[1], **opt_kwargs)
    else:
        parser.add_argument(*names, **opt_kwargs)

def get_build_option(optname, cli_input=None, family=None, default=None):
    """Determine build option value.

    If there was input from the command line it takes precedence. Otherwise
    an existing family-specific option value is chosen, or a non-family
    specific default is returned. If neither condition is valid, ``default`` is
    returned.

    Parameters
    ----------
    optname : str
      Option name
    cli_input
      Potential input from a corresponding command line option
    family : str
      Optional build family identifier
    default :
      Value to return if no information is available
    """
    from bigmess import cfg
    if not cli_input is None:
        # got something meaningful as a commandline arg -- got with it
        lgr.debug("using cmdline input '%s' for build option '%s'"
                  % (cli_input, optname))
        return cli_input
    if not family is None and cfg.has_option('build', '%s %s' % (family, optname)):
        val = cfg.get('build', '%s %s' % (family, optname))
        lgr.debug("using %s-specific configuration '%s' for build option '%s'"
                  % (family, val, optname))
        return val
    if cfg.has_option('build', optname):
        val = cfg.get('build', optname)
        lgr.debug("using generic configuration '%s' for build option '%s'"
                  % (val, optname))
        return val
    lgr.debug("using default configuration '%s' for build option '%s'"
               % (default, optname))
    return default

def get_path_cfg(option, cmdline_input, family, ensure_exists=False,
                 default=None):
    """Specialized frontend for build options that specify paths

    Parameters
    ----------
    option : str
      Base name of the build option
    cmdline_input : any
      Value given via cmdline option
    family : str
      Build family ID
    """
    path_ = get_build_option(option, cmdline_input, family, default)
    if path_ is None:
        return path_
    path_ = os.path.expanduser(os.path.expandvars(path_))
    lgr.debug("path for '%s' set to '%s'" % (option, path_))
    return path_

def get_dir_cfg(option, cmdline_input, family, ensure_exists=False,
                default=None):
    """Specialized frontend for build options that specify directories

    Parameters
    ----------
    option : str
      Base name of the build option
    cmdline_input : any
      Value given via cmdline option
    family : str
      Build family ID
    ensure_exists : bool
      If True, the directory is created of it doesn't exist.
    """
    dir_ = get_path_cfg(option, cmdline_input, family, ensure_exists=ensure_exists,
                        default=default)
    if ensure_exists and not os.path.exists(dir_):
        lgr.debug("create directory for '%s'" % option)
        os.makedirs(dir_)
    return dir_


def arg2bool(arg):
    if arg in (True, False, None):
        return arg
    arg = arg.lower()
    if arg in ['0', 'no', 'off', 'disable', 'false']:
        return False
    elif arg in ['1', 'yes', 'on', 'enable', 'true']:
        return True
    else:
        raise argparse.ArgumentTypeError(
                "'%s' cannot be converted into a boolean" % arg)
