"""Generate the code to be built based on the model.dat file.

Note that any error in creating the template will raise a
SystemExit exception.

At what point does it become worth using a templating system like
Jinja2?

"""

# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path
import sys
from typing import Sequence

from parse_xspec.models import ModelDefinition, \
    parse_xspec_model_description

import utils_template


def replace_term(txt: str, term: str, replace: str) -> str:
    """Replace the first term with replace in txt"""

    idx = txt.find(term)
    if idx < 0:
        sys.stderr.write(f'ERROR: unable to find {term}\n')
        sys.exit(1)

    return txt[:idx] + replace + txt[idx + len(term):]


def apply_compiled(models: Sequence[ModelDefinition],
                   template: Path,
                   outfile: Path
                   ) -> None:
    """Convert the template for the compiled code."""

    addmodels = []
    mulmodels = []
    conmodels = []
    mstrs = []
    for model in models:
        mdef, mtype, mdesc = utils_template.wrapmodel_compiled(model)
        if mtype == "Add":
            addmodels.append(mdesc)
        elif mtype == "Mul":
            mulmodels.append(mdesc)
        elif mtype == "Con":
            conmodels.append(mdesc)
        else:
            assert False  # should not happen

        mstrs.append(mdef)

    with template.open(mode='rt') as ifh:
        out = ifh.read()

        out = replace_term(out, '@@ADDMODELS@@', '\n'.join(addmodels))
        out = replace_term(out, '@@MULMODELS@@', '\n'.join(mulmodels))
        out = replace_term(out, '@@CONMODELS@@', '\n'.join(conmodels))
        out = replace_term(out, '@@MODELS@@', '\n'.join(mstrs))

    with outfile.open(mode='wt') as ofh:
        ofh.write(out)


def apply_python(modelfile: Path,
                 models: Sequence[ModelDefinition],
                 template: Path,
                 xspec_version: str,
                 outfile: Path
                 ) -> None:
    """Convert the template for the Python code.

    xspec_version : str
        The XSPEC library we are building against, including the patch
        level.

    """

    mstrs = []
    for model in models:
        mname, mdef = utils_template.wrapmodel_python(model)
        mstrs.append(f"    '{mname}': {mdef}")

    with template.open(mode='rt') as ifh:
        out = ifh.read()

        out = replace_term(out, '@@MODELDAT@@', str(modelfile))
        out = replace_term(out, '@@PYINFO@@', ',\n'.join(mstrs))
        out = replace_term(out, '@@XSPECVER@@', xspec_version)

    with outfile.open(mode='wt') as ofh:
        ofh.write(out)


def find_models(modelfile: Path
                ) -> tuple[list[ModelDefinition], list[ModelDefinition]]:
    """Extract the models we can support from the model.dat file

    The return values are the supported then unsupported models.
    """

    if not modelfile.is_file():
        sys.stderr.write(f'ERROR: unable to find model.dat file: {modelfile}.\n')
        sys.exit(1)

    allmodels = parse_xspec_model_description(modelfile)
    if len(allmodels) == 0:
        sys.stderr.write(f'ERROR: unable to parse model.dat file: {modelfile}\n')
        sys.exit(1)

    supported, unsupported = utils_template.select_models(allmodels)
    if len(supported) == 0:
        sys.stderr.write(f'ERROR: unable to find any models in: {modelfile}\n')
        sys.exit(1)

    return supported, unsupported


def report(models, unsupported):
    """Report on what models we are using and not using."""

    print("###############################################")
    print(f"Number of supported models:     {len(models)}")
    print(f"          unsupported:          {len(unsupported)}")
    print("")

    def count_type(label, mtype):
        matches = [m for m in models if m.modeltype == mtype]
        print(f"   {label:27s}  {len(matches)}")

    def count_lang(label):
        matches = [m for m in models if m.language == label]
        print(f"   {label:27s}  {len(matches)}")

    count_type("additive", "Add")
    count_type("multiplicative", "Mul")
    count_type("convolution", "Con")
    print("")

    count_lang("C++ style")
    count_lang("C style")
    count_lang("Fortran - single precision")
    count_lang("Fortran - double precision")
    print("")

    if len(unsupported) > 0:
        print("Unsupported:")
        for i, mdl in enumerate(unsupported, 1):
            print(f"   {i}. {mdl.name} - {mdl.modeltype}/{mdl.language}")

        print("")

    print("###############################################")
