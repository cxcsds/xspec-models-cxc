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
from pathlib import Path
import subprocess
import sys
import sysconfig

from setuptools import setup

from pybind11.setup_helpers import Pybind11Extension, build_ext

# How do we use local modules like helpers? This is a hack based on
# discussions around
# https://github.com/python-versioneer/python-versioneer/issues/193
#
# Note that we do not treat the helpers code as Python modules that
# can be imported, but as code that has to be run and returns a
# value. This is awkward, but may better separate the build logic from
# the build implementation.
#
sys.path.append(os.path.dirname(__file__))

from helpers import template

# How can we best set this up?
__version__ = "0.0.30"


def helper(script: str, *args: str) -> list[str]:
    """Run the helper script and return the STDOUT by line."""

    exefile = f"helpers/{script}"
    comm = ["python", exefile] + list(args)
    out = subprocess.run(comm, capture_output=True, check=True, text=True)
    return out.stdout.strip().split('\n')


# Access the model.dat file. This also checks HEADAS is set up.
#
modeldat = Path(helper("report_xspec_modelfile.py")[0])

# Where are the include and library directories for XSPEC?
#
dirs = helper("report_xspec_directories.py")
xspec_inc_dir = Path(dirs[0])
xspec_lib_dir = Path(dirs[1])

# What are the libraries we need to use to compile against XSPEC? This
# logic is the one that likely needs to change when there is a new
# version (not patch) of XSPEC released.
#
xspec_libs = helper("report_xspec_libraries.py", str(xspec_lib_dir))

# What version of XSPEC is in use?
#
def get_compiler() -> str:
    """Guess the C++ compiler to use.

    If the CXX environment variable is used then use that, otherwise
    try g++ and then clang.

    """
    compiler = os.getenv("CXX")
    if compiler is not None:
        return compiler

    # Do not try anything too clever here.
    #
    for compiler in ["g++", "clang++"]:
        args = [compiler, "--version"]

        try:
            subprocess.run(args, check=True)
            return compiler
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass

    raise ValueError("Use the CXX environment variable to select the C++ compiler to use")


def compile_code(inc_path, lib_path):
    """Compile the code. Specific to report_xspec_version."""

    basename = "report_xspec_version"
    helpers = Path("helpers")

    compiler = get_compiler()
    print(f"** Using compiler: {compiler}")
    args = [compiler,
            str(helpers / f"{basename}.cxx"),
            "-o", str(helpers / basename),
            f"-Wl,-rpath,{lib_path}",
            f"-I{inc_path}",
            f"-L{lib_path}",
            "-lXSUtil"
        ]

    subprocess.run(args, check=True)
    return helpers / basename


compiled = compile_code(inc_path=xspec_inc_dir,
                        lib_path=xspec_lib_dir)

proc = subprocess.run([str(compiled)], check=True,
                      stdout=subprocess.PIPE, text=True)
xspec_version = proc.stdout.strip()
print(f"Building against XSPEC: '{xspec_version}'")

macros = [('VERSION_INFO', __version__)]

out_dir = Path('src')

# Note: we need access to the src/include directory - can we just
# hard-code this path or access it via some setuptools method?
#
include_dir = out_dir / 'include'
if not include_dir.is_dir():
    sys.stderr.write(f'ERROR: unable to find {include_dir}/')
    sys.exit(1)

######################################################################
#
# Process the model.dat file and the templates to create the module
# (C++ and Python).
#
compiled_code = out_dir / 'xspec_models_cxc' / 'xspec.cxx'
python_code = out_dir / 'xspec_models_cxc' / '__init__.py'

helper("apply_templates.py", str(modeldat), xspec_version,
       str(compiled_code), str(python_code))

######################################################################
#
# Create the extension module.
#
ext_modules = [
    Pybind11Extension("xspec_models_cxc._compiled",
                      [str(compiled_code)],
                      depends=[str(modeldat),
                               str('template/xspec.cxx')  # is this useful?
                      ],
                      cxx_std=11,
                      include_dirs=[str(include_dir),
                                    str(xspec_inc_dir)],
                      library_dirs=[str(xspec_lib_dir)],
                      libraries=xspec_libs,
                      define_macros=macros
                  ),
]

setup(
    version=__version__,
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
)
