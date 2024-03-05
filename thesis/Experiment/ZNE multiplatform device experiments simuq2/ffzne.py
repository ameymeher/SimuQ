import pickle

with open('interleaved_rb_results_28_01_2024_20_57_18.pickle', 'rb') as handle:
    interleaved_rb_results = pickle.load(handle)
    print(interleaved_rb_results)