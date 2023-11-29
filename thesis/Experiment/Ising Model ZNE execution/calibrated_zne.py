import time
import yaml
import numpy as np
from SimuQ.thesis.Experiment.utilities.hamiltonian_models import Ising
from SimuQ.thesis.Experiment.utilities.evaluation_metrics import TV
from simuq.qutip import QuTiPProvider
import logging.config
import logging

# Make this configurable parameters for the script
########################################################################################################################
N = 4
T = 1
system = "ibmq_mumbai"
noise_factor = 0

#Setup logger
with open('../../experiments/logging.yaml', encoding="utf8") as ly:
    loggingDict = yaml.safe_load(ly)
logging.config.dictConfig(loggingDict)
logger = logging.getLogger("optimization_level_experiment")

########################################################################################################################
# Ising chain model creation

h = np.array([1 for j in range(N)])
J_chain = np.zeros((N, N))
for j in range(N - 1):
    J_chain[j, j + 1] = 1

J_cycle = np.copy(J_chain)
J_cycle[0, N - 1] = 1

# On the IBM devices, only Ising_chain has a solution, therefore keeping it
logger.info("Creating the model with {} qubits and simulation time to be: {} units".format(N, T))
Ising_chain = Ising(N, T, J_chain, h)
# Ising_cycle = Ising(N, T, J_cycle, h)

########################################################################################################################
# Classical simulation for comparison

qtpp = QuTiPProvider()
qtpp.compile(Ising_chain)
qtpp.run()
res_chain_gt = qtpp.results()

########################################################################################################################
# Experiment run

from ibm_provider_custom import IBMProvider
ibm = IBMProvider(from_file="../ibm_API_key", hub="ibm-q-ncsu", group="nc-state", project="quantum-compiler")
ibm.compile(Ising_chain, backend=system, trotter_num=4, use_pulse=True, noise_factor=0)