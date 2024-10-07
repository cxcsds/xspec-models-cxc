#!/usr/bin/env python

# SPDX-License-Identifier: GPL-3.0-or-later

"""Return the library names needed to compile against XSPEC.

"""

import glob
from pathlib import Path
import os
import sys
import sysconfig


def doit(libdir: str) -> None:
    """Given the library directory, find the libraries"""

    xspec_libdir = Path(libdir)

    # There's some attempt to be platform independent, but
    # is it worth it?
    #
    if sysconfig.get_config_var("WITH_DYLD"):
        suffix = ".dylib"
    else:
        # Should this just be hard-coded?
        suffix = sysconfig.get_config_var('SHLIB_SUFFIX')

    # The tricky thing is that we have XSFunctions, XSUtil, and XS as
    # arguments. So we can not just look for XS*, as that will match
    # multiple libraries. We also don't want to include all matches to XS
    # as there are a number of matches we do not need.
    #
    def match(name: str) -> str:
        # Would it make sense to take the lib prefix from sysconfig?
        head = f"lib{name}{suffix}"
        ms = glob.glob(str(xspec_libdir / head))
        if len(ms) == 1:
            return name

        head = f"lib{name}_*{suffix}"
        ms = glob.glob(str(xspec_libdir / head))
        if len(ms) == 1:
            return Path(ms[0]).stem[3:]

        head = f"lib{name}-*{suffix}"
        ms = glob.glob(str(xspec_libdir / head))
        if len(ms) == 1:
            return Path(ms[0]).stem[3:]

        raise OSError(f"Unable to find a match for lib{name}*{suffix} in {xspec_libdir}")

    for libname in ["XSFunctions", "XSUtil", "XS", "hdsp",
                    "cfitsio", "CCfits", "wcs"]:
        # Note: not all names are versioned
        print(match(libname))


if __name__ == "__main__":

    if len(sys.argv) != 2:
        sys.stderr.write(f"Usage: {sys.argv[0]} libdir\n")
        sys.exit(1)

    doit(sys.argv[1])
