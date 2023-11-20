import time
import yaml
import numpy as np
from SimuQ.thesis.Experiment.utilities.hamiltonian_models import Ising
from SimuQ.thesis.Experiment.utilities.evaluation_metrics import TV
from simuq.qutip import QuTiPProvider
import logging.config
import logging

#Setup logger
with open('../../experiments/logging.yaml', encoding="utf8") as ly:
    loggingDict = yaml.safe_load(ly)
logging.config.dictConfig(loggingDict)
logger = logging.getLogger("optimization_level_experiment")

def experiment(ibm,N,T,system,noise_factor):
    
    tv_value = -1
    execution_time = 0
    
    try:
        #Make this configurable parameters for the script
        ########################################################################################################################
        #Ising chain model creation
        
        h = np.array([1 for j in range(N)])
        J_chain = np.zeros((N, N))
        for j in range(N - 1):
            J_chain[j, j + 1] = 1
        
        J_cycle = np.copy(J_chain)
        J_cycle[0, N - 1] = 1
        
        #On the IBM devices, only Ising_chain has a solution, therefore keeping it
        logger.info("Creating the model with {} qubits and simulation time to be: {} units".format(N,T))
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
        
        ibm.compile(Ising_chain, backend=system, trotter_num=4,use_pulse=True, noise_factor=noise_factor)
        ibm.run()
        
        job = ibm.return_job()
        
        start_time = time.time()
        while job.status().name == "QUEUED":
            time.sleep(30)
            print("Time passed till now: {}".format(time.time() - start_time))
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        res_ibm_chain_real = ibm.results(on_simulator=False)
        tv_value = TV(res_chain_gt, res_ibm_chain_real)
        #print("Time for the complete execution: {}".format(end_time - start_time))
        
        ########################################################################################################################

    finally:
        return tv_value, execution_time



from ibm_provider_custom import IBMProvider
ibm = IBMProvider(from_file="../ibm_API_key", hub="ibm-q-ncsu", group="nc-state", project="quantum-compiler")

for N in range(7,16):
    for T in range(1,4):
        for noise_factor in range(6):
            logger.info(experiment(ibm, N, T, "ibmq_mumbai", noise_factor))

