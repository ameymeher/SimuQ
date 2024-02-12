from qiskit_transpiler import get_pm
import numpy as np
from qiskit import QuantumCircuit
from qiskit.transpiler import InstructionProperties
from qiskit_ibm_provider import IBMProvider
from qiskit_experiments.library import InterleavedRB
from qiskit import QuantumCircuit
import pickle
import datetime

#Setting the IBM provider
api_file = "../../../../ibm_API_key"
with open(api_file, "r") as f:
    api_key = f.readline().strip()
provider = IBMProvider(api_key, instance='ibm-q-ncsu/nc-state/quantum-compiler')

#Setting the parameters for experiments
params = []
for system in ['ibm_brisbane','ibmq_mumbai']:
    with open("../../circuits/{}_10_1.pickle".format(system), "rb") as f:
        circuit = pickle.load(f)
    
    qubits = list(map(lambda x: [x[0][0]],list(circuit[0].calibrations['rx'].keys())))

    for qubit in qubits:
        params.append({'system': system, 'qubit': qubit})    

#Function to conduct the RB experiment
def conduct_rx_rb_experiment(param):
     
    qubit = param['qubit'][0]

    #Getting the backend
    print("Getting the backend for the system: ", param['system'])
    backend = provider.get_backend(param['system'])

    #Circuit to only pass as a gate
    print("Creating the custom rx gate for qubit: ", qubit)
    gate_circuit = QuantumCircuit(1, name='custom_rx_{}'.format(qubit))
    gate_circuit.rx(np.pi/2,0)
    custom_rx = gate_circuit.to_gate()

    #Circuit for getting the calibration
    calibration_circuit = QuantumCircuit(qubit + 1)
    calibration_circuit.rx(np.pi/2,qubit)

    #Getting the calibration
    pm = get_pm(backend)
    calibrated_circuit = pm.run(calibration_circuit)
    calibration = list(calibrated_circuit.calibrations['rx'].values())[0]
    print("Calibration for qubit: ", qubit, " is: ", calibration)

    #Setting the calibration
    backend.target.add_instruction(custom_rx, {(qubit,): InstructionProperties(calibration=calibration)})

    #Creating the interleaved RB experiment
    lengths = np.arange(1, 200, 30)
    num_samples = 10
    seed = 1010
    qubits = [qubit] # make sure it is the qubit added in the backend target
    print("Creating the interleaved RB experiment for qubis: ", qubits)

    int_exp = InterleavedRB(
        custom_rx, qubits, lengths, num_samples=num_samples, seed=seed, backend=backend)

    #Running the experiment
    int_expdata = int_exp.run(backend)

    #Updating the config
    param['job_id'] = int_expdata.job_ids[0]
    print("Job id for the experiment: ", param['job_id'])
    param['calibration'] = calibration
    return param

#Conducting the experiments
updated_rx_params = list(map(conduct_rx_rb_experiment, params))

#Pickle the updated params
now = datetime.datetime.now()
timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
filename = 'params/updated_rx_params_' + timestamp + '.pkl'

with open(filename, 'wb') as f:
    pickle.dump(updated_rx_params, f)