"""Build the xspec_models_cxc module

The interface is auto-generated based on the model.dat file from the
HEASARC installation. The HEADAS environment variable must be set and
the library environment set up to point to all the required libraries
(so, it is likely that `source $HEADAS/headas-init.sh` or equivalent
has been performed).

At present only XSPEC 12.12.1 to 12.14.1 is supported (newer versions
may work and older versions see limited to no testing), and the build
is very fragile (for instance, there has been no macOS testing).

There is also support for the CXC xspec-modelsonly conda installation
of XSPEC, which does some "interesting" things to accomodate the
HEASARC/XSPEC installation within a conda-like environment.

"""

# SPDX-License-Identifier: GPL-3.0-or-later

import glob
import os
import pathlib
import sys
import sysconfig

from setuptools import setup

from pybind11.setup_helpers import Pybind11Extension, build_ext

# How do we use local modules like helpers? This is a hack based on
# discussions around
# https://github.com/python-versioneer/python-versioneer/issues/193
#
sys.path.append(os.path.dirname(__file__))

from helpers import template
from helpers.identify_xspec import get_xspec_macros

# How can we best set this up?
__version__ = "0.0.30"

# Check HEASARC is set up. The following does not provide a useful
# message from 'pip install' so how do we make it more meaningful?
#
HEADAS = os.getenv('HEADAS')
if HEADAS is None:
    sys.stderr.write('##################################################\n')
    sys.stderr.write('ERROR: unable to find HEADAS environment variable.\n')
    sys.stderr.write('##################################################\n')
    sys.exit(1)

HEADAS = pathlib.Path(HEADAS)

modelfile = HEADAS / '../spectral/manager/model.dat'
modelfile = modelfile.resolve()
if not modelfile.is_file():
    sys.stderr.write('##################################################\n')
    sys.stderr.write('ERROR: model.dat file not found:\n')
    sys.stderr.write(str(modelfile) + '\n')
    sys.stderr.write('##################################################\n')
    sys.exit(1)

out_dir = pathlib.Path('src')
out_dir.mkdir(exist_ok=True)

# It would be nice to query for this from the system, such as with
# pkg_config. We can try and find the versions directly instead.
#
#xspec_libs = ['XSFunctions', 'XSUtil', 'XS', 'hdsp_6.29',
#              'cfitsio', 'CCfits_2.6', 'wcs-7.3.1']

# Ideally we can use HEADAS but if this is using the CXC
# xspec-modelsonly package then things get a bit-more complex.
#
if (HEADAS / 'include').is_dir():
    base_path = HEADAS
else:
    base_path = (HEADAS / '..').resolve()

# There's some attempt to be platform independent, but
# is it worth it?
#
if sysconfig.get_config_var("WITH_DYLD"):
    suffix = ".dylib"
else:
    # Should this just be hard-coded?
    suffix = sysconfig.get_config_var('SHLIB_SUFFIX')

platlibdir = sysconfig.get_config_var('platlibdir')

xspec_libdir = base_path / platlibdir
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

# The tricky thing is that we have XSFunctions, XSUtil, and XS as
# arguments. So we can not just look for XS*, as that will match
# multiple libraries. We also don't want to include all matches to XS
# as there are a number of matches we do not need.
#
def match(name):
    # Would it make sense to take the lib prefix from sysconfig?
    head = f"lib{name}{suffix}"
    ms = glob.glob(str(xspec_libdir / head))
    if len(ms) == 1:
        return name

    head = f"lib{name}_*{suffix}"
    ms = glob.glob(str(xspec_libdir / head))
    if len(ms) == 1:
        return pathlib.Path(ms[0]).stem[3:]

    head = f"lib{name}-*{suffix}"
    ms = glob.glob(str(xspec_libdir / head))
    if len(ms) == 1:
        return pathlib.Path(ms[0]).stem[3:]

    raise OSError(f"Unable to find a match for lib{name}*{suffix} in {xspec_libdir}")


xspec_libs = []
for libname in ["XSFunctions", "XSUtil", "XS", "hdsp",
                "cfitsio", "CCfits", "wcs"]:
    # Note: not all names are versioned
    xspec_libs.append(match(libname))


xspec_version, xspec_macros = get_xspec_macros(base_path)
print(f"Building against XSPEC: '{xspec_version}'")
print(f"   {xspec_macros[1][1]} {xspec_macros[2][1]} {xspec_macros[3][1]}")
if len(xspec_macros)> 4:
    print(f"   patch: {xspec_macros[4][1]}")

# Create the code now we believe we have the XSPEC installation
# sorted out.
#
info = template.apply(modelfile, xspec_version, out_dir)

# Note: we need access to the src/include directory - can we just
# hard-code this path or access it via some setuptools method?
#
include_dir = out_dir / 'include'
if not include_dir.is_dir():
    sys.stderr.write(f'ERROR: unable to find {include_dir}/')
    sys.exit(1)

macros = [('VERSION_INFO', __version__)] + xspec_macros

ext_modules = [
    Pybind11Extension("xspec_models_cxc._compiled",
                      [str(info['outfile'])],
                      depends=[str(modelfile),
                               str(template)],  # is this useful?
                      cxx_std=11,
                      include_dirs=[str(include_dir),
                                    str(xspec_incdir)],
                      library_dirs=[str(xspec_libdir)],
                      libraries=xspec_libs,
                      define_macros = macros
                  ),
]

setup(
    version=__version__,
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
)
