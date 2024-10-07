#!/usr/bin/env python

# SPDX-License-Identifier: GPL-3.0-or-later

"""Return the location of the XSPEC model.dat file.

"""

from pathlib import Path
import os
import sys

HEADAS_ENV = os.getenv('HEADAS')
if HEADAS_ENV is None:
    sys.stderr.write('##################################################\n')
    sys.stderr.write('ERROR: unable to find HEADAS environment variable.\n')
    sys.stderr.write('##################################################\n')
    sys.exit(1)

HEADAS = Path(HEADAS_ENV)

modelfile = HEADAS / '../spectral/manager/model.dat'
modelfile = modelfile.resolve()

if not modelfile.is_file():
    sys.stderr.write('##################################################\n')
    sys.stderr.write('ERROR: model.dat file not found:\n')
    sys.stderr.write(str(modelfile) + '\n')
    sys.stderr.write('##################################################\n')
    sys.exit(1)

print(str(modelfile))
sys.exit(0)
