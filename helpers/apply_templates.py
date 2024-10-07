#!/usr/bin/env python

# SPDX-License-Identifier: GPL-3.0-or-later

"""Process the templates to create the module files.

Usage:

  ./apply_templates.py modeldat xspecver outcompiled outpython

This uses the model.dat file to identify what models and parameters
are needed to create the python and C++ code. The xspecver argument
is the XSPEC version string (e.g. "12.14.1" or "12.14.1c").

"""

from pathlib import Path
import sys

# local import
import template


def doit(modeldat: str,
         xspecver: str,
         *,
         out_python: str,
         out_compiled: str
         ) -> None:

    modelfile = Path(modeldat)
    models, unsupported = template.find_models(modelfile)

    template_dir = Path('template')
    template_compiled = template_dir / 'xspec.cxx'
    template_python = template_dir / '__init__.py'
    for temp in [template_compiled, template_python]:
        if not temp.is_file():
            raise ValueError(f"Unable to find template: {temp}")

    # Check that the directories exist. This is ugly and potentially
    # dangerous.
    #
    outc = Path(out_compiled).resolve()
    outp = Path(out_python).resolve()
    for out in [outc, outp]:
        if out.exists():
            continue

        for parent in reversed(out.parents):
            if parent.is_dir():
                continue

            parent.mkdir()

    # Create the code we want to compile
    #
    template.apply_compiled(models, template_compiled, outc)
    template.apply_python(modelfile, models, template_python,
                          xspecver, outp)

    template.report(models, unsupported)


if __name__ == "__main__":

    if len(sys.argv) != 5:
        sys.stderr.write(f"Usage: {sys.argv[0]} modeldat xspecver outcompiled outpython\n")
        sys.exit(1)

    doit(sys.argv[1], sys.argv[2],
         out_compiled=sys.argv[3],
         out_python=sys.argv[4])
