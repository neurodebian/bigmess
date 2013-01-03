# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the bigmess package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
""" """

import os
import sys
import bigmess
from distutils.core import setup
from glob import glob


__docformat__ = 'restructuredtext'

extra_setuptools_args = {}
if 'setuptools' in sys.modules:
    extra_setuptools_args = {'tests_require': ['nose'],
                             'test_suite': 'nose.collector',
                             'zip_safe': False,
                             'extras_require': {'doc': 'Sphinx >= 0.3',
                                                'test': 'nose >= 0.10.1'}}


def main(**extra_args):
    setup(name='bigmess',
          version=bigmess.__version__,
          author='Michael Hanke and the bigmess developers',
          author_email='michael.hanke@gmail.com',
          license='MIT License',
          url='https://github.com/neurodebian/bigmess',
          download_url='https://github.com/neurodebian/bigmess/tags',
          description='test and evaluate heterogeneous data processing pipelines',
          long_description=open('README.rst').read(),
          classifiers=["Development Status :: 3 - Alpha",
                       "Environment :: Console",
                       "License :: OSI Approved :: MIT License",
                       "Operating System :: OS Independent",
                       "Programming Language :: Python",
                       ],
          platforms="OS Independent",
          provides=['bigmess'],
          # please maintain alphanumeric order
          packages=['bigmess',
                    'bigmess.cmdline',
                    ],
          package_data={'bigmess': ['bigmess.cfg']},
          scripts=glob(os.path.join('bin', '*'))
          )

if __name__ == "__main__":
    main(**extra_setuptools_args)
