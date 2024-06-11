# -*- coding: utf-8 -*-
"""
Created on Tue Aug 09 09:43:30 2016

@author: mbouhier
"""

import atexit
import datetime
import os
import random

import dask.array as da
import h5py

from helpers import mc_logging


#PAS UTILISE#
class McProjectFile(object):
    
    def __init__(self, path):
        self._createProjectFile(path)
        
    def _createProjectFile(self, hdf5workDirectory):
        """
        Fichier du projet, celui qui contient tous les jdd chargés etc, tous
        les objets dataset.
        Remplace self.datasets.py anciennement dictionnaire contenant toutes les données
        programme en memoire vive
        """
        path = hdf5workDirectory + "//projectFile_%s.h5" % (datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S"))
        # print("path before:",path)
        # path =  os.path.abspath(path)
        # print("path after:",path)


        with h5py.File(path, "w") as f:
            f.create_group("datasets.py")
            f.create_group("relationships")
            mc_logging.debug("project file created")
        self._projectFilePath = path
        
        
    def getFile(self):
        f = h5py.File(self._projectFilePath, "r+")
        self._projectFileRef = f
        atexit.register(f.close) #fermeture "quoi qu'il arrive" à la sortie (?)
        return f
        
    def close(self):
        if hasattr(self,"_projectFileRef"): self._projectFileRef.close()
        mc_logging.debug("project file closed")
        return True


    def delete(self):
        self.close()
        try:
            print("_projectFilePath", self._projectFilePath)
            os.remove(self._projectFilePath)
            mc_logging.debug("project file deleted")
        except Exception as e:
            mc_logging.debug("can't delete project file")


            
class McWorkFile(object):
    
    #=========================================================================#
    #                    Methodes de base                                     #
    #=========================================================================#
    def __init__(self, path):
        self._createWorkFile(path)
        
        
    #=========================================================================#
    #                Accesseurs                                               #
    #=========================================================================#
    def getTempHolder(self, datasetShape, datasetName = '', dtype = 'f'):
        """
        return a reference on a "dataset" named datasetname of size datashapeShape
        of hdf5 workFile
        """
        h5wf = self.getFile()
        if not datasetName:
            datasetName = "tempHolder%d" % (random.randint(0, 1000000))
            
        #on supprime d'abord tout dataset ayant le meme nom
        if datasetName in h5wf: del h5wf[datasetName]
        #on creer un array dans le hdf5    
        h5wf.create_dataset(datasetName, shape = datasetShape, dtype = dtype)#compression="gzip", )
        
        return h5wf[datasetName]

    def getDaskDataset(self, datasetShape, datasetName = '', chunks = None):
        """
        return a Dask dataset object based on an hdf5 dataset contained on a
        temporary workFile
        
        from https://media.readthedocs.org/pdf/dask/latest/dask.pdf p13
        A good choice of chunks follows the following rules:
            1. A chunk should be small enough to fit comfortably in memory. We’ll have many chunks in memory at once.
            2. A chunk must be large enough so that computations on that chunk take significantly longer than the 1ms overhead
            per task that dask scheduling incurs. A task should take longer than 100ms.
            3. Chunks should align with the computation that you want to do. For example if you plan to frequently slice along
            a particular dimension then it’s more efficient if your chunks are aligned so that you have to touch fewer chunks.
            If you want to add two arrays then its convenient if those arrays have matching chunks patterns.
        """
        chunk_size = self.getChunkSize(datasetShape) # a determiner empiriquement en debut de programme
        if not chunks: chunks = (chunk_size, datasetShape[1])
            
        hdf5_dataset = self.getTempHolderFromWorkFile(datasetShape, datasetName)
        print("hdf5_dataset.shape:",hdf5_dataset.shape)
        return da.from_array(hdf5_dataset, chunks = chunks)
        
        
    def getFile(self):

        wf_ref = getattr(self, "_workFileRef",None)
        if not wf_ref:
            f = h5py.File(self._workFilePath, "r+")
            self._workFileRef = f
        else:
            f = self._workFileRef 
            
        return f


    #=========================================================================#
    #                                                                         #
    #=========================================================================#
    def _createWorkFile(self, hdf5workDirectory):
        """
        Fichier avec lequel seront effectués les calculs temporaire
        Le fichier est remis à zero à chaque lancement
        """
        self._delTmpFiles(hdf5workDirectory)
        path = hdf5workDirectory + "//tmpWorkFile__%s.h5" % (datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S"))
        with h5py.File(path, "w"):
            mc_logging.debug("work file created")
        self._workFilePath = path
        
        
    def _delTmpFiles(self, hdf5workDirectory):
        """
        Suppression de tous les fichiers temporaires qui n'aurait pas été supprimés
        TODO: Voir utilisation import tempfile en remplacement de ces methodes
              combinées avec atexit, voir all_features.py de guidata
        """
        tmpFiles = [f for f in os.listdir(hdf5workDirectory) if
                    os.path.isfile(os.path.join(hdf5workDirectory, f)) and "tmpWorkFile" in f]

        for tmpFile in tmpFiles:
            path = hdf5workDirectory + ('//') + tmpFile
            try:
                os.remove(path)
                mc_logging.debug("workfiles deleted")
            except Exception as e:
                mc_logging.debug("can't delete tmpFiles:")
                mc_logging.debug(e)
                
    def close(self):
        try:
            if self._workFileRef: self._workFileRef.close()
            mc_logging.debug("work file closed")
            return True

        except Exception as e:
            mc_logging.debug("can't close work file")
            return False

    def delete(self):
        self.close()
        self._delTmpFiles("bin//temp")
        
    #=========================================================================#
    #                                                                         #
    #=========================================================================#
        