from qiskit_ibm_provider import IBMProvider
import pickle

provider = IBMProvider()
backend_name = ['ibm_brisbane','ibmq_mumbai','ibm_kyoto']

def get_error_rates(backend_name):
    backend = provider.get_backend(backend_name)
    backend_props = backend.properties()

    basis_gate_errors = {}

    for basis_gate in backend.configuration().basis_gates:
        basis_gate_errors[basis_gate] = []
        for gate_props in backend_props.gates:
            data = gate_props.to_dict()
            if data['gate'] == basis_gate:
                for param in data['parameters']:
                    if param['name'] == 'gate_error':
                        basis_gate_errors[basis_gate].append({"qubits" : data['qubits'], "error": param['value']})

    #Get the data
    with open('error_rates/{}.pkl'.format(backend_name), 'wb') as f:
        pickle.dump(basis_gate_errors, f, protocol=pickle.HIGHEST_PROTOCOL)

    return True

list(map(lambda x: get_error_rates(x),backend_name))