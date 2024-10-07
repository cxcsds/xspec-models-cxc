"""Generate the code to be built based on the model.dat file.

Note that any error in creating the template will raise a
SystemExit exception.

At what point does it become worth using a templating system like
Jinja2?

"""

# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path
import sys

from parse_xspec.models import ModelDefinition, \
    parse_xspec_model_description


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


def apply_python(modelfile, models, template, xspec_version, outfile):
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

    # Filter to the ones we care about.
    #
    models1 = []
    unsupported = []
    for m in allmodels:
        if m.modeltype in ['Add', 'Mul', 'Con']:
            models1.append(m)
        else:
            unsupported.append(m)

    # A sanity check (at present this should be all supported
    # "language styles").
    #
    allowed_langs = ["Fortran - single precision",
                     "Fortran - double precision",
                     "C style",
                     "C++ style"]
    models = []
    for m in models1:
        if m.language in allowed_langs:
            models.append(m)
        else:
            unsupported.append(m)

    if len(models) == 0:
        sys.stderr.write(f'ERROR: unable to find any models in: {modelfile}\n')
        sys.exit(1)

    return models, unsupported


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
