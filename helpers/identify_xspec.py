"""
Identify the version of XSPEC being built against by compiling
a small program which calls the XSPEC "get a version" routine.

The assumption is that this only needs the XSUtil library, and
that this is unversioned (i.e. we can hard-code the name).

Is this

- worth the effort?
- how do we automate the compiler choice (e.g. search for clang)

"""

import os
import pathlib
import re
import subprocess


def get_compiler() -> str:
    """Guess the C++ compiler to use.

    If the CXX environment variable is used then use that, otherwise
    try g++ and then clang.

    """
    compiler = os.getenv("CXX")
    if compiler is not None:
        return compiler

    # Do not try anything too clever here.
    #
    for compiler in ["g++", "clang++"]:
        args = [compiler, "--version"]

        try:
            subprocess.run(args, check=True)
            return compiler
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass

    raise ValueError("Use the CXX environment variable to select the C++ compiler to use")


def compile_code(base):
    """Compile the code.

    base gives the location from which we can access /lib and /include.
    Ideally this would be HEADAS but the CXC xspec-modelsonly conda
    package has a different idea.

    """

    basename = "report_xspec_version"
    helpers = pathlib.Path("helpers")

    compiler = get_compiler()
    print(f"** Using compiler: {compiler}")
    args = [compiler,
            str(helpers / f"{basename}.cxx"),
            "-o", str(helpers / basename),
            f"-Wl,-rpath,{base}/lib",
            f"-I{base}/include",
            f"-L{base}/lib",
            "-lXSUtil"
        ]

    subprocess.run(args, check=True)
    return helpers / basename


def get_xspec_macros(base):
    """Return the macro definitions which define the XSPEC version.

    Parameters
    ----------
    base : pathlib.Path
        The path to the HEADAS /lib and /include directories.

    Returns
    -------
    xspec_version, macros : str, list
        The XSPEC version, including the patch level, and then the
        macro definitons to pass to the compiled code.

    """

    code = compile_code(base)
    command = subprocess.run([str(code)],
                             check=True,
                             stdout=subprocess.PIPE)

    xspec_version = command.stdout.decode().strip()

    # split the XSPEC version
    toks = xspec_version.split(".")
    assert len(toks) == 3, xspec_version
    xspec_major = toks[0]
    xspec_minor = toks[1]

    match = re.match(r"^(\d+)(.*)$", toks[2])
    xspec_micro = match[1]
    xspec_patch = None if match[2] == "" else match[2]

    macros = [
        ('BUILD_XSPEC', xspec_version),
        ('BUILD_XSPEC_MAJOR', xspec_major),
        ('BUILD_XSPEC_MINOR', xspec_minor),
        ('BUILD_XSPEC_MICRO', xspec_micro),
    ]

    if xspec_patch is not None:
        macros.append(('BUILD_XSPEC_PATCH', xspec_patch))

    return xspec_version, macros
