import pickle
from qiskit_ibm_provider import IBMProvider
#from qiskit import execute
from qiskit_ibm_runtime import QiskitRuntimeService, Sampler, Options


api_file = "../../ibm_API_key"
with open(api_file, "r") as f:
    api_key = f.readline().strip()
provider = IBMProvider(api_key, instance='ibm-q-ncsu/nc-state/quantum-compiler')


service = QiskitRuntimeService(channel="ibm_quantum")

job_params = []

for N in [4,6,8,10]:
    for T in [0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0,1.5,2.0]:
        for system in ['ibm_brisbane','ibm_kyoto','ibm_sherbrooke','ibm_nazca']:
            filename = "circuits/" + system + "_" + str(N) + "_" + str(T) + ".pkl"
            with open(filename, 'rb') as handle:
                circuit = pickle.load(handle)['circuit']
            
            #Get the backend
            #backend = provider.get_backend(system)
            #job = backend.run(circuit, shots=4096)
            #job = execute(circuit, shots=4096, backend=backend)

            #Execute using Sampler
            backend = service.backend(system)
            options = Options()
            options.resilience_level = 1
            sampler = Sampler(backend=backend,options=options)

            job = sampler.run(circuit, shots=4096)

            #Append the job parameters
            job_params.append({'system': system, 'N': N, 'T': T, 'job_id': job.job_id()})

print(job_params)

#Save the job parameters
with open("circuits/job_params_granular_T_sampler.pkl", "wb") as f:
    pickle.dump(job_params, f)