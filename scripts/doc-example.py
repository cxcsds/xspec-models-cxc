"""The intro example from the documentation"""

import numpy as np
from matplotlib import pyplot as plt
import xspec_models_cxc as x

egrid = np.arange(0.1, 10, 0.001)
apec = x.info('apec')
phabs = x.info('phabs')
pars_apec = [p.default for p in apec.parameters]
pars_phabs = [p.default for p in phabs.parameters]

yapec = x.apec(energies=egrid, pars=pars_apec)
yphabs = x.phabs(energies=egrid, pars=pars_phabs)
ymodel = yphabs * yapec
emid = (egrid[:-1] + egrid[1:]) / 2

plt.plot(emid, ymodel, label='phabs * apec')

plt.yscale('log')
plt.ylim(1e-9, 0.01)
plt.legend()

plt.xlabel('Energy (keV)')
plt.ylabel('Photon/cm$^2$/s')

kdblur = x.info('kdblur')
pars_kdblur = [p.default for p in kdblur.parameters]

x.kdblur(energies=egrid, pars=pars_kdblur, model=ymodel)
plt.plot(emid, ymodel, alpha=0.8, label='Convolved')
plt.legend()
