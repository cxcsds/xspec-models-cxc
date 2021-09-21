#  Copyright (C) 2007, 2015-2018, 2019, 2020, 2021
#  Smithsonian Astrophysical Observatory
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Experiment with XSPEC models.

"""

from dataclasses import dataclass
from enum import Enum, auto

from ._compiled import *

__version__ = _compiled.__version__


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


@dataclass
class XSPECModel:
    """An XSPEC model."""

    modeltype: ModelType
    name: str
    funcname: str
    language: LanguageStyle
    elo: float
    ehi: float
    use_errors: bool = False
    can_cache: bool = True


_info = {
@@PYINFO@@
    }


def info(model):
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

def list_models(modeltype=None, language=None):
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

    """

    out = set()
    for k, v in _info.items():
        if modeltype is None and language is None:
            out.add(k)
            continue

        if modeltype is not None and v.modeltype == modeltype:
            out.add(k)

        if language is not None and v.language == language:
            out.add(k)

    return sorted(out)
