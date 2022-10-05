"""Example of XSPEC model interface"""

import numpy as np

from matplotlib import pyplot as plt

import xspec_models_cxc as x

x.chatter(0)  # Hide the screen messages

vxspec = x.get_version()
print(f"Version: {vxspec}")

def add_version():
    plt.text(0.98, 0.98, f"XSPEC {vxspec}",
             transform=plt.gcf().transFigure,
             verticalalignment="top",
             horizontalalignment="right")


egrid = np.arange(0.1, 11, 0.01)
emid = (egrid[:-1] + egrid[1:]) / 2

for kT in [0.3, 0.5, 1, 3, 5, 10]:
    y = x.apec(energies=egrid, pars=[kT, 1, 0])
    plt.plot(emid, y, label=f'kT={kT}', alpha=0.6)

plt.xscale('log')
plt.yscale('log')

plt.legend()

plt.xlabel('Energy (keV)')
plt.ylabel('Photon/cm$^2$/s')
plt.title('APEC model: Abundance=1 Redshift=0')
add_version()

plt.savefig('example-additive.png')

plt.clf()

for nH in [0.01, 0.05, 0.1, 0.5, 1]:
    y = x.phabs(energies=egrid, pars=[nH])
    plt.plot(emid, y, label=f'nH={nH}', alpha=0.6)

plt.xscale('log')
plt.yscale('log')

plt.legend()

plt.xlabel('Energy (keV)')
plt.ylabel('Relative')
plt.title('PHABS model')
add_version()

plt.savefig('example-multiplicative.png')

plt.clf()

model = x.phabs(energies=egrid, pars=[0.05]) * x.apec(energies=egrid, pars=[0.5, 1, 0])
plt.plot(emid, model, label='Unconvolved', c='k', alpha=0.8)

for pars in [[0.1, 0], [0.2, -1], [0.2, 1]]:
    # the model argument gets over-written by gsmooth
    y = x.gsmooth(energies=egrid, pars=pars, model=model.copy())
    plt.plot(emid, y, label=f'$\sigma$={pars[0]} index={pars[1]}', alpha=0.8)

plt.xscale('log')
plt.yscale('log')

plt.legend()

plt.xlabel('Energy (keV)')
plt.ylabel('Photon/cm$^2$/s')
plt.title('GSMOOTH(PHABS * APEC)')
add_version()

plt.savefig('example-convolution.png')
