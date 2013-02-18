.. -*- mode: rst; fill-column: 78; indent-tabs-mode: nil -*-
.. vi: set ft=rst sts=4 ts=4 sw=4 et tw=79:
  ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ###
  #
  #   See COPYING file distributed along with the bigmess package for the
  #   copyright and license terms.
  #
  ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ###

.. _chap_build_packages:

**********************************************
Building packages for many target environments
**********************************************

Sometimes is is necessary to build source packages for a number of different
target environments. Let's say a research institute made a smart move and only
operates Debian-based machines. Some of these machines are running Debian
stable, some developer machines have been upgraded to Debian testing, and
a few machines are running the latest Ubuntu LTS release. Typical tasks for
a sysadmin are to deploy some in-house research on all these machines, or to
"backport" a more recent version of a utility package from Debian testing
and make it also available on all machines.

There are various existing solutions to this problem. The approach that bigmess
is taking is to create a thin wrapper around pbuilder_ or cowbuilder_ that
allow for setting up various build environments in chroots and using them to
build packages for all desired target environments on a single machine (if
hardware architectures are compatible). Information on necessary build
environments can be specified in a configuration file. Here is an example::

  [build]
  build basedir = /home/exampleuser/buildplace
  chroot basedir = /home/exampleuser/chroots
  result directory = /home/exampleuser/buildresults

  environments = properdebian-squeeze properdebian-wheezy

  properdebian mirror = http://ftp.debian.org/debian
  properdebian components = main
  properdebian architectures = amd64 i386

In the first three lines of the ``build`` section we specify where we want to
perform the actual build process, where the build environments shall be stored,
and where to place built packages.  Afterwards we specify the current Debian
stable "squeeze" and the current testing version "wheezy" as target
environments. We are using the codenames under which they are available in the
Debian archive. Note that both codenames are prefixed with ``properdebian``.
This is an arbitrarily chosen name for a family of our build environments that
share a common configuration. What remains of the ``build`` section is this
common configuration for the ``properdebian`` family. It contains a Debian
mirror URL, a list of architectures to build for, and mirror components to
enable.

With this configuration placed in a file ``bigmess.cfg`` in the current
directory, or in ``~/.config/bigmess.cfg`` we can create all desired build
environments with a single command::

  % bigmess bootstrap_buildenv

Internally this command will call pbuilder_ to create the chroots. This
requires root permissions, so pbuilder_ is called via sudo. Therefore you will
either be prompted for a password, or you configure sudo accordingly.

After this was successfully done, we are ready to build packages. Let's say we
need to build a package for all of our Debian squeeze machines::

  % bigmess build_pkg --env properdebian-squeeze somepackage_0.1-1.dsc

When this command returns successfully, we will have packages for both i386 and
amd64 waiting for us in ``/home/exampleuser/buildresults``.

The minimal build environments need to be updated from time to time to account
for updates in the base installation. This can be done for all environments at
once by running::

  % bigmess update_buildenv

Whenever something is not working as expected it could be necessary to
investigate the situation in the actual build environment. This is supported
by the ``run_buildenv`` command::

  % bigmess run_buildenv --env properdebian squeeze --arch i386 --mount /home


Backporting
===========

A little more interesting is the use case where we want to build a single
source package for all the machines and their operating system versions we need
to care for. To do this correctly, it is not sufficient to do a plain build. We
need to mangle the package version to ensure a proper upgrade path. For
example, if we install a backport of ``example_1.0-1`` on a Debian squeeze
machine, we need to make sure that the version in or for Debian wheezy has a
higher version number, so that APT will also update this package. This is
typically done by adding a suffix to the original package version. Bigmess can
help with this too. All that need to be done is to configure a suitable
version suffix for each target environment, by adding a section like the
following to the configuration file::

  [codename backport ids]
  squeeze = mybp60
  wheezy = mybp70

With this configuration in place we can build binary packages for all operating
system releases with a single command::

  % bigmess build_pkg --backport somepackage_0.1-1.dsc

According to our configuration this will yield::

  somepackage_0.1-1~nd60_amd64.changes
  somepackage_0.1-1~nd60_i386.changes
  somepackage_0.1-1~nd70_amd64.changes
  somepackage_0.1-1~nd70_i386.changes

Internally, the backporting is done via the ``backport-dsc`` command (that is
also part of bigmess). ``backport-dsc`` generates a new source package which is
then built. ``backport-dsc`` can do more than just version mangling. It supports
patch series that are conditionally applied depending on the target
distribution, and supports patching the Debian package itself, for example, to
adjust dependencies for particular target environments.

.. _pbuilder: http://packages.debian.org/sid/pbuilder
.. _cowbuilder: http://packages.debian.org/sid/cowbuilder

Build packages in parallel for more speed
=========================================

Although the commands above  already facilitate some aspects of a package
handling routine they all operate in a serial fashion, hence building for 20
environments takes at least 20 times the duration of a single build. This is
not so nice. There are some systems that allow for setting up build farms
with a bunch of build-slaves. Bigmess, however, takes a different approach by
using a general purpose batch scheduler to carry out package builds. For this
purpose bigmess can interface with the HTCondor_ and submit build jobs to a
Condor pool with the ``build_pkg_condor`` command.
