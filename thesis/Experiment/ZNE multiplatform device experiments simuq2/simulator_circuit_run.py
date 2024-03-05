import pickle
from qiskit_ibm_provider import IBMProvider
from qiskit import execute
from qiskit_ibm_runtime import Sampler, Options
from qiskit.providers.fake_provider import FakeMumbai
from qiskit_aer.noise import NoiseModel

api_file = "../../ibm_API_key"
with open(api_file, "r") as f:
    api_key = f.readline().strip()
provider = IBMProvider(api_key, instance='ibm-q-ncsu/nc-state/quantum-compiler')

from qiskit_aer.noise import NoiseModel

noise_model = NoiseModel.from_backend(FakeMumbai()).to_dict()
simulator = provider.get_backend("ibmq_qasm_simulator")
simulator.options.update_options(noise_model=noise_model)

job_params = []

for N in range(4,11):
    for T in range(1,3):
        for system in ['ibmq_mumbai']:
            filename = "circuits/" + system + "_" + str(N) + "_" + str(T) + ".pkl"
            with open(filename, 'rb') as handle:
                circuit = pickle.load(handle)['circuit']

            job = execute(circuit, shots=4096, backend=simulator)

            #Append the job parameters
            job_params.append({'system': system, 'N': N, 'T': T, 'job_id': job.job_id()})
            print(job_params)

#Save the job parameters
with open("circuits/job_params_simulator.pkl", "wb") as f:
    pickle.dump(job_params, f)