"""Can I call smaug?"""

import numpy as np

from matplotlib import pyplot as plt

import xspec_models_cxc as x

vxspec = x.get_version()
print(f"XSPEC version:  {vxspec}")
print(f"Module version: {x.__version__}")

def add_version():
    plt.text(0.98, 0.98, f"XSPEC {vxspec}",
             transform=plt.gcf().transFigure,
             verticalalignment="top",
             horizontalalignment="right")

    plt.text(0.02, 0.98, f"Module {x.__version__}",
             transform=plt.gcf().transFigure,
             verticalalignment="top",
             horizontalalignment="left")


x.cosmology(h0=70, lambda0=0.73, q0=0)

egrid = np.arange(0.1, 10, 0.01)

pars = [0.4 if p.name == 'redshift' else p.default
        for p in x.info('smaug').parameters]

x.setXFLT(1, {'inner': 0.01, 'outer': 0.1, 'width': 360})
x.setXFLT(2, {'inner': 0.1, 'outer': 0.2, 'width': 360})

y1 = x.smaug(energies=egrid, pars=pars, spectrum=1)
y2 = x.smaug(energies=egrid, pars=pars, spectrum=2)

emid = (egrid[:-1] + egrid[1:]) / 2

fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, height_ratios=[2, 1])

ax1.plot(emid, y1, label='Bin 1')
ax1.plot(emid, y2, label='Bin 2')

ax1.set_yscale('log')

ax1.legend()

ax1.set_ylabel('Photons/cm$^2$/s')

ax2.plot(emid, y2 / y1, label='Bin 2 / Bin 1')

ax2.set_xlabel('Energy (keV)')
ax2.set_ylabel('Ratio')

ax2.legend()

add_version()

plt.savefig('smaug.png')
