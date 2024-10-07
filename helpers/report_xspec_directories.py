#!/usr/bin/env python

# SPDX-License-Identifier: GPL-3.0-or-later

"""Return the library and include directories.

This should just be $HEADAS/lib and $HEADAS/include, except for the
fact that the CXC xspec-modelsonly conda package does things a little
differently (or, perhaps, that XSPEC doesn't have the equivalent of a
share/ directory in which to place the extra files).

It is assumed that the HEADAS environment variable exists.

"""

from pathlib import Path
import os

HEADAS_ENV = os.getenv('HEADAS')
HEADAS = Path(HEADAS_ENV)

if (HEADAS / 'include').is_dir():
    base_path = HEADAS
else:
    base_path = (HEADAS / '..').resolve()

xspec_libdir = base_path / 'lib'
xspec_incdir = base_path / 'include'

if not xspec_libdir.is_dir():
    sys.stderr.write('###########################################\n')
    sys.stderr.write('ERROR: unable to find HEADAS lib directory.\n')
    sys.stderr.write(str(HEADAS / platlibdir))
    sys.stderr.write(str(HEADAS / '..' / platlibdir))
    sys.stderr.write('###########################################\n')
    sys.exit(1)

if not xspec_incdir.is_dir():
    sys.stderr.write('###########################################\n')
    sys.stderr.write('ERROR: unable to find HEADAS lib directory.\n')
    sys.stderr.write(str(HEADAS / 'include'))
    sys.stderr.write(str(HEADAS / '..' / 'include'))
    sys.stderr.write('###########################################\n')
    sys.exit(1)

print(xspec_incdir)
print(xspec_libdir)
