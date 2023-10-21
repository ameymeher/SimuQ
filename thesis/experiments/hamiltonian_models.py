from simuq.qsystem import QSystem
from simuq.environment import qubit

def Ising(N, T, J, h):
    qs = QSystem()
    q = [qubit(qs) for _ in range(N)]
    H = 0
    for j in range(N):
        for k in range(N):
            H += J[j, k] * q[j].Z * q[k].Z
    for j in range(N):
        H += h[j] * q[j].X
    qs.add_evolution(H, T)
    return qs
