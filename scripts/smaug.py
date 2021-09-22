"""Can I call smaug?"""

import numpy as np
import xspec_models_cxc as x

print(f"Using: {x.get_version()}")

x.cosmology(h0=70, lambda0=0.73, q0=0)

egrid = np.arange(0.1, 10, 0.01)

pars = [0.4 if p.name == 'redshift' else p.default
        for p in x.info('smaug').parameters]

x.setXFLT(1, {'inner': 0.01, 'outer': 0.1, 'width': 360})
x.setXFLT(2, {'inner': 0.1, 'outer': 0.2, 'width': 360})

y1 = x.smaug(energies=egrid, pars=pars, spectrum=1)
y2 = x.smaug(energies=egrid, pars=pars, spectrum=2)

emid = (egrid[:-1] + egrid[1:]) / 2

plt.plot(emid, y1, label='Bin 1')
plt.plot(emid, y2, label='Bin 2')

plt.yscale('log')

plt.legend()

plt.xlabel('Energy (keV)')
plt.ylabel('Photons/cm$^2$/s')

plt.savefig('smaug.png')
