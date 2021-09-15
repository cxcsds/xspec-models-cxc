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

This should install [pybind11](https://pybind11.readthedocs.io/en/stable/index.html)
automatically, but if not you can just say

```
% pip install pybind11
```

I am not putting this on [PyPI](https://pypi.org/) yet as there are a
lot of things to work out first!

## Example

You will need to ensure that numpy is installed for the following
example!

We need to manually initialize the library with the `init` function (I
haven't hid the screen output as it is useful to see at this time):

```
>>> import xspec_models_cxc as x
>>> x.__version__
'0.0.1'
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

At the moment we only have the apec model. We can evaluate it for the
default parameters of [1, 1, 0] (that is, kT=1, Abundance=1, Redshift=0)
for the energy grid 0.1-0.2, 0.2-0.3, 0.3-0.4, and 0.4-0.5 with

```
>>> import xspec_models_cxc as x
>>> x.init()
 Solar Abundance Vector set to angr:  Anders E. & Grevesse N. Geochimica et Cosmochimica Acta 53, 197 (1989)
 Cross Section Table set to vern:  Verner, Ferland, Korista, and Yakovlev 1996
>>> pars = [1, 1, 0]
>>> egrid = [0.1, 0.2, 0.3, 0.4, 0.5]
>>> x.apec(pars, egrid)
Reading APEC data from 3.0.9

array([2.10839183, 0.31196176, 0.22008776, 0.12295151])
>>>
```

Note that the return values have units of photons/cm^2/s as this is an
XSPEC [additive
model](https://heasarc.gsfc.nasa.gov/xanadu/xspec/manual/Additive.html).
