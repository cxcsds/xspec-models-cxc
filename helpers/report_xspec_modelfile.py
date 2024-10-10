#!/usr/bin/env python

# SPDX-License-Identifier: GPL-3.0-or-later

"""Return the location of the XSPEC model.dat file.

"""

import xspec_models_cxc_helpers as xu

print(xu.get_xspec_model_path())
