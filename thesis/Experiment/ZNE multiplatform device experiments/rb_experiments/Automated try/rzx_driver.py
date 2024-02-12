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
for system in ['ibmq_mumbai']:
    with open("../../circuits/{}_4_1.pickle".format(system), "rb") as f:
        circuit = pickle.load(f)
    
    qubits = list(map(lambda x: [x[0][0],x[0][1]],list(circuit[0].calibrations['rzx'].keys())))

    for qubit in qubits:
        params.append({'system': system, 'qubit': qubit})    

#Function to conduct the RB experiment
def conduct_rzx_rb_experiment(param):
     
    qubit = param['qubit']

    #Getting the backend
    print("Getting the backend for the system: ", param['system'])
    backend = provider.get_backend(param['system'])

    #Circuit to only pass as a gate
    print("Creating the custom rzx gate for qubits: ", qubit)
    gate_circuit = QuantumCircuit(2, name='custom_rzx_{}'.format(qubit))
    gate_circuit.rzx(np.pi/2,0,1)
    custom_rzx = gate_circuit.to_gate()

    #Circuit for getting the calibration
    calibration_circuit = QuantumCircuit(max(qubit)+1)
    calibration_circuit.rzx(np.pi/2,qubit[0],qubit[1])

    #Getting the calibration
    pm = get_pm(backend)
    calibrated_circuit = pm.run(calibration_circuit)
    calibration = list(calibrated_circuit.calibrations['rzx'].values())[0]
    #print("Calibration for qubit: ", qubit, " is: ", calibration)

    #Setting the calibration
    backend.target.add_instruction(custom_rzx, {(qubit[0],qubit[1]): InstructionProperties(calibration=calibration)})
    print(backend.configuration().coupling_map)

    #Creating the interleaved RB experiment
    lengths = np.arange(1, 200, 30)
    num_samples = 10
    seed = 1010
    qubits = (qubit[0],qubit[1]) # make sure it is the qubit added in the backend target
    print("Creating the interleaved RB experiment for qubits: ", qubits)

    int_exp = InterleavedRB(
        custom_rzx, qubits, lengths, num_samples=num_samples, seed=seed, backend=backend)

    #Running the experiment
    int_expdata = int_exp.run(backend)

    #Updating the config
    param['job_id'] = int_expdata.job_ids[0]
    print("Job id for the experiment: ", param['job_id'])
    param['calibration'] = calibration
    return param

#Conducting the experiments
updated_rzx_params = list(map(conduct_rzx_rb_experiment, params))

#Pickle the updated params
now = datetime.datetime.now()
timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
filename = 'params/updated_rzx_params_' + timestamp + '.pkl'

with open(filename, 'wb') as f:
    pickle.dump(updated_rzx_params, f)