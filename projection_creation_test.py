import h5py
import numpy as np
import matplotlib.pyplot as pl


filename = "C://Users//mbouhier//Desktop//clustering_git_pyqt5_python3_converted2//projection_test_streamw02.h5"

ds_size = 2145
W_size = 1015
vectors_number = 25

W = np.linspace(0, 2*np.pi, W_size)


with h5py.File(filename, 'w') as f:

    #=================================================================
    # Creation conteneurs
    #=================================================================
    f.create_dataset("vectors", (vectors_number, W_size))
    f.create_dataset("vectors_names", (vectors_number,1), dtype = h5py.special_dtype(vlen=str))
    f.create_dataset("values", (ds_size, vectors_number))

    #=================================================================
    # Remplissage
    #=================================================================
    for i in range(vectors_number):
        f["vectors"][i,:] = np.sin(W+3*np.random.random(1)) + 0.2*np.random.random_sample(len(W))
        pl.plot(W, f["vectors"][i])

        f["vectors_names"][i,0] = "base_vector_%d" % (i,)


    f["values"][:,:] = np.random.random((ds_size,vectors_number))

    pl.show()


    # f["values"][:]
