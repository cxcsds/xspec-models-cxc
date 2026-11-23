# Copyright (C) 2026
# Smithsonian Astrophysical Observatory
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Tests of evaluating a model for multiple parameter sets at once: the
# pars argument can be 2D, with one row per parameter set.
#

import numpy as np

import pytest

import xspec_models_cxc as x


# We need to set up the cosmology as this is currently not done in FNINIT.
#
x.cosmology(h0=70, lambda0=0.73, q0=0)

# We want to ensure we have a fixed abundance / cross section
# for the checks below. If we didn't set them here then it
# would depend on the user's ~/.xspec/Xspec.init file
#
x.abundance('lodd')
x.cross_section('vern')


# A model from each language style, along with parameter sets to use
# (these are the model-function parameters, so they do not include a
# normalization argument).
#
# The thermal models are avoided as they need extra data files to be
# installed to be evaluated.
#
MODELS = [("powerlaw", [[1.7], [0.5], [2.0]]),
          ("bkn2pow", [[1.0, 2.0, 0.1, 1.0, 2.0],
                       [1.0, 1.0, 0.5, 2.0, 3.0]]),
          ("gaussian", [[6.4, 0.1], [6.7, 0.5]]),
          ("apec", [[1.0, 1.0, 0.0], [2.0, 0.5, 0.1]]),
          ("wabs", [[0.1], [1.0], [5.0]]),
          ("TBabs", [[0.1], [1.0]]),
          ("zpowerlw", [[1.7, 0.1], [0.5, 0.5]])]


def get_dtype(model):
    """What is the dtype used by this model?"""

    return {x.LanguageStyle.CppStyle8: np.float64,
            x.LanguageStyle.CStyle8: np.float64,
            x.LanguageStyle.F77Style4: np.float32,
            x.LanguageStyle.F77Style8: np.float64}[x.info(model).language]


def get_egrid():
    return np.arange(0.1, 10, 0.01)


@pytest.mark.parametrize("model,pars", MODELS)
def test_eval_vectorized(model, pars):
    """A 2D pars array evaluates the model for each row"""

    mfunc = getattr(x, model)
    egrid = get_egrid()

    pars = np.asarray(pars)
    y1 = [mfunc(energies=egrid, pars=p) for p in pars]

    y2 = mfunc(energies=egrid, pars=pars)

    assert y2.shape == (len(pars), egrid.size - 1)

    for i, expected in enumerate(y1):
        assert y2[i] == pytest.approx(expected)


@pytest.mark.parametrize("model,pars", MODELS)
def test_eval_vectorized_inplace(model, pars):
    """A 2D pars array and matching 2D out array"""

    mfunc = getattr(x, model)
    egrid = get_egrid()

    pars = np.asarray(pars)
    dtype = get_dtype(model)

    out = np.zeros((len(pars), egrid.size - 1), dtype=dtype)
    y = mfunc(energies=egrid, pars=pars, out=out)

    assert y is out

    expected = [mfunc(energies=egrid, pars=p) for p in pars]
    for i, exp in enumerate(expected):
        assert out[i] == pytest.approx(exp, rel=1e-5)


@pytest.mark.parametrize("model,pars", MODELS)
def test_eval_vectorized_lists(model, pars):
    """The vectorized interface accepts non-numpy input"""

    mfunc = getattr(x, model)
    egrid = get_egrid()

    # a list of lists is converted to a 2D array
    #
    y = mfunc(energies=list(egrid), pars=pars)

    pars = np.asarray(pars)
    expected = mfunc(energies=egrid, pars=pars)
    assert y == pytest.approx(expected)


@pytest.mark.parametrize("model,pars", MODELS)
def test_eval_vectorized_1d_unchanged(model, pars):
    """A 1D pars array still returns a 1D array"""

    mfunc = getattr(x, model)
    egrid = get_egrid()

    pars = np.asarray(pars)
    y1 = mfunc(energies=egrid, pars=pars[0])
    assert y1.shape == (egrid.size - 1, )

    y2 = mfunc(energies=egrid, pars=pars)
    assert y1 == pytest.approx(y2[0])


def test_eval_vectorized_inplace_shape_mismatch():
    """The out array must match the parameter array"""

    egrid = get_egrid()
    pars = np.asarray([[0.1], [1.0]])

    # 2D pars requires a 2D out
    out = np.zeros(egrid.size - 1, dtype=np.float32)
    with pytest.raises(ValueError):
        x.wabs(energies=egrid, pars=pars, out=out)

    # the first dimension must match the number of parameter sets
    out = np.zeros((3, egrid.size - 1), dtype=np.float32)
    with pytest.raises(ValueError):
        x.wabs(energies=egrid, pars=pars, out=out)


def test_eval_vectorized_inplace_dtype_mismatch():
    """The out array must have the dtype expected by the model"""

    egrid = get_egrid()

    # wabs is a FORTRAN single-precision model
    out = np.zeros(egrid.size - 1, dtype=np.float64)
    with pytest.raises(TypeError):
        x.wabs(energies=egrid, pars=[0.1], out=out)


def test_eval_vectorized_bad_pars():
    """The number of parameters is checked for each row"""

    egrid = get_egrid()

    # powerlaw has one parameter
    pars = np.asarray([[1.7, 2.0], [0.5, 2.0]])
    with pytest.raises(RuntimeError):
        x.powerlaw(energies=egrid, pars=pars)


def test_eval_vectorized_convolution():
    """A convolution model supports a 2D model argument"""

    egrid = get_egrid()

    base = x.powerlaw(energies=egrid, pars=[1.7])

    cpars = np.asarray([[10.0, 0.5, 10.0],
                        [10.0, 1.0, 10.0],
                        [1.0, 0.5, 8.0]])

    single = []
    for cp in cpars:
        vals = base.copy()
        x.cflux(energies=egrid, pars=cp, model=vals)
        single.append(vals)

    out = np.tile(base, (len(cpars), 1))
    y = x.cflux(energies=egrid, pars=cpars, model=out)

    assert y is out
    for i, exp in enumerate(single):
        assert out[i] == pytest.approx(exp)


def test_eval_vectorized_energies_2d():
    """The energies grid must remain 1D"""

    egrid = get_egrid()
    e2 = np.asarray([egrid, egrid])

    with pytest.raises((TypeError, ValueError)):
        x.powerlaw(energies=e2, pars=[1.7])
