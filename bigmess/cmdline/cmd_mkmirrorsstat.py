# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the bigmess package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Generate mirrors status webpage and update the time stamp in the deployed location.

"""

__docformat__ = 'restructuredtext'

# magic line for manpage summary
# man: -*- % generate APT sources lists

import argparse
import os
import logging

from os.path import join as opj

from bigmess import cfg

lgr = logging.getLogger(__name__)
parser_args = dict(formatter_class=argparse.RawDescriptionHelpFormatter)


def setup_parser(parser):
    parser.add_argument('-t', '--timestamp-dir', default=os.curdir,
                        help="""deployed directory where timestamp file to be kept""")
    parser.add_argument('-d', '--dest-dir', default=os.curdir,
                        help="""target directory for storing the generated page""")


def _literal_seconds(t):
    t = int(t)                            # assure seconds in int

    s = t % 60
    t /= 60

    m = t % 60; 
    t /= 60

    h = t % 24
    d = t/24

    names = ('day', 'hour', 'minute', 'second')
    values = (d, h, m, s)

    report = [ '%d %s%s' % (x, s, ('', 's')[x!=1]) for (x,s) in zip(values, names)
               if x or s == 'second'][:2]   # report only 2 most important ones

    return ' '.join(report)

def test_literal_seconds():
    assert(_literal_seconds(0) == '0 seconds')
    assert(_literal_seconds(10) == '10 seconds')
    assert(_literal_seconds(3602) == '1 hour 2 seconds')
    assert(_literal_seconds(3600*24*4) == '4 days 0 seconds')   # awkward -- TODO


def run(args):
    import codecs, time, urllib2
    from jinja2 import Environment, PackageLoader, FileSystemLoader
    jinja_env = Environment(loader=PackageLoader('bigmess'))
    template = jinja_env.get_template('mirrors_status.rst')

    stampfile = cfg.get('mirrors monitor', 'stampfile', 'TIMESTAMP')
    warn_threshold = cfg.getfloat('mirrors monitor', 'warn-threshold') * 3600

    lgr.debug("using stampfile %(stampfile)s", locals())

    mirrors_info = {}
    for mirror in cfg.options('mirrors'):

        mirror_url = cfg.get('mirrors', mirror)
        mirror_name = cfg.get('mirror names', mirror)

        try:
            url = '%(mirror_url)s/%(stampfile)s' % locals()
            u = urllib2.urlopen(url)
            stamp = u.read()
            age = (time.time() - int(stamp))   # age in hours
            age_str = _literal_seconds(age)
            if age > warn_threshold:
                lgr.warning("Mirror %(mirror)s is %(age_str)s old", locals())
                status = "**OLD**"
            else:
                status = "OK"
        except urllib2.URLError:
            lgr.error("Cannot fetch '%s'" % url)
            # Here ideally we should revert to use previously known
            # state
            age_str = None
            status = "**N/A**"

        mirrors_info[mirror] = [mirror_url, mirror_name, age, age_str, status]

    page = template.render(
        timestamp=time.time(),
        info=mirrors_info)

    with codecs.open(opj(args.dest_dir, 'mirrors_status.rst' ), 'wb', 'utf-8') as of:
        of.write(page)

