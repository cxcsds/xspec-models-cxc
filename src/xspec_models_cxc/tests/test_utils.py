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
import xspec_models_cxc_helpers as xu


def test_get_modeldat_path():
    """Check what the field contains"""

    assert isinstance(x._model_dat, str)
    assert x._model_dat.endswith("/model.dat")


def test_compare_modeldat_paths():
    """At this point these should be the same"""

    path = xu.get_xspec_model_path()
    assert x._model_dat == str(path)


def test_get_include_path():
    """Just check we get something"""

    path = x.get_include_path()
    assert isinstance(path, Path)
    assert path.stem == "xspec_models_cxc"
    assert path.suffix == ".hh"
