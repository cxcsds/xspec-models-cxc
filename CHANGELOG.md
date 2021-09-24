# Changes in xspec-models-cxc

## 0.0.25

The `cosmology` routine now returns a dictionary with the key `h0`
rather than `H0` as it matches the "set" version, which uses `h0` to
set the Hubble constant.

There are internal changes to separate out the template code from the
module definition so we can use it to support user models, but that is
still a long-way off.

## 0.0.24

Support direct access to models via the C++ RealArray type. The C++
models now have a `<name>_` variant which accepts
`xspec_models_cxc.RealArray` arguments rather than NumPy ones.  So far
it does not seem to make things any faster, but more experimentation
is needed.

The convolution models have not been updated to use this interface.

## 0.0.23

First version of a test suite.

## 0.0.22

The tableModel function now takes an optional model argument.

Note that model arguments have to have exactly the right data type -
so for tableModel that is numpy.float32 - otherwise they won't get
updated in place. It really should error out if the types don't match.
Or we drop the model argument support.

## 0.0.21

You can now import xspec_models_cxc even if the XSPEC libraries can't
be found (e.g. LD_LIBRARY_PATH is not set):

```
>>> import xspec_models_cxc
Unable to import compiled XSPEC models
```

You can still access the model data - i.e. with `info` and
`list_models`.

## 0.0.20

Initial support for XSPEC table models.

There are two parts to using XSPEC table models:

- parsing the file structure to find out about the parameters
- using the model

We only support the latter at this time.

```
>>> impoer xspec_models_cxc as x
>>> infile = 'RCS.mod'
>>> egrid = np.arange(0.1, 1, 0.1)
>>> pars = [1, 0.1, 0.1]
>>> x.tableModel(infile, "add", pars=pars, energies=egrid)
array([2.9454877 , 2.6992798 , 1.9146949 , 1.1823336 , 0.6685946 ,
       0.35602048, 0.1817703 , 0.09004311], dtype=float32)
```

It's very easy to make things go boom - e.g. using the wrong
number of parameters

```
>>> x.tableModel(infile, "add", pars=[1, 2], energies=egrid)
Segmentation fault (core dumped)
```

## 0.0.19

We can now find out about the parameter values for a model:

```
>>> import xspec_models_cxc as x
>>> m = x.info('apec')
>>> m.name
'apec'
>>> m.modeltype
<ModelType.Add: 1>
>>> [(p.name, p.default, p.units) for p in m.parameters]
[('kT', 1.0, 'keV'), ('Abundanc', 1.0, None), ('Redshift', 0.0, None)]
```

## 0.0.18

Provide the first access to the model.dat-derived values from
Python. There are two routines:

  info(name)
  list_models(modeltype=None, language=None)

Note that this does not provide access to the parameter information.

## 0.0.17

Reworked the code layout so that the compiled is now available as
`xspec_models_cxc._compiled` which is re-exported by the
`xspec_models_cxc` module. Users should see no difference when
importing `xspec_models_cxc`. This is just to set up future changes to
add model information, but I am not 100% convinced the build is
correct.

## 0.0.16

Oops: a check I added to make an error message more readable lead to
it always failing (when it was used correctly). Oops.

## 0.0.15

Models can now work in-place - that is over-write an input array
rather than allocating a new array at each call. The convolution
models now always use this - over-writing the model argument - and the
other models can use this by setting the out argument. The docstrings
for the models have "; inplace" added to them to indicate this
behavior. For example

```
>>> help(xspec_models_cxc.apec)
Help on built-in function apec in module xspec_models_cxc:

apec(...) method of builtins.PyCapsule instance
    apec(*args, **kwargs)
    Overloaded function.

    1. apec(pars: numpy.ndarray[numpy.float64], energies: numpy.ndarray[numpy.float64], spectrum: int = 1, initStr: str = '')
-> numpy.ndarray[numpy.float64]

    The XSPEC additive apec model (3 parameters).

    2. apec(pars: numpy.ndarray[numpy.float64], energies: numpy.ndarray[numpy.float64], out: numpy.ndarray[numpy.float64], spectrum: int = 1, initStr: str = '') -> numpy.ndarray[numpy.float64]

    The XSPEC additive apec model (3 parameters); inplace.
```

The change to the convolution models means that the example script
had to change from

```
for pars in [...];
    y = x.gsmooth(ebergies=egrid, pars=pars, model=model)
	plt.plot(...)
```

to

```
for pars in [...];
    # the model argument gets over-written by gsmooth
    y = x.gsmooth(ebergies=egrid, pars=pars, model=model.copy())
	plt.plot(...)
```

## 0.0.14

Now supports convolution models. We now provide access to 230 of the
231 models in the XSPEC 12.12.0 / heasoft-6.29 release. The
unsupported model is the "pileup" model - it's the one "acn" model in
the library.

## 0.0.13

Separated out the template code from `setup.py` to a separate module
(`helpers.template`) to make it look like I have some idea of coding
standards.

## 0.0.12

Added SPDX-Licencse-Identifier tags. Am I doing it right?

## 0.0.11

Improve support for getting and setting features used by the
XSPEC model library, including

- cross-section table (`cross_section`)
- number of elements in the abundance table (`numberElements`)
- the Cosmology settings (`cosmology`); note that there we can only
  get or set all three values at once (H0, q0, lambda0) even though we
  could add support to change them individually
- support for a number of "databases":
  - XFLT
  - model string
  - keyword
  These have subtly-different APIs and I wonder if it would be
  better to just use a dictionary. The naming is also unclear.

There have also been some changes to provide better - or at least
somewhat-more-appropriate for Python - errors.

Of note is that the current setup leaves the cosmology settings
initially at (0.0, 0.0, 0.0). This is less-than ideal.

Technically we should now be able to use the SMAUG model, but I have
not tested it, other than showing it picks up the XFLT values.

## 0.0.10

Support the `spectrum` argument to all models and, for non-FORTRAN
models, the `initStr` argument.

## 0.0.9

Support C-style models. This bumps the number of supported models to
209 (there are 8 new models in this release).

## 0.0.8

An internal change to better use XSPEC types and which simplifies the
internals (no need to re-create the FORTRAN signatures).

## 0.0.7

Support FORTRAN models (at least for additive and multiplicative
models). This bumps the number of models from 115 to 201.

Note that a FORTRAN compiler is not required (although it will have
been needed to build XSPEC).

## 0.0.6

The initalization of the XSPEC model library is now done
automatically, the first time any routine is called, rather than
requiring an explicit call to a `init` function. The screen output the
initialization creates - that is, displaying the default abundance and
cross-section tables - has now been hidden.

The error-handling has been improved to raise errors other than
RuntimeError when appropriate.

## 0.0.5

Improve the module documentation. It's still not great but it is a
move in the right direction.

## 0.0.4

Start transitioning to `setup.cfg`. This seems to work...

There should be no functional changes in this release, other than that
NumPy shuold now be installed if not already available.

## 0.0.3

The first steps in auto-generating code: all the C++-style additive
and multiplicative models are now supported (there are 115 of
them). We use the [parse-xspec](https://github.com/cxcsds/parse_xspec)
package to extract the information from the `model.dat` file, but this
is handled for you at build time and isn't needed at runtime.

## 0.0.2

There is no functional change but the model interface is generated by
a template rather than being hard coded.

## 0.0.1

A minimum viable product to show an interface to the XSPEC model
library that lets you call some functions and evaluate a model.

Issues include, but are not limited to:

- the model interface is not automatically generated
- many missing functions
- there is no information about each model
- initialization is manual
- how can we use the functionality to support user models
  (from a different Python package)
- the build is fragile
