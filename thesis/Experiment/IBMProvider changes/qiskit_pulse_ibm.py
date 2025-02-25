import networkx as nx
from qiskit import QuantumCircuit
from qiskit.pulse import DriveChannel, GaussianSquare, ShiftPhase

from qiskit_transpiler import get_pm


def get_n_link(backend):
    configuration = backend.configuration()
    defaults = backend.defaults()
    n = configuration.num_qubits

    connected_pairs_cnot = configuration.coupling_map
    instruction_schedule_map = defaults.instruction_schedule_map

    def get_control_qubit(q1, q2):  # Control performs Z
        try:
            cx_sched = instruction_schedule_map.get("cx", qubits=(q1, q2))
        except:
            try:
                cx_sched = instruction_schedule_map.get("ecr", qubits=(q1, q2))
            except:
                cx_sched = instruction_schedule_map.get("cz", qubits=(q1, q2))
        supported = False
        for time, inst in cx_sched.instructions:
            if isinstance(inst.channel, DriveChannel) and not isinstance(inst, ShiftPhase):
                if isinstance(inst.pulse, GaussianSquare):
                    target = inst.channel.index
                    control = q1 if target == q2 else q2
                    supported = True
        if not supported:
            raise ValueError("This machine is not supported!")
        return control

    link = []
    for item in connected_pairs_cnot:
        if get_control_qubit(item[0], item[1]) == item[0]:
            link.append(item)

    return n, link


def clean_as(boxes, edges, backend, with_measure=True,noise_factor=0):
    n, link = get_n_link(backend)
    circ = QuantumCircuit(n)
    DG = nx.DiGraph()
    DG.add_nodes_from([i for i in range(len(boxes))])
    DG.add_edges_from(edges)
    topo_order = list(nx.topological_sort(DG))
    for i in range(len(boxes)):
        idx = topo_order[i]
        t = boxes[idx][1]
        for (line, ins), params in boxes[idx][0]:
            if line < n:
                if ins == 0:
                    q = line
                    for _ in range(noise_factor):
                        circ.rz(-params[1], q)
                        circ.rx(2 * params[0] * t, q)
                        circ.rz(params[1], q)
                        circ.rz(-params[1], q)
                        circ.rx(-2 * params[0] * t, q)
                        circ.rz(params[1], q)
                    circ.rz(-params[1], q)
                    circ.rx(2 * params[0] * t, q)
                    circ.rz(params[1], q)
                else:
                    q = line
                    lamb = 2 * params[0] * t
                    for _ in range(noise_factor):
                        circ.rz(lamb, q)
                        circ.rz(-lamb, q)
                    circ.rz(lamb, q)
            else:
                # print(line)
                (q0, q1) = link[line - n]
                theta = 2 * params[0] * t
                if ins == 0:
                    for _ in range(noise_factor):
                        circ.rzx(theta, q0, q1)
                        circ.rzx(-theta, q0, q1)
                    circ.rzx(theta, q0, q1)
                elif ins == 1:
                    for _ in range(noise_factor):
                        circ.rxx(theta, q0, q1)
                        circ.rxx(-theta, q0, q1)
                    circ.rxx(theta, q0, q1)
                elif ins == 2:
                    for _ in range(noise_factor):
                        circ.ryy(theta, q0, q1)
                        circ.ryy(-theta, q0, q1)
                    circ.ryy(theta, q0, q1)
                else:
                    for _ in range(noise_factor):
                        circ.rzz(theta, q0, q1)
                        circ.rzz(-theta, q0, q1)
                    circ.rzz(theta, q0, q1)
    if with_measure:
        circ.measure_all()
    return circ


def transpile_to_circ(backend, alignment, sol_gvars, boxes, edges):
    circ = clean_as(boxes, edges, backend)
    return circ


def transpile(backend, alignment, sol_gvars, boxes, edges, use_pulse=True, with_measure=True,noise_factor=0):
    if use_pulse:
        pm = get_pm(backend)
        # return clean_as(boxes, edges, backend)
        return pm.run(clean_as(boxes, edges, backend, with_measure,noise_factor))
    else:
        return clean_as(boxes, edges, backend, with_measure)
