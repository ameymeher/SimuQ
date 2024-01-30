import yaml
import logging.config
import logging
import numpy as np
import pickle
from hamiltonian_models import Ising
from qiskit_ibm_provider import IBMProvider
from simuq.solver import generate_as

#Setup logger
with open('logging.yaml', encoding="utf8") as ly:
    loggingDict = yaml.safe_load(ly)
logging.config.dictConfig(loggingDict)
logger = logging.getLogger("circuit_setup")

#Ising chain model creation
def generate_base_circuit(N,T,system):
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
    
    #return the circuit
    return Ising_chain

def get_fake_backend(backend):
    from qiskit.providers.fake_provider import FakeWashington, FakeGuadalupe
    if backend == "ibmq_washington":
        return FakeWashington()
    elif backend == "ibmq_guadalupe":
        return FakeGuadalupe()
    else:
        raise Exception("Unsupported backend")

def compile(
        qs,
        backend="ibmq_mumbai",
        aais="heisenberg",
        tol=0.01,
        trotter_num=6,
        verbose=0,
        use_pulse=True,
        state_prep=None,
        use_fake_backend=False,
        with_measure=True
    ):

    #Setting the IBM provider
    api_file = "../ibm_API_key"
    with open(api_file, "r") as f:
            api_key = f.readline().strip()
    provider = IBMProvider(api_key, instance='ibm-q-ncsu/nc-state/quantum-compiler')

    #SimuQ code
    if not use_fake_backend:
        backend = provider.get_backend(backend)
    else:
        backend = get_fake_backend(backend)

    nsite = backend.configuration().n_qubits

    if qs.num_sites > nsite:
        raise Exception("Device has less sites than the target quantum system.")

    if aais == "heisenberg":
        import ibm
        from qiskit_pulse_ibm import transpile

        mach = ibm.generate_qmachine(backend)
        comp = transpile

    layout, sol_gvars, boxes, edges = generate_as(
        qs,
        mach,
        trotter_num,
        solver="least_squares",
        solver_args={"tol": tol},
        override_layout=None,
        verbose=verbose,
    )

    prog = comp(
        backend,
        layout,
        sol_gvars,
        boxes,
        edges,
        use_pulse=use_pulse,
        with_measure=with_measure,
        noise_factor=0
    )

    from qiskit import transpile as transpile_qiskit

    prog = transpile_qiskit(prog, backend=backend)
    layout = layout
    qs_names = qs.print_sites()

    if state_prep is not None:
        prog = prog.compose(state_prep, qubits=layout, front=True)

    return prog

def generate_circuits(N,T,system):

    Ising_chain = generate_base_circuit(N,T,system)
    circuit = compile(Ising_chain,backend=system)

    #Pickling the circuit
    with open("circuit.pickle", 'wb') as handle:
        pickle.dump(circuit, handle, protocol=pickle.HIGHEST_PROTOCOL)

    return "ABC"

print(generate_circuits(4,1,"ibmq_mumbai"))