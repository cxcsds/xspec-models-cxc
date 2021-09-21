"""Build the xspec_models_cxc module

The interface is auto-generated based on the model.dat file from the
HEASARC installation. The HEADAS environment variable must be set.

At present only XSPEC 12.12.0 (and patches) is supported, and the
build is very fragile.

"""

# SPDX-License-Identifier: GPL-3.0-or-later

import os
import pathlib
import sys

from setuptools import setup

from pybind11.setup_helpers import Pybind11Extension, build_ext

# How do we use local modules like helpers? This is a hack based on
# discussions around
# https://github.com/python-versioneer/python-versioneer/issues/193
#
sys.path.append(os.path.dirname(__file__))

from helpers import template

__version__ = "0.0.18"

# Check HEASARC is set up. The following does not provide a useful
# message from 'pip install' so how do we make it more meaningful?
#
HEADAS = os.getenv('HEADAS')
if HEADAS is None:
    sys.stderr.write('ERROR: unable to find HEADAS environment variable.\n')
    sys.exit(1)

HEADAS = pathlib.Path(HEADAS)

modelfile = HEADAS / '../spectral/manager/model.dat'
modelfile = modelfile.resolve()

out_dir = pathlib.Path('src')
out_dir.mkdir(exist_ok=True)

info = template.apply(modelfile, out_dir)

# It would be nice to query for this from the system,
# such as with pkg_config.
#
xspec_libs = ['XSFunctions', 'XSUtil', 'XS', 'hdsp_6.29',
              'cfitsio', 'CCfits_2.6', 'wcs-7.3.1']

ext_modules = [
    Pybind11Extension("xspec_models_cxc._compiled",
                      [str(info['outfile'])],
                      depends=[str(modelfile), str(template)],  # is this useful?
                      cxx_std=11,
                      include_dirs=[str(HEADAS / 'include')],
                      library_dirs=[str(HEADAS / 'lib')],
                      libraries=xspec_libs,
                      define_macros = [('VERSION_INFO', __version__)],
                      ),
]

setup(
    version=__version__,
    ext_modules=ext_modules,
    extras_require={"test": "pytest"},
    cmdclass={"build_ext": build_ext},
)
