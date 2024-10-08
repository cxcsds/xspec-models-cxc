#  Copyright (C) 2024
#  Smithsonian Astrophysical Observatory
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Utility routines for interfacing with XSPEC models.

This module is used, along with the `parse-xspec module
<https://pypi.org/project/parse-xspec/>`_, to create the code needed
to support calling XSPEC user models from Python.

"""

from importlib import resources
from pathlib import Path
from typing import Sequence

from parse_xspec.models import ModelDefinition


__all__ = ("get_include_path", "select_models",
           "wrapmodel_compiled", "wrapmodel_python",
           )


def get_include_path() -> Path:
    """Return the location of the C++ include file."""

    path = resources.files("xspec_models_cxc.include")
    return path / "xspec_models_cxc.hh"
