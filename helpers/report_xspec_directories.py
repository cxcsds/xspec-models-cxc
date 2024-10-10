#!/usr/bin/env python

# SPDX-License-Identifier: GPL-3.0-or-later

"""Return the library and include directories.

Is this actually useful anymore?

"""

import xspec_models_cxc_helpers as xu

print(xu.get_xspec_include_path())
print(xu.get_xspec_library_path())
