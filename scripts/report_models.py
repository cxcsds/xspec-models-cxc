#!/usr/bin/env python

"""

Usage:

  ./report_models.py <model.dat>

Aim:

List the supported and unsupported models for the given XSPEC
library. This repeats logic in helpers/template.py, so it really
should use some common code.

It also requires

    pip install parse-xspec

even though this is not needed to run `xspec_models_cxc`.

"""

import sys

from parse_xspec.models import parse_xspec_model_description

import xspec_models_cxc as x

# Try to access the model file
#
allmodels = parse_xspec_model_description(x._model_dat)
if len(allmodels) == 0:
    sys.stderr.write("Unable to parse model.dat file: {x._model_dat}")
    sys.exit(1)

print(f"XSPEC version: {x.get_version()}\n")
nmodels = len(x.list_models())
print(f"Number of models: {nmodels}\n")

print("| Type           | Total  | Supported |")
print("| -------------- | ------ | --------- |")

ntotal_all = 0
nsupported_all = 0

for (name, enum) in [("additive", x.ModelType.Add),
                     ("multiplicative", x.ModelType.Mul),
                     ("convolution", x.ModelType.Con),
                     ("acn", None)]:

    if enum is None:
        nsupported = 0
        ntotal = len([m for m in allmodels if m.modeltype == "Acn"])
    else:
        nsupported = len(x.list_models(modeltype=enum))
        ntotal = len([m for m in allmodels if m.modeltype == enum.name])

    ntotal_all += ntotal
    nsupported_all += nsupported
    print(f"| {name:14s} | {ntotal:6d} | {nsupported:9d} |")

print("| -------------- | ------ | --------- |")

ntotal_all2 = 0
nsupported_all2 = 0

for name, lname in [("C++", "C++ style"),
                    ("C", "C style"),
                    ("FORTRAN sp", "Fortran - single precision"),
                    ("FORTRAN dp", "Fortran - double precision")]:

    ntotal = len([m for m in allmodels if m.language == lname])

    # ugh
    if lname == "C++ style":
        language = x.LanguageStyle.CppStyle8
    elif lname == "C style":
        language = x.LanguageStyle.CStyle8
    elif lname == "Fortran - single precision":
        language = x.LanguageStyle.F77Style4
    elif lname == "Fortran - double precision":
        language = x.LanguageStyle.F77Style8
    else:
        assert False

    nsupported = len(x.list_models(language=language))

    ntotal_all2 += ntotal
    nsupported_all2 += nsupported
    print(f"| {name:14s} | {ntotal:6d} | {nsupported:9d} |")

print("| -------------- | ------ | --------- |\n")

print(f"Number skipped:   {ntotal_all - nsupported_all}\n")

if ntotal_all == ntotal_all2 and nsupported_all == nsupported_all2:
    sys.exit(0)

sys.stderr.write("Error summing models\n")
sys.stderr.write("  ntotal     = {ntotal_all} {ntotal_all2}\n")
sys.stderr.write("  nsupported = {nsupported_all} {nsupported_all2}\n")
sys.exit(1)
