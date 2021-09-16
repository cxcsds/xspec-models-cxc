# xspec-models-cxc

Exploring ways to create a Python module that can let users use the
[XSPEC model
library](https://heasarc.gsfc.nasa.gov/xanadu/xspec/manual/XSappendixExternal.html)
with minimal effort. The idea would then be that packages like
[Sherpa](https://github/sherpa/sherpa) and
[3ML](https://github.com/threeML/threeML) could build on this package.

Well, that's the plan.

The home page for this module is
[xspec-models-cxc](https://github.com/cxcsds/xspec-models-cxc) and
have I mentioned that this is **very experimental**?

## LICENSE

This is released under the GNU GPL version 3 as this is built on code
developed for Sherpa and the CIAO contrib packages.

## How to build

You need to have XSPEC 12.12.0 installed, have the `HEADAS` environment
variable set up, and hope that your XSPEC build uses the same versions
of the libraries as mine does (since there's currently no way to query XSPEC for these vaues programatically).

With this you can

```
% git clone https://github.com/cxcsds/xspec-models-cxc
% cd xspec-models-cxc
```

I suggest creating a new venv or conda environment, and then install
with the following (the `--log` option is useful when there are build
failures, which there will be!):

```
% pip install . --log=log
```

The build requires both
[pybind11](https://pybind11.readthedocs.io/en/stable/index.html) and
[parse-xspec](https://github.com/cxcsds/parse_xspec) but they will be
used automatically. Neither is required to use the compiled module.

I am not putting this on [PyPI](https://pypi.org/) yet as there are a
lot of things to work out first!

## Notes

I had to

```
% export LD_LIBRARY_PATH=$HEADAS/lib
```

in order to use the module. I believe it depends on how you built the
XSPEC model library (I am using a full XSPEC installation).

## Example

We need to manually initialize the library with the `init` function (I
haven't hid the screen output as it is useful to see at this time):

```
>>> import xspec_models_cxc as x
>>> x.__version__
'0.0.4'
>>> x.init()
 Solar Abundance Vector set to angr:  Anders E. & Grevesse N. Geochimica et Cosmochimica Acta 53, 197 (1989)
 Cross Section Table set to vern:  Verner, Ferland, Korista, and Yakovlev 1996
```

With this we can do a few things:

- what version of XSPEC are we using?

```
>>> x.get_version()
'12.12.0'
```

- playing with the chatter setting

```
>>> x.chatter()
10
>>> x.chatter(0)
>>> x.chatter()
0
>>> x.chatter(10)
```

- how about abundances tables?

```
>>> x.abundance()
'angr'
>>> x.abundance('lpgp')
 Solar Abundance Vector set to lpgp:  Lodders K., Palme H., Gail H.P., Landolt-Börnstein, New Series, vol VI/4B, pp 560–630 (2009) (Photospheric)
>>> x.abundance()
'lpgp'
>>> x.abundance('angr')
 Solar Abundance Vector set to angr:  Anders E. & Grevesse N. Geochimica et Cosmochimica Acta 53, 197 (1989)
```

It isn't clever enough to notice if you give it an unsupported
abundance name.

- what has atomic number 17?

```
>>> x.elementName(17)
'Cl'
```

- what is the abundance of an element?

```
>>> x.elementAbundance('Cl')
3.160000119351025e-07
>>> x.elementAbundance(17)
3.160000119351025e-07
```

Note that there's limited checking which could be improved:

```
>>> x.elementAbundance('Po')
XSPEC::getAbundance: Invalid element: Po entered, returning 0.
0.0
>>> x.elementAbundance(-4)
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
TypeError: elementAbundance(): incompatible function arguments. The following argument types are supported:
    1. (arg0: str) -> float
    2. (arg0: int) -> float

Invoked with: -4
>>> x.elementAbundance(256)
XSPEC::getAbundance: Invalid element atomic number: 256 entered, returning 0.
0.0
```

- can I evaluate a model?

At the moment we only have a limited number of models - that is those that
are labelled as having a 'C++' interface. On the positive side, this
is all automaticaly generated based on the `model.dat` file from XSPEC.

### APEC

The `model.dat` record for this model is

```
apec           3  0.         1.e20           C_apec    add  0
kT      keV     1.    0.008   0.008   64.0      64.0      .01
Abundanc " "    1.    0.      0.      5.        5.        -0.001
Redshift " "    0.   -0.999  -0.999   10.       10.       -0.01
```

So, if we want to use the default parameters - that is, kT=1,
Abundance=1, Redshift=0 - for the energy grid 0.1-0.2, 0.2-0.3,
0.3-0.4, and 0.4-0.5 we can say:

```
>>> import xspec_models_cxc as x
>>> x.init()
 Solar Abundance Vector set to angr:  Anders E. & Grevesse N. Geochimica et Cosmochimica Acta 53, 197 (1989)
 Cross Section Table set to vern:  Verner, Ferland, Korista, and Yakovlev 1996
>>> help(x.apec)
Help on built-in function apec in module xspec_models_cxc:

apec(...) method of builtins.PyCapsule instance
    apec(arg0: numpy.ndarray[numpy.float64], arg1: numpy.ndarray[numpy.float64]) -> numpy.ndarray[numpy.float64]

    The XSPEC additive apec model (3 parameters).

>>> pars = [1, 1, 0]
>>> egrid = [0.1, 0.2, 0.3, 0.4, 0.5]
>>> x.apec(pars, egrid)
Reading APEC data from 3.0.9

array([2.10839183, 0.31196176, 0.22008776, 0.12295151])
>>>
```

We can see what dufference dropping the abundance to 0 makes:

```
>>> x.apec([1, 0, 0], egrid)
array([0.47038697, 0.21376409, 0.1247977 , 0.08182932])
```

Note that the return values have units of photons/cm^2/s as this is an
XSPEC [additive
model](https://heasarc.gsfc.nasa.gov/xanadu/xspec/manual/Additive.html).

### TBABS

The TBabs is a multiplicative model:

```
TBabs          1   0.03       1.e20          C_tbabs     mul 0
nH       10^22 1.  0.       0.      1E5       1E6       1E-3
```

With the default setting we don't expect much flux to get through for
the selected energy range (~0.1 - 0.5 keV), but this increases as nH
decreases by a magnitude or two:

```
>>> import numpy
>>> egrid = np.arange(0.1, 0.5, 0.05)
>>> x.abundance('wilm')
 Solar Abundance Vector set to wilm:  Wilms, J., Allen, A. & McCray, R. ApJ 542 914 (2000) (abundances are set to zero for those elements not included in the paper).
>>> help(x.TBabs)
Help on built-in function TBabs in module xspec_models_cxc:

TBabs(...) method of builtins.PyCapsule instance
    TBabs(arg0: numpy.ndarray[numpy.float64], arg1: numpy.ndarray[numpy.float64]) -> numpy.ndarray[numpy.float64]

    The XSPEC multiplicative TBabs model (1 parameters).

>>> x.TBabs([1], egrid)
tbvabs Version 2.3
Cosmic absorption with grains and H2, modified from
Wilms, Allen, & McCray, 2000, ApJ 542, 914-924
Questions: Joern Wilms
joern.wilms@sternwarte.uni-erlangen.de
joern.wilms@fau.de

http://pulsar.sternwarte.uni-erlangen.de/wilms/research/tbabs/

PLEASE NOTICE:
To get the model described by the above paper
you will also have to set the abundances:
   abund wilm

Note that this routine ignores the current cross section setting
as it always HAS to use the Verner cross sections as a baseline.
array([1.28407670e-175, 9.06810629e-062, 9.04157274e-029, 3.26034136e-016,
       2.02047907e-010, 5.09045226e-007, 3.97658583e-005])
>>> x.TBabs([0.1], egrid)
array([3.24234405e-18, 7.86595867e-07, 1.56900525e-03, 2.82700325e-02,
       1.07286588e-01, 2.34787860e-01, 3.63037122e-01])
>>> x.TBabs([0.01], egrid)
array([0.01782731, 0.24523089, 0.52427897, 0.70005576, 0.79993471,
       0.86510249, 0.90363929])
```

Note that the return values have no units as this is an XSPEC
[multiplicative
model](https://heasarc.gsfc.nasa.gov/xanadu/xspec/manual/Multiplicative.html).
