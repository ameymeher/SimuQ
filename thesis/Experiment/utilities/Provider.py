from qiskit_ibm_provider import IBMProvider

def get_provider():
    with open('../ibm_API_key', 'r') as file:
        token = file.readline()

    return IBMProvider(token=token, instance="ibm-q-ncsu/nc-state/quantum-compiler")