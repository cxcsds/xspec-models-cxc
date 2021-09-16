"""Build the xspec_models_cxc module"""

import os
import pathlib
import sys

from setuptools import setup

from pybind11.setup_helpers import Pybind11Extension, build_ext
from pybind11 import get_cmake_dir

__version__ = "0.0.2"

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

if not modelfile.is_file():
    sys.stderr.write('ERROR: unable to find HEADAS environment variable.\n')
    sys.exit(1)


# It would be nice to query for this from the system,
# such as with pkg_config.
#
xspec_libs = ['XSFunctions', 'XSUtil', 'XS', 'hdsp_6.29',
              'cfitsio', 'CCfits_2.6', 'wcs-7.3.1']

ext_modules = [
    Pybind11Extension("xspec_models_cxc",
                      ["src/xspec.cxx"],
                      cxx_std=11,
                      include_dirs=[str(HEADAS / 'include')],
                      library_dirs=[str(HEADAS / 'lib')],
                      libraries=xspec_libs,
                      define_macros = [('VERSION_INFO', __version__)],
                      ),
]

# How do we include the model.dat file?

setup(
    name="xspec_models_cxc",
    version=__version__,
    license="GNU GPL v3",
    author="Douglas Burke",
    author_email="dburke@cfa.harvard.edu",
    url="https://github.com/cxcsds/xspec-models-cxc",
    description="Access the XSPEC models from Python **experimental**",
    long_description=open('README.md', 'rt').read(),
    long_description_content_type="text/markdown",
    ext_modules=ext_modules,
    extras_require={"test": "pytest"},
    cmdclass={"build_ext": build_ext},
    zip_safe=False,
    platforms='Linux, Mac OS X',
    python_requires='~=3.7',
    classifiers=[
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: C',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Scientific/Engineering :: Astronomy',
        'Topic :: Scientific/Engineering :: Physics'
    ],
)
