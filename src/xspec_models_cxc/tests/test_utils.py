# Copyright (C) 2024
# Smithsonian Astrophysical Observatory
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Basic tests of the utility code.
#

from io import StringIO
from pathlib import Path

import numpy as np

import pytest

from parse_xspec import models

import xspec_models_cxc as x
import xspec_models_cxc.utils as xu


def test_get_modeldat_path():
    """Check what the field contains"""

    assert isinstance(x._model_dat, str)
    assert x._model_dat.endswith("/model.dat")


def test_get_include_path():
    """Just check we get something"""

    path = xu.get_include_path()
    assert isinstance(path, Path)
    assert path.stem == "xspec_models_cxc"
    assert path.suffix == ".hh"


def test_check_can_find_models():
    """Just check we can access some models.

    This is not particularly informative, and is just a basic check.

    """

    allmodels = models.parse_xspec_model_description(x._model_dat)
    supported, unsupported = xu.select_models(allmodels)
    # We don't know how many, but we do support some files.
    assert len(supported) > 0


def test_wrapmodel_additive():
    """"Check an additive model"""

    # Similar to agauss in XSPEC, but not quite
    mdesc = StringIO('''agauss         2   0.         1.e20          C_agauss  add  0
LineE   A      10.0   0.      0.      1.e6      1.e6      0.01
Sigma   A      1.0    0.      0.      1.e6      1.e6      -0.01

''')
    allmodels = models.parse_xspec_model_description(mdesc)
    supported, unsupported = xu.select_models(allmodels)
    assert len(supported) == 1
    assert len(unsupported) == 0

    cterms = xu.wrapmodel_compiled(supported[0])
    assert cterms[1] == "Add"
    assert cterms[2] == "agauss - 2 parameters"
    mdefs = cterms[0].split("\n")
    assert len(mdefs) == 3

    assert mdefs[0] == '    m.def("agauss", xspec_models_cxc::wrapper_C<C_agauss, 2>, "The XSPEC additive agauss model (2 parameters).","pars"_a,"energies"_a,"spectrum"_a=1,"initStr"_a="");'
    assert mdefs[1] == '    m.def("agauss", xspec_models_cxc::wrapper_inplace_C<C_agauss, 2>, "The XSPEC additive agauss model (2 parameters); inplace.","pars"_a,"energies"_a,"out"_a,"spectrum"_a=1,"initStr"_a="",py::return_value_policy::reference);'
    assert mdefs[2] == '    m.def("agauss_", xspec_models_cxc::wrapper_inplace_CXX<agauss, 2>, "The XSPEC additive agauss model (2 parameters); RealArray, inplace.","pars"_a,"energies"_a,"out"_a,"spectrum"_a=1,"initStr"_a="",py::return_value_policy::reference);'

    pterms = xu.wrapmodel_python(supported[0])
    assert pterms[0] == "agauss"
    assert pterms[1] == "XSPECModel(modeltype=ModelType.Add, name='agauss', funcname='agauss', language=LanguageStyle.CppStyle8, elo=0.0, ehi=1e+20, parameters=[XSPECParameter(paramtype=ParamType.Default, name='LineE', default=10.0, units='A', softmin=0.0, softmax=1000000.0, hardmin=0.0, hardmax=1000000.0, delta=0.01), XSPECParameter(paramtype=ParamType.Default, name='Sigma', default=1.0, units='A', frozen=True, softmin=0.0, softmax=1000000.0, hardmin=0.0, hardmax=1000000.0, delta=0.01)])"


def test_wrapmodel_multiplicative():
    """"Check a multiplicative model"""

    # Taken from XSPEC 12.14.1
    mdesc = StringIO('''cabs           1  0.         1.e20           xscabs    mul  0
nH      10^22   1.    0.0     0.0     1.e5      1.e6      1.e-3

''')
    allmodels = models.parse_xspec_model_description(mdesc)
    supported, unsupported = xu.select_models(allmodels)
    assert len(supported) == 1
    assert len(unsupported) == 0

    cterms = xu.wrapmodel_compiled(supported[0])
    assert cterms[1] == "Mul"
    assert cterms[2] == "cabs - 1 parameter"
    mdefs = cterms[0].split("\n")
    assert len(mdefs) == 3

    assert mdefs[0] == '    m.def("cabs", xspec_models_cxc::wrapper_f<xscabs_, 1>, "The XSPEC multiplicative cabs model (1 parameter).","pars"_a,"energies"_a,"spectrum"_a=1);'
    assert mdefs[1] == '    m.def("cabs", xspec_models_cxc::wrapper_inplace_f<xscabs_, 1>, "The XSPEC multiplicative cabs model (1 parameter); inplace.","pars"_a,"energies"_a,"out"_a,"spectrum"_a=1,py::return_value_policy::reference);'
    assert mdefs[2] == ''

    pterms = xu.wrapmodel_python(supported[0])
    assert pterms[0] == "cabs"
    assert pterms[1] == "XSPECModel(modeltype=ModelType.Mul, name='cabs', funcname='xscabs', language=LanguageStyle.F77Style4, elo=0.0, ehi=1e+20, parameters=[XSPECParameter(paramtype=ParamType.Default, name='nH', default=1.0, units='10^22', softmin=0.0, softmax=100000.0, hardmin=0.0, hardmax=1000000.0, delta=0.001)])"


def test_wrapmodel_convolution():
    """"Check a convolution model"""

    # Taken from XSPEC 12.14.1
    mdesc = StringIO('''gsmooth        2  0.         1.e20           C_gsmooth    con  0
Sig_6keV keV    1.00  0.0     0.0       10.     20.        .05
Index    " "    0.00  -1.     -1.       1.      1.        -0.01

''')
    allmodels = models.parse_xspec_model_description(mdesc)
    supported, unsupported = xu.select_models(allmodels)
    assert len(supported) == 1
    assert len(unsupported) == 0

    cterms = xu.wrapmodel_compiled(supported[0])
    assert cterms[1] == "Con"
    assert cterms[2] == "gsmooth - 2 parameters"
    mdefs = cterms[0].split("\n")
    assert len(mdefs) == 1

    assert mdefs[0] == '    m.def("gsmooth", xspec_models_cxc::wrapper_con_C<C_gsmooth, 2>, "The XSPEC convolution gsmooth model (2 parameters); inplace.","pars"_a,"energies"_a,"model"_a,"spectrum"_a=1,"initStr"_a="",py::return_value_policy::reference);'

    pterms = xu.wrapmodel_python(supported[0])
    assert pterms[0] == "gsmooth"
    assert pterms[1] == "XSPECModel(modeltype=ModelType.Con, name='gsmooth', funcname='gsmooth', language=LanguageStyle.CppStyle8, elo=0.0, ehi=1e+20, parameters=[XSPECParameter(paramtype=ParamType.Default, name='Sig_6keV', default=1.0, units='keV', softmin=0.0, softmax=10.0, hardmin=0.0, hardmax=20.0, delta=0.05), XSPECParameter(paramtype=ParamType.Default, name='Index', default=0.0, frozen=True, softmin=-1.0, softmax=1.0, hardmin=-1.0, hardmax=1.0, delta=0.01)])"
