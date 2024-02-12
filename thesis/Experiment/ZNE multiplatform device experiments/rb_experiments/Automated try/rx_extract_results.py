import numpy as np
from qiskit import QuantumCircuit
from qiskit_ibm_provider import IBMProvider
from qiskit_experiments.library import InterleavedRB
from qiskit import QuantumCircuit
from qiskit_experiments.framework import ExperimentData
from qiskit.transpiler import InstructionProperties
import pickle
import os
import glob

#Setting the IBM provider
api_file = "../../../../ibm_API_key"
with open(api_file, "r") as f:
        api_key = f.readline().strip()
provider = IBMProvider(api_key, instance='ibm-q-ncsu/nc-state/quantum-compiler')

#Unpickle the latest file from the folder params based on timestamp
list_of_files = glob.glob('params/*')

latest_file = max(list_of_files, key=os.path.getctime)
with open(latest_file, "rb") as f:
    params = pickle.load(f)

#Function to extract the results
def extract_results(param):

    qubit = param['qubit'][0]

    #Circuit to only pass as a gate
    gate_circuit = QuantumCircuit(1, name='custom_rx_{}'.format(param['qubit']))
    gate_circuit.rx(np.pi/2,0)
    custom_rx = gate_circuit.to_gate()

    #Set the backend calibration
    backend = provider.get_backend(param['system'])
    backend.target.add_instruction(custom_rx,{(qubit,): InstructionProperties(calibration=param['calibration'])})

    #Creating the interleaved RB experiment
    lengths = np.arange(1, 200, 30)
    num_samples = 10
    seed = 1010
    qubits = [qubit] # make sure it is the qubit added in the backend target
    print("Creating the interleaved RB experiment for qubis: ", qubits)

    int_exp = InterleavedRB(
        custom_rx, qubits, lengths, num_samples=num_samples, seed=seed, backend=backend)

    #Running analysis
    int_expdata = ExperimentData(experiment=int_exp)
    int_expdata.add_jobs(provider.retrieve_job(param['job_id']))
    int_exp.analysis.run(int_expdata,replace_results=True)
    int_expdata.block_for_results()
    
    #Extracting the results
    param['error'] = int_expdata.analysis_results("EPC").value
    print("Error for qubit: ", qubit, " is: ", param['error'].nominal_value)
    return param


params = list(filter(lambda x: 1 if x['system'] == 'ibmq_mumbai' else 0,params))
results = list(map(extract_results,params))
