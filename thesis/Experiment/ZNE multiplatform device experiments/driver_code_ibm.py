import threading
import yaml
import logging.config
import logging
import pickle
from datetime import datetime
from reliability_utility_ibm import get_gate_fidelities
from circuit_setup import generate_circuits

#Setup logger
with open('logging.yaml', encoding="utf8") as ly:
    loggingDict = yaml.safe_load(ly)
logging.config.dictConfig(loggingDict)
logger = logging.getLogger("driver_code_ibm")

parameters = []
systems = ['ibmq_mumbai']

for N in range(4,5):
    for T in range(1,3):
        for system in systems:
            parameters.append({"N" : N, "T" : T, "system" : system})

#Generate the circuits for each of the parameters
circuits = list(map(lambda x: generate_circuits(x["N"],x["T"],x["system"]),parameters))

#Conduct the Interleaved RB experiment to get the fidelities and pickle the results
def interleaved_rb_experiments():

    #Conduct the experiments
    interleaved_rb_results = list(map(lambda x: get_gate_fidelities(x[0],x[1]),zip(circuits,parameters)))

    #Pickle the results
    filename = "interleaved_rb_results/" + datetime.now().strftime("%d_%m_%Y_%H_%M_%S") + ".pickle"
    with open(filename, 'wb') as handle:
        pickle.dump(interleaved_rb_results, handle, protocol=pickle.HIGHEST_PROTOCOL)

def hamiltonian_simulation_experiments():
    print("Hamiltonian simulation experiment underway")

interleaved_rb_experiments_thread = threading.Thread(target=interleaved_rb_experiments)
hamiltonian_simulation_experiments_thread = threading.Thread(target=hamiltonian_simulation_experiments)

#Parallel execution of both
interleaved_rb_experiments_thread.start()
hamiltonian_simulation_experiments_thread.start()

#Wait for all tasks to complete
interleaved_rb_experiments_thread.join()
hamiltonian_simulation_experiments_thread.join()

#Post processing to generate the reliability of each of the circuits
#Pickle these results as well


#Final tasks
print("All tasks completed")