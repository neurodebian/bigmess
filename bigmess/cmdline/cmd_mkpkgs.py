# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the bigmess package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Generate package pages in reStructured Text format.

"""

__docformat__ = 'restructuredtext'

# magic line for manpage summary
# man: -*- % generate package pages

import argparse
import os
import re
import codecs
import logging

from os.path import join as opj

from bigmess import cfg
from .helpers import parser_add_common_args
from ..utils import load_db

lgr = logging.getLogger(__name__)
parser_args = dict(formatter_class=argparse.RawDescriptionHelpFormatter)


def setup_parser(parser):
    parser_add_common_args(parser, opt=('pkgdb',))
    parser.add_argument('-d', '--dest-dir', default=os.curdir,
                        help="""target directory for storing the generated pages""")
    parser.add_argument('-t', '--template',
                        help="""Path to a custom template file""")
    parser.add_argument('--pkgs', '--packages',
                        nargs='+',
                        help="""render pages for these binary packages""")


def _underline_text(text, symbol):
    underline = symbol * len(text)
    return '%s\n%s\n' % (text, underline)


def _proc_long_descr(lines):
    lines = [l.replace('% ', '%% ') for l in lines]
    lines = [l.replace(r'\t', '    ') for l in lines]
    re_leadblanks = re.compile("^ *")
    re_itemized = re.compile("^[o*-+] +")
    re_itemized_gr = re.compile("^( *)([-o*+] +)?(.*?)$")

    def unwrap_lines(lines):
        out = []
        indent_levels = [-1]
        for l in lines:
            match = re_itemized_gr.search(l).groups()
            if ((len(match[0]) in indent_levels and match[1] is None)
                or (len(match[0]) > max(indent_levels) + 4)) \
                and match[2].strip() != '.':
                # append to previous
                if not out[-1].endswith(" "):
                    out[-1] += " "
                out[-1] += match[2]
            else:
                out.append(l)

            indent_levels = [len(match[0])]
            if match[1] is not None:
                indent_levels += [len(match[0]) + len(match[1])]
            if match[2].strip() == '.':
                # reset though if '.'
                indent_levels = [-1]
        return out

    def dedent_withlevel(lines):
        """Dedent `lines` given in a list provide dedented lines and
        how much was dedented
        """
        nleading = min([re_leadblanks.search(l).span()[1]
                        for l in lines])
        return [l[nleading:] for l in lines], nleading

    def block_lines(ld, level=0):
        # so we got list of lines
        # dedent all of them first
        ld, level = dedent_withlevel(ld)

        # lets collect them in blocks/paragraphs
        # 1. into paragraphs split by '.'
        blocks, block = [], None

        # next block can begin if
        #  1.  . line
        #  2. it was an itemized list and all items begin with
        #     the same symbol or get further indented accordingly
        #     so let's first check if it is an itemized list
        itemized_match = re_itemized.search(ld[0])
        if itemized_match:
            allow_indents = " " * itemized_match.span()[1]
        else:
            allow_indents = None
        for l in ld:
            if block is None or l.strip() == '.'\
                    or (len(l) and (len(block) and (
                        (l.startswith(' ') and not block[-1].startswith(' '))
                        or
                        (not l.startswith(' ') and block[-1].startswith(' '))))):
                block = []
                blocks.append(block)
            if l.strip() != '.':
                block.append(l)
        if len(blocks) == 1:
            return blocks[0]
        else:
            return [block_lines(b, level + 1) for b in blocks if len(b)]

    def blocks_to_rst(bls, level=0):
        # check if this block is an itemized beast
        #itemized_match = re_itemized_gr.search(bls[0][0])
        #if itemized_match:
        #    res += ' 'allow_indents = " "*itemized_match.span()[1]
        out = ''
        for b in bls:
            if isinstance(b, list):
                if len(b) == 1:
                    out += " " * level + b[0] + '\n\n'
                else:
                    out += blocks_to_rst(b, level + 1)
            else:
                e = " " * level + b + '\n'
                if not re_itemized.search(b):
                    pass
                    #e += '\n'
                elif len(e) and e[0] == ' ':
                    # strip 1 leading blank
                    e = e[1:]
                out += e
        out += '\n'
        return out

    ld = unwrap_lines(lines)
    bls = block_lines(ld)
    return blocks_to_rst(bls)


def _gen_pkg_page(pname, db, pkg_template):
    bindb = db['bin']
    srcdb = db['src']
    binpkginfo = bindb[pname]
    srcpkginfo = srcdb[binpkginfo['src_name']]
    pkginfo = {}
    pkginfo.update(binpkginfo)
    pkginfo.update(srcpkginfo)

    if 'short_description' in pkginfo:
        title = _underline_text('**%s** -- %s' % (pname,
                                                  pkginfo['short_description']),
                                '*')
    else:
        title = _underline_text('**%s**' % pname, '*')
    if 'long_description' in pkginfo:
        long_descr = _proc_long_descr(pkginfo['long_description'])
    else:
        long_descr = 'No description available.'

    availability = dict([(cfg.get('release names', k), v)
                         for k, v in binpkginfo['in_suite'].iteritems()])
    page = pkg_template.render(
        cfg=cfg,
        pname=pname,
        title=title,
        description=long_descr,
        availability=availability,
        **pkginfo)
    return page


def run(args):
    from jinja2 import Environment, PackageLoader, FileSystemLoader
    lgr.debug("using package DB at '%s'" % args.pkgdb)
    if not args.template is None:
        templ_dir = os.path.dirname(args.template)
        templ_basename = os.path.basename(args.template)
        jinja_env = Environment(loader=FileSystemLoader(templ_dir))
        template = jinja_env.get_template(templ_basename)
    else:
        jinja_env = Environment(loader=PackageLoader('bigmess'))
        template = jinja_env.get_template('binary_pkg.rst')
    # read entire DB
    db = load_db(args.pkgdb)
    if args.pkgs is None:
        lgr.debug("render pages for all known binary packages")
        pkgs = db['bin']
    else:
        lgr.debug("render pages given list of binary packages only")
        pkgs = args.pkgs

    for pkg in pkgs:
        page = _gen_pkg_page(pkg, db, template)
        of = codecs.open(opj(args.dest_dir, '%s.rst' % pkg), 'wb', 'utf-8')
        of.write(page)
        of.close()
