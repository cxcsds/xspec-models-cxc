#!/usr/bin/env python

# SPDX-License-Identifier: GPL-3.0-or-later

"""Return the library names needed to compile against XSPEC.

"""

from pathlib import Path
import sys

import xspec_models_cxc_helpers as xu

def doit(libdir: str) -> None:
    """Given the library directory, find the libraries"""

    xspec_libdir = Path(libdir)
    out = xu.get_xspec_libs(xspec_libdir)
    for name in out:
        print(name)

if __name__ == "__main__":

    if len(sys.argv) != 2:
        sys.stderr.write(f"Usage: {sys.argv[0]} libdir\n")
        sys.exit(1)

    doit(sys.argv[1])
