#  Copyright (C) 2024
#  Smithsonian Astrophysical Observatory
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Code used to build the module.

This code is used to build the module *AND* is also included
in the module (i.e. is inserted into xspec_models_cxc.utils).

"""

from pathlib import Path
from typing import Sequence

from parse_xspec.models import ModelDefinition


#@@START@@

def select_models(models: Sequence[ModelDefinition]
                  ) -> tuple[list[ModelDefinition], list[ModelDefinition]]:
    """Identify the models that can be used from Python.

    Select those models that this module can provide access to from
    Python.  The reasons for a model being unsuported include: support
    could be added but it just hasn't yet, there is a new model type
    in XSPEC that this package does not yet understand, and models
    that are not really intended for use outside of XSPEC directly
    (such as mixing models).

    Parameters
    ----------
    models
        The models provided in the model.dat file (normally created
        by `parse_xspec.models.parse_xspec_model_description`.

    Returns
    -------
    supported, unsupported
        Those models that can be used and those that can not.

    Notes
    -----
    Only additive, multiplicative, and convolution models are
    currently supported. All four "language styles" - that is C, C++,
    FORTRAN 4-byte real, and FORTRAN 8-byte real are supported.

    """

    # Filter to the ones we care about.
    #
    supported1 = []
    unsupported = []
    for m in models:
        if m.modeltype in ['Add', 'Mul', 'Con']:
            supported1.append(m)
        else:
            unsupported.append(m)

    # A sanity check (at present this should be all supported
    # "language styles").
    #
    allowed_langs = ["Fortran - single precision",
                     "Fortran - double precision",
                     "C style",
                     "C++ style"]
    supported = []
    for m in supported1:
        if m.language in allowed_langs:
            supported.append(m)
        else:
            unsupported.append(m)

    return supported, unsupported


def get_npars(npars: int) -> str:
    """Return the number of parameters."""

    if npars == 0:
        return "no parameters"
    if npars == 1:
        return "1 parameter"

    return f"{npars} parameters"


def wrapmodel_basic(model: ModelDefinition,
                    npars: int,
                    call: str,
                    text: str,
                    inplace: bool = False,
                    convolution: bool = False
                    ) -> str:
    """Create the m.def line for a single model"""

    assert not(inplace and convolution)

    out = f'    m.def("{model.name}", {call}'

    if model.language == 'Fortran - single precision':
        out += f'_f<{model.funcname}_'
    elif model.language == 'Fortran - double precision':
        out += F'_F<{model.funcname}_'
    elif model.language == 'C++ style':
        out += f'_C<C_{model.funcname}'
    elif model.language == 'C style':
        out += f'_C<{model.funcname}'  # should this be 'c_{model.funcname}' (not for compmag...)?
    else:
        raise ValueError("Unsuported language: {model.name} {model.funcname} {model.language}")

    out += f', {npars}>, "{text}",'
    out += '"pars"_a,"energies"_a,'
    if convolution:
        out += '"model"_a,'

    if inplace:
        out += '"out"_a,'

    out += '"spectrum"_a=1'
    if not model.language.startswith('Fortran'):
        out += ',"initStr"_a=""'

    if inplace or convolution:
        out += ',py::return_value_policy::reference'

    out += ');'
    return out


def wrapmodel_cxx(model: ModelDefinition,
                  npars: int,
                  text: str) -> str:
    """Make the C++ version available as name_"""

    if model.language != 'C++ style':
        return ''

    out = f'    m.def("{model.name}_", xspec_models_cxc::wrapper_inplace_CXX<'
    out += f'{model.funcname}, {npars}>, "{text}",'
    out += '"pars"_a,"energies"_a,"out"_a,"spectrum"_a=1,'
    out += '"initStr"_a=""'
    out += ',py::return_value_policy::reference'
    out += ');'
    return out


def wrapmodel_add(model: ModelDefinition,
                  npars: int) -> str:
    """What is the m.def line for this additive model?"""

    npars_str = get_npars(npars)
    out = wrapmodel_basic(model, npars, 'xspec_models_cxc::wrapper',
                          f'The XSPEC additive {model.name} model ({npars_str}).')
    out += '\n'
    out += wrapmodel_basic(model, npars, 'xspec_models_cxc::wrapper_inplace',
                           f'The XSPEC additive {model.name} model ({npars_str}); inplace.',
                           inplace=True)
    out += '\n'
    out += wrapmodel_cxx(model, npars,
                         f"The XSPEC additive {model.name} model ({npars_str}); RealArray, inplace.")
    return out


def wrapmodel_mul(model: ModelDefinition,
                  npars: int) -> str:
    """What is the m.def line for this multiplicative model?"""

    npars_str = get_npars(npars)
    out = wrapmodel_basic(model, npars, 'xspec_models_cxc::wrapper',
                          f'The XSPEC multiplicative {model.name} model ({npars_str}).')
    out += '\n'
    out += wrapmodel_basic(model, npars, 'xspec_models_cxc::wrapper_inplace',
                           f'The XSPEC multiplicative {model.name} model ({npars_str}); inplace.',
                           inplace=True)
    out += '\n'
    out += wrapmodel_cxx(model, npars,
                         f"The XSPEC multiplicative {model.name} model ({npars_str}); RealArray, inplace.")
    return out


def wrapmodel_con(model: ModelDefinition,
                  npars: int) -> str:
    """What is the m.def line for this convolution model?"""

    npars_str = get_npars(npars)
    return wrapmodel_basic(model, npars, 'xspec_models_cxc::wrapper_con',
                           f'The XSPEC convolution {model.name} model ({npars_str}); inplace.',
                           convolution=True)


def wrapmodel_compiled(model: ModelDefinition
                       ) -> tuple[str, str, str]:
    """The C++ code needed to intrface with this model.

    Parameters
    ----------
    model
       The model to use.

    Returns
    -------
    compiled_code, modeltype, description
       The code needed to be included in the C++ module, the model
       type ("Add", "Mul", or "Con"), and a description.

    """

    npars = len(model.pars)
    if model.modeltype == 'Add':
        mdef = wrapmodel_add(model, npars)

    elif model.modeltype == 'Mul':
        mdef = wrapmodel_mul(model, npars)

    elif model.modeltype == 'Con':
        mdef = wrapmodel_con(model, npars)

    else:
        raise ValueError(f"Unknown model: {model.name} {model.modeltype}")

    npars_str = get_npars(npars)
    desc = f"{model.name} - {npars_str}"
    return mdef, model.modeltype, desc


def to_model(mtype: str) -> str:
    """What is the model type enumeration."""
    return {'Add': 'ModelType.Add',
            'Mul': 'ModelType.Mul',
            'Con': 'ModelType.Con' }[mtype]


def to_lang(langtype: str) -> str:
    """What is the language enumeration"""
    return {'C++ style': 'LanguageStyle.CppStyle8',
            'C style': 'LanguageStyle.CStyle8',
            'Fortran - single precision': 'LanguageStyle.F77Style4',
            'Fortran - double precision': 'LanguageStyle.F77Style8'}[langtype]


def to_ptype(ptype):
    """What is the parameter type enumeration"""
    # We don't support periodic yet
    return {'Basic': 'ParamType.Default',
            'Switch': 'ParamType.Switch',
            'Scale': 'ParamType.Scale',
            '?': 'ParamType.Periodic'}[ptype]


def wrapmodel_python(model: ModelDefinition) -> tuple[str, str]:
    """What is the Python code needed to use this model.

    Parameters
    ----------
    model
       The model to use.

    Returns
    -------
    name, python_code
       The name of the model and the python code needed to create
       an instance of the model.

    """

    mtype = to_model(model.modeltype)
    lang = to_lang(model.language)
    out = [f"XSPECModel(modeltype={mtype}",
           f"name='{model.name}'",
           f"funcname='{model.funcname}'",
           f"language={lang}",
           f"elo={model.elo}",
           f"ehi={model.ehi}"]

    pars = []
    for p in model.pars:
        ps = [f"XSPECParameter(paramtype={to_ptype(p.paramtype)}"]
        ps.append(f"name='{p.name}'")
        ps.append(f"default={p.default}")
        if p.units is not None:
            ps.append(f"units='{p.units}'")

        try:
            if p.frozen:
                ps.append("frozen=True")
        except AttributeError:
            # Assume that if there's no frozen attribute it is
            # always frozen
            ps.append("frozen=True")

        for t in ['soft', 'hard']:
            for r in ['min', 'max']:
                attr = getattr(p, f'{t}{r}')
                if attr is not None:
                    ps.append(f"{t}{r}={attr}")

        if p.delta is not None:
            ps.append(f"delta={p.delta}")

        pars.append(', '.join(ps) + ')')

    pars = ', '.join(pars)
    out.append(f"parameters=[{pars}]")

    if len(model.flags) > 0 and model.flags[0] > 0:
        out.append("use_errors=True")

    if len(model.flags) > 1 and model.flags[1] > 0:
        out.append("can_cache=False")

    return model.name, ', '.join(out) + ')'
