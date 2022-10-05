#  Copyright (C) 2007, 2015-2018, 2019, 2020, 2021
#  Smithsonian Astrophysical Observatory
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Experiment with XSPEC models.

The XSPEC model library is automatically initialized when the first
call is made, and not when the module is loaded.

There are three types of symbols in this package:

1. model functions, such as `apec` and `TBabs`, and `tableModel` for
   table models.
2. routines that set or get values such as the abundance
   table (`abundance`), cross-section table (`cross_sections`),
   cosmology (`cosmology`), and the chatter level (`chatter`).
3. routines about the models: `info` and `list_models`.

Examples
--------

What version of XSPEC is being used?

>>> import xspec_models_cxc as x
>>> x.get_version()
'@@XSPECVER@@'

What models are supported (the actual list depends on the
version of XSPEC the code was compiled against)?

>>> import xspec_models_cxc as x
>>> x.list_models()
['SSS_ice', 'TBabs', 'TBfeo', ..., 'zwndabs', 'zxipab', 'zxipcf']

Evaluate the multiplication of phabs and apec models, with their
default parameter ranges, on the grid from 0.1 to 10 keV with a bin
size of 1 eV. Note that the return value has one less element than the
grid, because it is evaluated over the range egrid[0]-egrid[1],
egrid[1]-egrid[2], ..., egrid[-2]-egrid[-1] - which for this case is
0.100-0.101, 0.101-0.102, ..., 9.998-9.999 keV.

>>> import numpy as np
>>> from matplotlib import pyplot as plt
>>> import xspec_models_cxc as x
>>> egrid = np.arange(0.1, 10, 0.001)
>>> apec = x.info('apec')
>>> phabs = x.info('phabs')
>>> pars_apec = [p.default for p in apec.parameters]
>>> pars_phabs = [p.default for p in phabs.parameters]
>>> yapec = x.apec(energies=egrid, pars=pars_apec)
>>> yphabs = x.phabs(energies=egrid, pars=pars_phabs)
>>> ymodel = yphabs * yapec
>>> emid = (egrid[:-1] + egrid[1:]) / 2
>>> plt.plot(emid, ymodel, label='phabs * apec')
>>> plt.yscale('log')
>>> plt.ylim(1e-9, 0.01)
>>> plt.legend()
>>> plt.xlabel('Energy (keV)')
>>> plt.ylabel('Photon/cm$^2$/s')

We can include a convolution component - in this case the kdblur model
- even if it is physically unrealistic. The two differences here is
that the model requires the data to be convolved to be sent in as the
`model` argument, and that this array is changed by the routine (in
the same way that the out parameter works for NumPy ufunc
routines). The convolution models also return the value so we could
have said

    out = x.kdblur(ebergies=.., pars=.., model=ymodel.copy())

which would keep the original model values (there is actualy a subtly
in that the `model` argument must be sent the correct datatype for the
convolution model - so either `np.float64` or `np.float32` - otherwise
it will not be changed).

>>> kdblur = x.info('kdblur')
>>> pars_kdblur = [p.default for p in kdblur.parameters]
>>> x.kdblur(energies=egrid, pars=pars_kdblur, model=ymodel)
>>> plt.plot(emid, ymodel, alpha=0.8, label='Convolved')
>>> plt.legend()

XSPEC table models [TableModel]_ are fun to work with, as you

1. need to read in the file to find out information on the model -
   such as whether it's atable or mtable (but unfortunately there is
   no header keyword to determine if it is an etable) - and the
   parameter names, values, and ranges.

2. use the file name when evaluating the model along with some of
   this metadata.

At the moment this module only supports the second part - calling the
models - and it is left to the user to find the other information out.

In this example the ``RCS.mod`` table model, which has three
parameters, does not add a redshift parameter, and is an "atable"
model (i.e. additive):

    % dmlist "RCS.mod[cols name, initial]" data,clean
    #  NAME           INITIAL
     tau                             1.0
     beta               0.10000000149012
     T                  0.10000000149012
    % dmkeypar xspec-tablemodel-RCS.mod"[primary]" redshift echo+
    0
    % dmkeypar "xspec-tablemodel-RCS.mod[primary]" addmodel echo+
    1

This can then be used with `tableModel` in a similar manner to the
other models, apart from requiring `table` and `table_type` arguments:

>>> infile = 'RCS.mod'
>>> pars = [1, 0.1, 0.1]
>>> egrid = np.arange(0.1, 10, 0.01)
>>> y = x.tableModel(table=infile, table_type="add", energies=egrid, pars=pars)

Note that it is very easy to make the table model code crash the
system, such as by sending in not enough parameters or setting a
parameter outside its hard limits:

>>> x.tableModel(infile, "add", pars=[1, 2], energies=egrid)
Segmentation fault (core dumped)

References
----------

.. [TableModel] https://heasarc.gsfc.nasa.gov/docs/heasarc/ofwg/docs/general/ogip_92_009/ogip_92_009.html

"""

from dataclasses import dataclass
from enum import Enum, auto
import logging
from typing import List, Optional, Sequence

try:
    from ._compiled import *
    __version__ = _compiled.__version__
except ImportError as ie:
    # Allow the actual error message to be reported if the user
    # has tweaked the log level, for instance with:
    #
    #   import logging; logging.basicConfig(level=logging.DEBUG)
    #
    logging.getLogger(__name__).warn("Unable to import compiled XSPEC models")
    logging.getLogger(__name__).info(str(ie))

    __version__ = "none"


class ModelType(Enum):
    """The various XSPEC model types."""

    Add = auto()
    Mul = auto()
    Con = auto()


class LanguageStyle(Enum):
    """The various ways to define and call XSPEC models."""

    CppStyle8 = auto()
    CStyle8 = auto()
    F77Style4 = auto()
    F77Style8 = auto()


class ParamType(Enum):
    """The XSPEC parameter type."""

    Default = auto()
    Switch = auto()
    Scale = auto()
    Periodic = auto()


@dataclass
class XSPECParameter:
    """An XSPEC parameter."""

    paramtype: ParamType
    name: str
    default: float
    units: Optional[str] = None
    frozen: bool = False
    # Would it be better to just have limits = [hardmin, softmni, softmax, hardmax]?
    softmin: Optional[float] = None
    softmax: Optional[float] = None
    hardmin: Optional[float] = None
    hardmax: Optional[float] = None
    delta: Optional[float] = None


@dataclass
class XSPECModel:
    """An XSPEC model."""

    modeltype: ModelType
    name: str
    funcname: str
    language: LanguageStyle
    elo: float
    ehi: float
    parameters: Sequence[XSPECParameter]
    use_errors: bool = False
    can_cache: bool = True


_info = {
@@PYINFO@@
    }


def info(model: str) -> XSPECModel:
    """Return information on the XSPEC model from the model.dat file.

    This returns the information on the model as taken from the XSPEC
    model library used to build this model.

    Parameters
    ----------
    name : str
        The XSPEC model name (case insensitive).

    Returns
    -------
    model : XSPECModel
        The dataclass that describes the mode;.

    See Also
    --------
    list_models

    Examples
    --------

    >>> m = info('apec')
    >>> m.name
    'apec'
    >>> m.modeltype
    <ModelType.Add: 1>
    >>> [(p.name, p.default, p.units) for p in m.parameters]
    [('kT', 1.0, 'keV'), ('Abundanc', 1.0, None), ('Redshift', 0.0, None)]

    """

    # We want case-insensitive comparison but for the keys to retain
    # their case. Using casefold() rather than lower() is a bit OTT
    # here as I would bet model.dat is meant to be US-ASCII.
    #
    check = model.casefold()
    out = next((v for k, v in _info.items() if k.casefold() == check),
               None)
    if out is None:
        raise ValueError(f"Unrecognized XSPEC model '{model}'")

    return out


# Do we need Optional here?
def list_models(modeltype: Optional[ModelType] = None,
                language: Optional[LanguageStyle] = None) -> List[str]:
    """Returns the names of XSPEC models from the model.dat file.

    This returns the information on the model as taken from the XSPEC
    model library used to build this model.

    Parameters
    ----------
    modeltype : ModelType or None, optional
        If not None then restrict the list to this model type.
    language : LanguageStyle or None, optional
        If not None then restrict the list to this language type.

    Returns
    -------
    models : list of str
        A sorted list of the model names.

    See Also
    --------
    info

    Notes
    -----
    The restrictions are combined, so setting both `modeltype` and
    `language` will select only those models which match both filters.

    Examples
    --------

    >>> len(list_models())
    231

    >>> 'tbabs' in list_models()
    False
    >>> 'TBabs' in list_models()
    True

    With XSPEC 12.12.0 / HEASOFT 6.29:

    >>> list_models(modeltype=ModelType.Con)
    ['cflux', 'clumin', 'cpflux', 'gsmooth', ..., 'zashift', 'zmshift']

    >>> list_models(modeltype=ModelType.Con, language=LanguageStyle.F77Style4)
    ['kyconv', 'rgsxsrc', 'thcomp']

    """

    out = set()
    for k, v in _info.items():

        if modeltype is not None and v.modeltype != modeltype:
            continue

        if language is not None and v.language != language:
            continue

        out.add(k)

    return sorted(out)
