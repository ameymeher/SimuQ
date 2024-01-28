import multiprocessing

parameters = range(100)  # Adjust as needed

for N in range(3,25):
    for system in ["ibmq_kolkata", "ibmq_mumbai", "ibm_cairo", "ibm_auckland", "ibm_hanoi"]:
        for T in range(1,6):
            for optimization_level in range(0,4):
                
            

num_processes = multiprocessing.cpu_count() 
pool = multiprocessing.Pool(processes=num_processes)
results = pool.starmap(your_function, parameters)

# Close the pool to release resources
pool.close()
pool.join()

# Process the results (if needed)
for result in results:
    print(result)