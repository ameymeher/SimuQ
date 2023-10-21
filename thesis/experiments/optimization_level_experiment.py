import time
import numpy as np
from hamiltonian_models import Ising
from evaluation_metrics import TV
from ibm_provider_custom import IBMProvider
from simuq.qutip import QuTiPProvider


#Make this configurable parameters for the script
N, T = 4, 1

########################################################################################################################
#Ising chain model creation

h = np.array([1 for j in range(N)])
J_chain = np.zeros((N, N))
for j in range(N - 1):
    J_chain[j, j + 1] = 1

J_cycle = np.copy(J_chain)
J_cycle[0, N - 1] = 1

#On the IBM devices, only Ising_chain has a solution, therefore keeping it
Ising_chain = Ising(N, T, J_chain, h)
#Ising_cycle = Ising(N, T, J_cycle, h)

########################################################################################################################
#Classical simulation for comparison

qtpp = QuTiPProvider()
qtpp.compile(Ising_chain)
qtpp.run()
res_chain_gt = qtpp.results()

########################################################################################################################
#Experiment run

ibm = IBMProvider(from_file="../ibm_API_key", hub="ibm-q-ncsu", group="nc-state", project="quantum-compiler")

ibm.compile(Ising_chain, backend="ibm_lagos", trotter_num=4)
ibm.run()

job = ibm.return_job()

start_time = time.time()
while job.status().name == "QUEUED":
    time.sleep(30)
    print("Time passed till now: {}".format(time.time() - start_time))

end_time = time.time()
execution_time = end_time - start_time

res_ibm_chain_real = ibm.results(on_simulator=False)
print(TV(res_chain_gt, res_ibm_chain_real))
print("Time for the complete execution: {}".format(end_time - start_time))

########################################################################################################################