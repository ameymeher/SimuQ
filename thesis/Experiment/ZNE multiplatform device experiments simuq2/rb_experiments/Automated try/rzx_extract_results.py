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
import pickle

#Setting the IBM provider
api_file = "../../../../ibm_API_key"
with open(api_file, "r") as f:
        api_key = f.readline().strip()
provider = IBMProvider(api_key, instance='ibm-q-ncsu/nc-state/quantum-compiler')

#Unpickle
filename = "params/updated_rzx_params_nazca.pkl"
with open(filename, "rb") as f:
    params = pickle.load(f)

#Function to extract the results
def extract_results(param):

    qubit = param['qubit']

    #Circuit to only pass as a gate
    gate_circuit = QuantumCircuit(2, name='custom_rzx_{}'.format(qubit))
    gate_circuit.rzx(np.pi/2,0,1)
    custom_rzx = gate_circuit.to_gate()

    #Set the backend calibration
    backend = provider.get_backend(param['system'])
    backend.target.add_instruction(custom_rzx, {(qubit[0],qubit[1]): InstructionProperties(calibration=param['calibration'])})

    #Creating the interleaved RB experiment
    lengths = np.arange(1, 200, 30)
    num_samples = 10
    seed = 1010
    qubits = (qubit[0],qubit[1]) # make sure it is the qubit added in the backend target
    print("Creating the interleaved RB experiment for qubis: ", qubits)

    int_exp = InterleavedRB(
        custom_rzx, qubits, lengths, num_samples=num_samples, seed=seed, backend=backend)

    #Running analysis
    int_expdata = ExperimentData(experiment=int_exp)
    int_expdata.add_jobs(provider.retrieve_job(param['job_id']))
    int_exp.analysis.run(int_expdata,replace_results=True)
    int_expdata.block_for_results()
    
    #Extracting the results
    param['error'] = int_expdata.analysis_results("EPC").value
    print("Error for qubit: ", qubit, " is: ", param['error'].nominal_value)
    print("Std dev for qubit: ", qubit, " is: ", param['error'].std_dev)
    return param


params = list(filter(lambda x: 1 if x['system'] == 'ibm_nazca' else 0,params))
results = list(map(extract_results,params))

#Save the results
filename = "params/rzx_errors_nazca.pkl"
with open(filename, "wb") as f:
    pickle.dump(results, f)