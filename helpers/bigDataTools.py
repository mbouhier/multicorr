# -*- coding: utf-8 -*-
"""
Created on Tue Aug 09 13:25:22 2016

@author: mbouhier
"""
import dask.array as da
import numpy as np

from helpers import mc_logging


def fillByChunk(input_array_like, output_array_like, progress_callback = None):
    """
    Methode remplissant un array block par block pour ne pas saturer la memoire
    callbackProgress: Methode prenant en argument un nombre de 0 à 100
    ce nombre represente l'avancée du traitement
    TODO, faire plutot de 0 à 1.
    callbackDone: Methode appelée à la fin du traitement
    """

    output_dtype  = getattr(output_array_like, 'dtype', None)
    
    if type(input_array_like) is list:
        
        nb_lines = len(input_array_like)
        
        if type(input_array_like[0]) is list: nb_cols = len(input_array_like[0])
        else:                                 nb_cols = 1
  
        input_shape = (nb_lines, nb_cols)
        
    else:                              
        input_shape = input_array_like.shape
    
    chunk_size = getChunkSize(input_shape)
    
    for i in range(0,input_shape[0], chunk_size):

       if progress_callback: progress_callback(100.0 * i / input_shape[0])
       
       i_min = i
       i_max = min(i + chunk_size, input_shape[0])
       
       input_chunk = input_array_like[i_min:i_max]
       
       if output_dtype:
           output_array_like[i_min:i_max] = np.array(input_chunk, dtype = output_dtype)
           #output_array_like[i_min:i_max] = input_chunk.astype(output_dtype, copy = False)
       else:
           output_array_like[i_min:i_max] = input_chunk
       
    if progress_callback:
        progress_callback(100)
        progress_callback(-1)

def processConsecutiveFloat64InMemoryCalculation():
    """
    Test automatique determinant la taille maximal avant un "MemoryError"
    """
    max_consecutive_float64_in_memory = 100000000
    increment = 10000
    size_with_no_error = 0
    
    for float64_nb in range(max_consecutive_float64_in_memory,1,-increment):
        try:
            m = np.ones((float64_nb,1), dtype = np.float64)
            size_with_no_error = float64_nb
            break
        except MemoryError as e:
#            print "memory error for:",float64_nb
#            print e
            continue
        except ValueError as e:
#            print "value error for:",float64_nb
#            print e
            continue
        
    print("inside processConsecutiveFloat64InMemoryCalculation:", size_with_no_error)

    #on detruit explicitement la reference pour liberer l'espace memoire, utile??
    m = None

    #on se garde une marge
    return int(size_with_no_error*0.10)
    
def getChunkSize(dataShape):
        """
        On recalcule une taille de "chunk", shape de datas maximal pour ne pas
        avoir de memory error
        done le nombre max de lignes exploitables, on se basse pour ça sur le nombre
        de float consecutifs possible en memoire
        """
        print("inside getChunkSize")
        
        if len(dataShape) < 2: dataShape = [dataShape[0], 1]

        chunk_size = processConsecutiveFloat64InMemoryCalculation()/dataShape[1]
        
        chunk_size = min(int(chunk_size), dataShape[0])


        percent_of_ds = 100.0*chunk_size/dataShape[0]
        
        mess = "Chunk_size: %d  " % (chunk_size,)
            
        if percent_of_ds > 0.1:
            mess = mess + "(%.2f%% of dataset size)" % (percent_of_ds)
            
        else:
            mess = mess +"(<0.01% of dataset size)"
        
        print(mess)
        return(chunk_size)



def std(datas, axis=0):
    """
    Methode de calcul du std
    """
    try:
        return np.std(datas, axis)
    except MemoryError as e:
        print("Can't process std with standard method (MemoryError), trying with HDF5")
        print(e)
        return stdHDF5(datas, axis)

def stdHDF5(datas, axis = 0):

    print("processing std of data (HDF5 version, axis %d)..." % (axis,))

    chunk_size = getChunkSize(datas.shape)

    #print("datas shape in _meanHDF5:", datas.shape)

    if len(datas.shape) >= 2:
        chunk_dim_2 = datas.shape[1]

    else:
        chunk_dim_2 = 1

    dset = da.from_array(datas, chunks = (chunk_size, chunk_dim_2))

    std = dset.std(axis = axis).compute()

    print("std of data processing done")

    return std


def normalizeHDF5(datas, workFile, method =''):

    """
    Methode de normalisation utilisant et renvoyant des datasets.py hdf5
    Ici normalisation spectre à spectre ou collonne apres colonne pour eviter les
    memory error
    TODO: verifier les performances
    """

    mc_logging.debug("Processing normalization (hdf5version) with method '%s'..." % method)

    print("datas.dtype", datas.dtype)

    sp_number = datas.shape[0]

    w_size = datas.shape[1]

    datas_dset = getDaskDatasetFromArray(datas)

    datas_normalized = workFile.getTempHolder(datas.shape)

    # ==========calcul du spectrum max en fonction de la methode===========

    if method in ["max", "sum"]:
        spectrums_maxs_shape = (sp_number, 1)

    elif method in ["columns_max", "columns_sum"]:
        spectrums_maxs_shape = (1, w_size)

    # spectrums_maxs = self.mcData.workFile.getTempHolder(spectrums_maxs_shape)
    # spectrums_maxs = np.ones(spectrums_maxs_shape)

    if method == "max":
        spectrums_maxs = datas_dset.max(axis = 1).compute()

    elif method == "sum":
        spectrums_maxs = datas_dset.sum(axis = 1).compute()

    elif method == "columns_max":
        spectrums_maxs = datas_dset.max(axis = 0).compute()

    elif method == "columns_sum":
        spectrums_maxs = datas_dset.sum(axis = 0).compute()

    elif method == "columns_std":
        spectrums_maxs = datas_dset.std(axis = 0).compute()

    elif method == "inertia":
        spectrums_maxs = da.square(datas_dset).sum(axis = 0).compute()

    else:
        raise NotImplementedError

    # ======================================================================
    print("Sp max")
    print(spectrums_maxs.shape)
    print(spectrums_maxs)

    chunk_size = getChunkSize(datas.shape)

    if method in ["max", "sum"]:

        for i in range(0, sp_number, chunk_size):
            i_min, i_max = i, min(i + chunk_size, sp_number)

            datas_normalized[i_min:i_max] = 1.0 * datas[i_min:i_max] / spectrums_maxs[i_min:i_max, None]

    elif method in ["columns_max", "columns_sum", "columns_std", "inertia"]:

        # spectrums_maxs==0 a un bug, d'ou le elementwise

        for i in range(w_size):
            if spectrums_maxs[i] == 0: spectrums_maxs[i] = np.nan

        print("spectrums_maxs:", spectrums_maxs)

        for i in range(0, sp_number, chunk_size):
            i_min, i_max = i, min(i + chunk_size, sp_number)

            chunk = 1.0 * datas[i_min:i_max] / spectrums_maxs

            chunk[np.isnan(chunk)] = 0  # Attention, on met a zero les nan, a discuter

            datas_normalized[i_min:i_max] = chunk

    # print "datas_normalized[0]",datas_normalized[0]

    mc_logging.debug("normalize done")

    return datas_normalized

def normalizeNumpy(datas, method =''):

    """

    Methode de normalisation vectorisé version numpy, plus rapide (a tester)

    mais limitée en taille de datas

    """

    print("Processing normalization with method '%s'..." % method, end = ' ')

    if method == "max":
        spectrums_maxs = 1.0 * np.max(datas, axis = 1)

    elif method == "sum":
        spectrums_maxs = 1.0 * np.sum(datas, axis = 1)

    else:
        raise NotImplementedError

    spectrums_maxs[spectrums_maxs == 0] = np.nan

    datas_normalized = 1.0 * datas / spectrums_maxs[:, np.newaxis]

    # on converti les valeurs nan en nombre pour eviter les probleme avec la PCA notament

    datas_normalized = np.nan_to_num(datas_normalized)

    mc_logging.debug("normalize done")

    return datas_normalized


def getMean(datas, axis = 0):
    """
    Methode de calcul du mean
    """
    try:
        return meanNumpy(datas, axis)
    except MemoryError as e:
        print("Can't process mean with standard method (MemoryError), trying with HDF5")
        print(e)
        return meanHDF5(datas, axis)


def meanNumpy(datas, axis = 0):

    print("processing mean data (Numpy version)...")

    mean = np.mean(datas, axis)

    print("mean data processing done")

    return mean

def meanHDF5(datas, axis = 0):

    print("processing mean data (HDF5 version, axis %d)..." % (axis,))

    chunk_size = getChunkSize(datas.shape)

    #print("datas shape in _meanHDF5:", datas.shape)

    if len(datas.shape) >= 2:
        chunk_dim_2 = datas.shape[1]
    else:
        chunk_dim_2 = 1

    dset = da.from_array(datas, chunks = (chunk_size, chunk_dim_2))

    mean = dset.mean(axis = axis).compute()

    print("mean data processing done")

    return mean



def getDaskDatasetFromArray(datas, chunks = None):

    """

    return a Dask dataset object based on an hdf5 dataset

    """

    chunk_size = getChunkSize(datas.shape)

    if not chunks: chunks = (chunk_size, datas.shape[1])

    return da.from_array(datas, chunks = chunks)

def storeDaskDatasetToHdf5Dataset(dask_dataset, hdf5_dataset):

    """

    Write by chunk dask dataset to hdf5_dataset

    """

    print(("storing dask dataset to hdf5 dataset",))

    assert (dask_dataset.shape == hdf5_dataset.shape)

    chunk_size = getChunkSize(dask_dataset.shape)

    sp_number = dask_dataset.shape[0]

    for i in range(0, sp_number, chunk_size):
        i_min = i

        i_max = min(i + chunk_size, sp_number)

        hdf5_dataset[i_min:i_max] = dask_dataset[i_min:i_max]

    print("done")