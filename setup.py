"""Build the xspec_models_cxc module

The interface is auto-generated based on the model.dat file from the
HEASARC installation. The HEADAS environment variable must be set.

At present only XSPEC 12.12.0 (and patches) is supported, and the
build is very fragile.

"""

import os
import pathlib
import sys

from setuptools import setup

from pybind11.setup_helpers import Pybind11Extension, build_ext
from pybind11 import get_cmake_dir

# Should probably use a templating system like Jinja2

from parse_xspec.models import parse_xspec_model_description

__version__ = "0.0.10"

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

allmodels = parse_xspec_model_description(modelfile)
if len(allmodels) == 0:
    sys.stderr.write(f'ERROR: unable to parse model.fat file: {modelfile}\n')
    sys.exit(1)

# Filter to the ones we care about
models = [m for m in allmodels if m.modeltype in ['Add', 'Mul']]
if len(models) == 0:
    sys.stderr.write(f'ERROR: unable to find any models in: {modelfile}\n')
    sys.exit(1)

# Create the code we want to compile
#
# When does it become worth using Jinja2 or equivalent?
#
template_dir = pathlib.Path('template')
out_dir = pathlib.Path('src')
filename = pathlib.Path('xspec.cxx')
template = template_dir / filename
outfile = out_dir / filename

# Ugly information flow here
addmodels = []
mulmodels = []
f77models = []
cxxmodels = []
cmodels = []

def wrapmod(model):

    npars = len(model.pars)
    if model.modeltype == 'Add':
        mtype = 'additive'
        addmodels.append(model.name)
    elif model.modeltype == 'Mul':
        mtype = 'multiplicative'
        mulmodels.append(model.name)
    else:
        assert False, model.modeltype

    out = f'    m.def("{model.name}", wrapper'

    if model.language == 'Fortran - single precision':
        out += f'_f<{model.funcname}_'
        f77models.append(model.funcname)
    elif model.language == 'C++ style':
        out += f'_C<C_{model.funcname}'
        cxxmodels.append(model.funcname)
    elif model.language == 'C style':
        out += f'_C<{model.funcname}'
        cmodels.append(model.funcname)
    else:
        assert False, (model.name, model.funcname, model.language)

    out += f', {npars}>, '
    out += f'"The XSPEC {mtype} {model.name} model ({npars} parameters).",'
    out += '"pars"_a,"energies"_a,"spectrum"_a=1'
    if not model.language.startswith('Fortran'):
        out += ',"initStr"_a=""'
    out += ');'
    return out

mstrs = [wrapmod(m) for m in models]


def replace_term(txt, term, replace):
    """Replace term with replace in txt"""

    idx = txt.find(term)
    if idx < 0:
        sys.stderr.write(f'ERROR: invalid template {template}\n')
        sys.exit(1)

    return txt[:idx] + replace + txt[idx + len(term):]


with template.open(mode='rt') as ifh:
    out = ifh.read()
    out = replace_term(out, '@@ADDMODELS@@', '\n'.join(addmodels))
    out = replace_term(out, '@@MULMODELS@@', '\n'.join(mulmodels))
    out = replace_term(out, '@@MODELS@@', '\n'.join(mstrs))

out_dir.mkdir(exist_ok=True)
with outfile.open(mode='wt') as ofh:
    ofh.write(out)

# Summarize
#
print("###############################################")
print(f"Number of models:  {len(mstrs)}")
print(f"   additive:       {len(addmodels)}")
print(f"   multiplicative: {len(mulmodels)}")
print(f"   C++:            {len(cxxmodels)}")
print(f"   C:              {len(cmodels)}")
print(f"   FORTRAN:        {len(f77models)}")
print("###############################################")


# It would be nice to query for this from the system,
# such as with pkg_config.
#
xspec_libs = ['XSFunctions', 'XSUtil', 'XS', 'hdsp_6.29',
              'cfitsio', 'CCfits_2.6', 'wcs-7.3.1']

ext_modules = [
    Pybind11Extension("xspec_models_cxc",
                      [str(outfile)],
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
