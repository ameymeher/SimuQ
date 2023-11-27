from qiskit_ibm_provider import IBMProvider
with open('../ibm_API_key','r') as file:
    token = file.readline()

provider = IBMProvider(token=token, instance="ibm-q-ncsu/nc-state/quantum-compiler")

n_4_t_1 = ["cna13m6m2pvg008sktx0",
"cna13nyyzmv0008w8t10",
"cna13q6m2pvg008sktxg",
"cna13rfj5tjg0080xg9g",
"cna13sz1m2c0008wypqg",
"cna13v7yzmv0008w8t1g"]

results = []
for job_id in n_4_t_1:
    results.append(provider.retrieve_job(job_id).result().get_counts())



