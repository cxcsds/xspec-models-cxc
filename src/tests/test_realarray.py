"""Check out the RealArray support"""

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


@pytest.mark.parametrize("arg", [[], 0])
def test_create(arg):
    out = x.RealArray(arg)
    assert isinstance(out, x.RealArray)


@pytest.mark.parametrize("arg", [[], 0])
def test_create_is_empty(arg):
    out = x.RealArray(arg)
    assert len(out) == 0


@pytest.mark.parametrize("arg", [[], 0])
def test_create_str(arg):
    out = x.RealArray(arg)
    assert str(out) == '[]'


@pytest.mark.parametrize("n", [0, 1, 10])
def test_create_from_count(n):
    out = x.RealArray(n)
    assert len(out) == n
    for z in out:
        assert z == pytest.approx(0)


@pytest.mark.parametrize("invals",
                         [(1, 2, -3, 4),
                          [1, 2, -3, 4],
                          np.asarray([1, 2, -3, 4])])
def test_create_from_sequence(invals):
    out = x.RealArray(invals)
    assert len(out) == 4
    for (got, expected) in zip(out, invals):
        assert got == pytest.approx(expected)

    assert str(out) == '[1, 2, -3, 4]'


@pytest.mark.parametrize("idx,expected",
                         [(0, 0.1), (1, 0.2), (2, 0.3), (7, 0.8), (8, 0.9),
                          (-1, 0.9), (-2, 0.8), (-8, 0.2), (-9, 0.1)])
def test_get_index(idx, expected):

    out = x.RealArray(np.arange(0.1, 1, 0.1))

    assert out[idx] == pytest.approx(expected)


@pytest.mark.parametrize("idx", [10, -10])
def test_get_index_out_of_bounds(idx):

    out = x.RealArray(np.arange(0.1, 1, 0.1))
    with pytest.raises(IndexError):
        out[idx]


@pytest.mark.parametrize("idx", [0, 1, 2, 7, 8, -1, -2, -8, -9])
def test_set_index(idx):

    out = x.RealArray(np.arange(0.1, 1, 0.1))
    out[idx] = -999
    assert out[idx] == pytest.approx(-999)


@pytest.mark.parametrize("idx", [10, -10])
def test_set_index_out_of_bounds(idx):

    out = x.RealArray(np.arange(0.1, 1, 0.1))
    with pytest.raises(IndexError):
        out[idx] = -999


def test_create_copies():
    """We copy the data rather than accessing it"""

    invals = np.arange(0.1, 1, 0.1, dtype=np.float64)
    out = x.RealArray(invals)

    invals[2] += 1
    assert invals[2] == pytest.approx(1.3)

    assert out[2] == pytest.approx(0.3)


# Simple checks of using RealArray-ified arrays
#
def test_can_not_call_basic_interface():

    pars = [-1.7]
    egrid = [0.1, 0.2, 0.3, 0.4]

    output = [0, 0, 0]

    with pytest.raises(TypeError):
        x.powerlaw_(energies=egrid, pars=pars, out=output)

    with pytest.raises(TypeError):
        x.powerlaw_(energies=x.RealArray(egrid), pars=pars, out=x.RealArray(output))

    with pytest.raises(TypeError):
        x.powerlaw_(energies=egrid, pars=x.RealArray(pars), out=x.RealArray(output))

    with pytest.raises(TypeError):
        x.powerlaw_(energies=x.RealArray(egrid), pars=x.RealArray(pars), out=output)


# What models do we want to run to check they match the
# "basic" interface?
#
MODELS_ADD = [m for m in x.list_models(modeltype=x.ModelType.Add)
              if x.info(m).language == x.LanguageStyle.CppStyle8]
MODELS_MUL = [m for m in x.list_models(modeltype=x.ModelType.Mul)
              if x.info(m).language == x.LanguageStyle.CppStyle8]


@pytest.mark.parametrize("models", [MODELS_ADD, MODELS_MUL])
def test_have_models(models):
    """We have wrapped some models"""
    assert len(models) > 0


@pytest.mark.parametrize("model", MODELS_ADD + MODELS_MUL)
def test_evaluate(model):
    """We can evaluate the model

    We compare the model to the "basic" version.
    """

    mbasic = getattr(x, model)
    mreal = getattr(x, f'{model}_')

    info = x.info(model)
    bpars = [0.1 if p.name.casefold() == 'redshift' else p.default
             for p in info.parameters]
    rpars = x.RealArray(bpars)

    bgrid = np.arange(0.1, 11, 0.01)
    rgrid = x.RealArray(bgrid)

    out = x.RealArray(np.zeros(bgrid.size - 1))

    by = mbasic(energies=bgrid, pars=bpars)
    ry = mreal(energies=rgrid, pars=rpars, out=out)

    # We do not use pytest.approx here as they should be the same
    assert (ry == by).all()

    assert ry is out
