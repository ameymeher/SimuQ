import yaml
import logging.config
import logging

#Setup logger
with open('logging.yaml', encoding="utf8") as ly:
    loggingDict = yaml.safe_load(ly)
logging.config.dictConfig(loggingDict)
logger = logging.getLogger("reliability_utility_ibm")


def get_interleaved_fidelity(qc,parameters):

    calibrations = qc.calibrations
    print(type(calibrations['rx']))


def get_gate_fidelities(qc,parameters):

    """
    Return a JSON with the below format:
    {
        "gate_fidelities" : {
            "rx" : {
                "qubit" : qubit_number,
                "score" : score
            },
            "rzx" : {
                "qubit1" : qubit_1_number,
                "qubit2" : qubit_2_number,
                "score" : score
            }
        }
    }
    """
    logger.info("circuit {} system {}".format(qc,parameters['system']))
    return {
        "gate_fidelities" : {
            "rx" : {
                "qubit" : 0,
                "score" : 0
            },
            "rzx" : {
                "qubit1" : 0,
                "qubit2" : 1,
                "score" : 0
            }
        }
    }

def get_circuit_reliability(qc,fidelities):

    """
    Returns a score between 0 and 1
    """

    return 0




#Testing
#Temp code to get the pickled circuit
import pickle
with open("circuit.pickle", 'rb') as handle:
    qc = pickle.load(handle)


get_interleaved_fidelity(qc,None)