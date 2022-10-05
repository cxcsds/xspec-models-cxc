"""Generate the code to be built based on the model.dat file.

Note that any error in creating the template will raise a
SystemExit exception.

"""

# SPDX-License-Identifier: GPL-3.0-or-later

import pathlib
import sys

from parse_xspec.models import parse_xspec_model_description


__all__ = ("apply", )


def replace_term(txt, term, replace):
    """Replace the first term with replace in txt"""

    idx = txt.find(term)
    if idx < 0:
        sys.stderr.write(f'ERROR: unable to find {term}\n')
        sys.exit(1)

    return txt[:idx] + replace + txt[idx + len(term):]


def apply_compiled(models, template, outfile):
    """Convert the template for the compiled code."""

    # Ugly information flow here
    addmodels = []
    mulmodels = []
    conmodels = []
    f77models = []
    f77models_dp = []
    cxxmodels = []
    cmodels = []

    def get_npars(npars):
        if npars == 0:
            return "no parameters"
        if npars == 1:
            return "1 parameter"

        return f"{npars} parameters"

    def wrapmodel_basic(model, npars, call, text,
                        inplace=False,
                        convolution=False):
        """Create the m.def line for a single model"""

        assert not(inplace and convolution)

        out = f'    m.def("{model.name}", {call}'

        if model.language == 'Fortran - single precision':
            out += f'_f<{model.funcname}_'
            f77models.append(model.funcname)
        elif model.language == 'Fortran - double precision':
            out += F'_F<{model.funcname}_'
            f77models_dp.append(model.funcname)
        elif model.language == 'C++ style':
            out += f'_C<C_{model.funcname}'
            cxxmodels.append(model.funcname)
        elif model.language == 'C style':
            out += f'_C<{model.funcname}'  # should this be 'c_{model.funcname}' (not for compmag...)?
            cmodels.append(model.funcname)
        else:
            assert False, (model.name, model.funcname, model.language)

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

    def wrapmodel_cxx(model, npars, text):
        """Make the C++ version available as name_"""

        if model.language != 'C++ style':
            return ''

        out = '\n'
        out += f'    m.def("{model.name}_", xspec_models_cxc::wrapper_inplace_CXX<'
        out += f'{model.funcname}, {npars}>, "{text}",'
        out += '"pars"_a,"energies"_a,"out"_a,"spectrum"_a=1,'
        out += '"initStr"_a=""'
        out += ',py::return_value_policy::reference'
        out += ');'
        return out

    def wrapmodel_add(model, npars):
        """What is the m.def line for this additive model?"""

        addmodels.append((model.name, npars))

        out = wrapmodel_basic(model, npars, 'xspec_models_cxc::wrapper',
                              f'The XSPEC additive {model.name} model ({get_npars(npars)}).')
        out += '\n'
        out += wrapmodel_basic(model, npars, 'xspec_models_cxc::wrapper_inplace',
                               f'The XSPEC additive {model.name} model ({get_npars(npars)}); inplace.',
                               inplace=True)

        out += wrapmodel_cxx(model, npars,
                             f"The XSPEC additive {model.name} model ({get_npars(npars)}); RealArray, inplace.")

        return out

    def wrapmodel_mul(model, npars):
        """What is the m.def line for this multiplicative model?"""

        mulmodels.append((model.name, npars))

        out = wrapmodel_basic(model, npars, 'xspec_models_cxc::wrapper',
                              f'The XSPEC multiplicative {model.name} model ({get_npars(npars)}).')
        out += '\n'
        out += wrapmodel_basic(model, npars, 'xspec_models_cxc::wrapper_inplace',
                               f'The XSPEC multiplicative {model.name} model ({get_npars(npars)}); inplace.',
                               inplace=True)

        out += wrapmodel_cxx(model, npars,
                             f"The XSPEC multiplicative {model.name} model ({get_npars(npars)}); RealArray, inplace.")

        return out

    def wrapmodel_con(model, npars):
        """What is the m.def line for this convolution model?"""

        conmodels.append((model.name, npars))

        out = wrapmodel_basic(model, npars, 'xspec_models_cxc::wrapper_con',
                              f'The XSPEC convolution {model.name} model ({get_npars(npars)}); inplace.',
                              convolution=True)

        return out

    def wrapmodel(model):
        """What is the m.def line for this model?"""

        npars = len(model.pars)
        if model.modeltype == 'Add':
            return wrapmodel_add(model, npars)

        if model.modeltype == 'Mul':
            return wrapmodel_mul(model, npars)

        if model.modeltype == 'Con':
            return wrapmodel_con(model, npars)

        assert False, model.modeltype

    mstrs = [wrapmodel(m) for m in models]

    def hdr(arg):
        (model, npars) = arg  # apparently I can't write Haskell pattern-matching in Python
        return f"{model} - {get_npars(npars)}."

    with template.open(mode='rt') as ifh:
        out = ifh.read()

        repl = [hdr(m) for m in addmodels]
        out = replace_term(out, '@@ADDMODELS@@', '\n'.join(repl))

        repl = [hdr(m) for m in mulmodels]
        out = replace_term(out, '@@MULMODELS@@', '\n'.join(repl))

        repl = [hdr(m) for m in conmodels]
        out = replace_term(out, '@@CONMODELS@@', '\n'.join(repl))

        out = replace_term(out, '@@MODELS@@', '\n'.join(mstrs))

    with outfile.open(mode='wt') as ofh:
        ofh.write(out)

    return {'outfile': outfile,
            'models': [m.name for m in models],
            'additive': addmodels,
            'multiplicative': mulmodels,
            'convolution': conmodels,
            'C++': cxxmodels,
            'C': cmodels,
            'f77': f77models,
            'F77': f77models_dp,
        }


def apply_python(models, template, xspec_version, outfile):
    """Convert the template for the Python code.

    xspec_version : str
        The XSPEC library we are building against, including the patch
        level.

    """

    def to_model(mtype):
        return {'Add': 'ModelType.Add',
                'Mul': 'ModelType.Mul',
                'Con': 'ModelType.Con' }[mtype]

    def to_lang(langtype):
        return {'C++ style': 'LanguageStyle.CppStyle8',
                'C style': 'LanguageStyle.CStyle8',
                'Fortran - single precision': 'LanguageStyle.F77Style4',
                'Fortran - double precision': 'LanguageStyle.F77Style8'}[langtype]

    def to_ptype(ptype):
        # We don't support periodic yet
        return {'Basic': 'ParamType.Default',
                'Switch': 'ParamType.Switch',
                'Scale': 'ParamType.Scale',
                '?': 'ParamType.Periodic'}[ptype]

    mstrs = []
    for model in models:
        mtype = to_model(model.modeltype)
        lang = to_lang(model.language)
        out = [f"    '{model.name}': XSPECModel(modeltype={mtype}",
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

        mstrs.append(', '.join(out) + ')')

    with template.open(mode='rt') as ifh:
        out = ifh.read()

        out = replace_term(out, '@@PYINFO@@', ',\n'.join(mstrs))
        out = replace_term(out, '@@XSPECVER@@', xspec_version)

    with outfile.open(mode='wt') as ofh:
        ofh.write(out)


# At what point does it become worth using a templating system like
# Jinja2?
#
def apply(modelfile, xspec_version, out_dir):
    """Parse the model.dat file and create the code.

    Parameters
    ----------
    modelfile : pathlib.Path
        The he model.dat file.
    xspec_version : str
        The XSPEC library we are building against, including the patch
        level.
    out_dir : pathlib.Path
        The directory where to write the output.

    Returns
    -------
    models : dict
        Information on the different model types that were found and
        the files created.

    Notes
    -----
    The templates/xspec.cxx file is used as the template.

    """

    if not modelfile.is_file():
        sys.stderr.write(f'ERROR: unable to find model.dat file: {modelfile}.\n')
        sys.exit(1)

    allmodels = parse_xspec_model_description(modelfile)
    if len(allmodels) == 0:
        sys.stderr.write(f'ERROR: unable to parse model.fat file: {modelfile}\n')
        sys.exit(1)

    # Filter to the ones we care about
    models = [m for m in allmodels if m.modeltype in ['Add', 'Mul', 'Con']]

    # For now filter out FORTRAN double-precision models as I don't
    # know what to do with them (need to check against Sherpa).
    #
    allowed_langs = ["Fortran - single precision",
                     "Fortran - double precision",
                     "C style",
                     "C++ style"]
    models = [m for m in models if m.language in allowed_langs]

    if len(models) == 0:
        sys.stderr.write(f'ERROR: unable to find any models in: {modelfile}\n')
        sys.exit(1)

    if not out_dir.is_dir():
        sys.stderr.write(f'ERROR: unable to find output directory: {out_dir}\n')
        sys.exit(1)

    # Create the code we want to compile
    #
    template_dir = pathlib.Path('template')

    filename = pathlib.Path('xspec.cxx')
    template = template_dir / filename
    outfile = out_dir / filename
    out_dir.mkdir(exist_ok=True)
    info = apply_compiled(models, template, outfile)

    filename = pathlib.Path('__init__.py')
    template = template_dir / filename
    out_dir = out_dir / 'xspec_models_cxc'
    outfile = out_dir / filename
    out_dir.mkdir(exist_ok=True)
    apply_python(models, template, xspec_version, outfile)

    # It looks like info['models'] does not contain repeated values.
    #
    print("###############################################")
    print(f"Number of supported models:  {len(info['models'])}")

    # Summarize. We can't use the length of these as they may include
    # repeated models (e.g. because we provide different ways to
    # access the model). Hence the conversion to a set first (as the
    # names are the same).
    #
    def count(label, value=None):
        if value is None:
            value = label

        print(f"   {label:20s}  {len(set(info[value]))}")

    count("additive")
    count("multiplicative")
    count("convolution")
    count("C++")
    count("C")
    count("FORTRAN (sp)", "f77")
    count("FORTRAN (dp)", "F77")

    nskip = len(allmodels) - len(info['models'])
    if nskip > 0:
        print("")
        print(f"   Number skipped: {nskip}")

        assert len(info['models']) == len(models)

        allknown = set(m.name for m in allmodels)
        known = set(m.name for m in models)
        for i, unknown in enumerate(sorted(allknown.difference(known)), 1):
            print(f"      {i}. {unknown}")

        print("")

    print("###############################################")

    return info
