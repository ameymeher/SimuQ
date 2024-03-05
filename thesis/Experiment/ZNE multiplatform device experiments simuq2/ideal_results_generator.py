#Getting the ideal results
from hamiltonian_models import Ising
from simuq.qutip import QuTiPProvider
import numpy as np
import pickle

def get_ideal_result(N,T):
    #Ising chain model creation
    h = np.array([1 for j in range(N)])
    J_chain = np.zeros((N, N))
    for j in range(N - 1):
        J_chain[j, j + 1] = 1

    J_cycle = np.copy(J_chain)
    J_cycle[0, N - 1] = 1
    Ising_chain = Ising(N, T, J_chain, h)

    #Classical simulation
    qtpp = QuTiPProvider()
    qtpp.compile(Ising_chain)
    qtpp.run()

    return qtpp.results()

ideal_results = {}

for N in [4,6,8,10]:
    for T in [0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0,1.5,2.0]:
        ideal_results[(N,T)] = get_ideal_result(N,T)

print(len(ideal_results))

with open("results/ideal_results.pkl", "wb") as f:
    pickle.dump(ideal_results, f)