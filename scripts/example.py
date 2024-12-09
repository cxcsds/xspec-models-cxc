"""Example of XSPEC model interface"""

import numpy as np

from matplotlib import pyplot as plt

import xspec_models_cxc as x

x.chatter(0)  # Hide the screen messages

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


egrid = np.arange(0.1, 20, 0.01)
emid = (egrid[:-1] + egrid[1:]) / 2

for kT in [0.1, 0.3, 0.5, 1, 3, 5, 10]:
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

plt.close()

x.abundance('wilm')
x.cross_section('vern')


for nH in [0.01, 0.05, 0.1, 0.5, 1]:
    y = x.TBabs(energies=egrid, pars=[nH])
    plt.plot(emid, y, label=f'nH={nH}', alpha=0.6)

plt.xscale('log')
plt.yscale('log')
plt.ylim(1e-14, 2)

plt.legend()

plt.xlabel('Energy (keV)')
plt.ylabel('Transmission')
plt.title('TBABS model')
add_version()

plt.savefig('example-multiplicative.png')

plt.close()

model = x.TBabs(energies=egrid, pars=[0.05]) * x.apec(energies=egrid, pars=[0.5, 1, 0])
plt.plot(emid, model, label='Unconvolved', c='k', alpha=0.8)

for pars in [[0.1, 0], [0.2, -1], [0.2, 1]]:
    # the model argument gets over-written by gsmooth, hence the copy
    y = x.gsmooth(energies=egrid, pars=pars, model=model.copy())
    plt.plot(emid, y, label=rf'$\sigma$={pars[0]} index={pars[1]}', alpha=0.8)

plt.xscale('log')
plt.yscale('log')

plt.legend()

plt.xlabel('Energy (keV)')
plt.ylabel('Photon/cm$^2$/s')
plt.title('GSMOOTH(TBABS * APEC)')
add_version()

plt.savefig('example-convolution.png')
plt.close()
