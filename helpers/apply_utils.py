#!/usr/bin/env python

# SPDX-License-Identifier: GPL-3.0-or-later

"""Create the utils code

Usage:

  ./apply_utils.py infile1 infile2 outfile

Add the contents of infile2 (after the marker) to the end of infile1
to create outfile.

The idea is that we want to use infile2 to create the module, but
we also want the same code included in the module.

"""

from pathlib import Path
import sys


def doit(infile1, infile2, outfile):

    out = Path(infile1).read_text()
    out += "\n\n"

    # Extract the infile2 contents
    intext = Path(infile2).read_text()
    token = "#@@START@@\n"
    idx = intext.find(token)
    if idx == -1:
        raise ValueError(f"Unable to find start token in {infile2}")

    out += intext[idx + len(token) + 1:]

    outpath = Path(outfile)
    with outpath.open(mode='wt') as ofh:
        ofh.write(out)


if __name__ == "__main__":

    if len(sys.argv) != 4:
        sys.stderr.write(f"Usage: {sys.argv[0]} infile1 infile2 outfile\n")
        sys.exit(1)

    doit(sys.argv[1], sys.argv[2], sys.argv[3])
