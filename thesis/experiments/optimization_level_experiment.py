import time
import yaml
import numpy as np
from hamiltonian_models import Ising
from evaluation_metrics import TV
from ibm_provider_custom import IBMProvider
from simuq.qutip import QuTiPProvider
import logging.config
import logging

#Setup logger
with open('logging.yaml',encoding="utf8") as ly:
    loggingDict = yaml.safe_load(ly)
logging.config.dictConfig(loggingDict)
logger = logging.getLogger("optimization_level_experiment")


def experiment(ibm,N,T,system,optimization_level,use_pulse):
    
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
        
        ibm.compile(Ising_chain, backend=system, trotter_num=4,optimization_level=optimization_level,use_pulse=use_pulse)
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
        return  tv_value, execution_time




ibm = IBMProvider(from_file="../ibm_API_key", hub="ibm-q", group="open", project="main")


# for N in range(3,7):
#     for T in range(1,4):
#         for optimization_level in range(1,4):
#             logger.info(experiment(ibm, N, T, "ibm_nairobi", optimization_level,True))
#             logger.info(experiment(ibm, N, T, "ibm_nairobi", optimization_level,False))
            
#         logger.info(experiment(ibm, N, T, "ibm_nairobi", None,True))
#         logger.info(experiment(ibm, N, T, "ibm_nairobi", None,False))
            
print(experiment(ibm, 4, 1, "ibm_nairobi", 3,True))
# print(experiment(ibm, 4, 1, "ibm_nairobi", 2,True))
# print(experiment(ibm, 4, 1, "ibm_nairobi", 1,True))
# print(experiment(ibm, 4, 1, "ibm_nairobi", None,True))
# print(experiment(ibm, 4, 1, "ibm_nairobi", 3,0))
# print(experiment(ibm, 4, 1, "ibm_nairobi", 2,1))
# print(experiment(ibm, 4, 1, "ibm_nairobi", 2,0))
# print(experiment(ibm, 4, 1, "ibm_nairobi", 1,1))
# print(experiment(ibm, 4, 1, "ibm_nairobi", 1,0))
# print(experiment(ibm, 4, 1, "ibm_nairobi", 0,1))
# print(experiment(ibm, 4, 1, "ibm_nairobi", 0,0))
# print(experiment(ibm, 4, 1, "ibm_nairobi", None,1))
# print(experiment(ibm, 4, 1, "ibm_nairobi", None,0))
    
# for N in range(3,7):
#         for T in range(1,11):
#             for optimization_level in range(0,4):
#                 tv_value , execution_time = experiment(ibm, N, T, "ibm_nairobi", optimization_level))

#             tv_value , execution_time = experiment(ibm, N, T, "ibm_nairobi", None))
