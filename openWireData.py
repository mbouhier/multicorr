# -*- coding: utf-8 -*-

"""
 OpenWireData2  Import spectral data from a Renishaw WXD file (using ActiveX server)


 Syntax:
    [X, W, yx, path, Map] = OpenWireData2(path)


 Input: either no inputs, in which case uigetfile is called or input path name, in
 which case it is not.  Note that the ActiveX server does not see the Matlab path,
 so the full (not relative) path of the WXD file to read must be specified.


 Output:

 X    - spectra (with spectrum in each row)
 W    - Wavenumber information
 yx   - spatial information or numbering of spectra
 path - path of wxd file (if needed)
 Map  - ActiveX object used to import WiRE data


 If the Map output is used, then be sure to free the resources associated with the
 ActiveX server (see the M-code for an example).

"""

"""
Pour une carto streamline:
    yx[:,0] = x ordre croissant
    yx[:,1] = x ordre croissant
"""



"""
Modif le 15/09/14, decallage de +1 dans la borne max des boucles for et demarrage des indices a 0 dans les
assignation. Difference entre code matlab et python
Modif le 17/09/14 Les données de certains spectres sont rangées par ordre decroissant, on les remet donc dans le bon sens
"""
try:
    import win32com.client
except ImportError:
    print("Import error for win32com.client")

from numpy import *

import os


import numpy as np
import time


#from enthought.pyface.api import ProgressDialog

#from PyQt5.QtWidgets import ProgressDialog

from PyQt5.QtCore import QRect
from PyQt5.QtWidgets import QProgressDialog
#from pyface.api import GUI


import h5py
import os
from helpers import mc_logging

from renishawWiRE import WDFReader

#pour retrocompatibilité, revoie du numpy array

from wdf import Wdf


def openWireData2(path, qt_mode = False):

    X, W, yx = openWireDataHDF5(path, qt_mode)
    return (np.array(X),W,yx)


def _delTmpFiles(directory, prefix):

    """
    Suppression de tous les fichiers temporaires qui n'aurait pas été supprimés
    TODO: Voir utilisation import tempfile en remplacement de ces methodes
          combinées avec atexit, voir all_features.py de guidata
    """

    tmpFiles = [f for f in os.listdir(directory) if
                os.path.isfile(os.path.join(directory, f)) and prefix in f]



    if tmpFiles:
        mc_logging.debug("previous temp files detected")

        

    for tmpFile in tmpFiles:

        path = directory + ('//') + tmpFile

        try:
            os.remove(path)
            mc_logging.debug("workfiles deleted")

        except Exception as e:
            mc_logging.debug("can't delete tmpFiles")

                

def openWireDataHDF5(path, qt_mode = False):

    try:
        
        wdf = Wdf()
        wdf.open(path)

        area = wdf.map_area

        x_count = area.count.x 
        y_count = area.count.y

        x_step = area.step.x
        y_step = area.step.y

        x_start = area.start.x
        y_start = area.start.y

        nb_spectra = wdf.hdr.ncollected

        print("dataset contains ", nb_spectra, " spectra")
        print("xstep, ystep = ", x_step, y_step)
        print("xcount, ycount = ", x_count, y_count)

        #=============== Liste des coordonnées =============================
        y_values = np.arange(y_start, y_start + y_count * y_step, y_step)
        x_values = np.arange(x_start, x_start + x_count * x_step, x_step)

        y_grid, x_grid = np.meshgrid(y_values, x_values, indexing='xy')
        yx = np.stack((y_grid, x_grid), axis=-1).reshape(-1, 2)
        #===================================================================

        W = wdf.xlist()
        X = np.array([wdf.spectrum(i) for i in range(nb_spectra)])

        print("len(yx):",len(yx))
        print("X.shape:",X.shape)
        print("yx.shape:",yx.shape)
        
        wdf.close()

    except Exception as e:
        print("Error: Can't load '%s'"%(path,))
        raise(e)
    

    return (X,W,yx)



def openWireDataHDF5_with_py_wdf_reader(path, qt_mode = False):
    #wdf file opening based on https://github.com/alchem0x2A/py-wdf-reader/tree/master

    SINGLE_SPECTRUM = 1
    DEPTH_SERIES = 2
    GRID_MAPPING = 3

    try:
        print('Opening "%s"' % path)
        reader = WDFReader(path)

        #Adding white ligh image
        ##################img = PIL.Image.open(reader.img)
        ##################img1 = img.crop(box=reader.img_cropbox)

        print("WDFReader.measurement_type:",reader.measurement_type)


        #==============================================
        if(reader.measurement_type == SINGLE_SPECTRUM):
            W = reader.xdata
            X = reader.spectra
            yx = [(0,0)]

            return ([X],W,yx)
        #==============================================
        if(reader.measurement_type == DEPTH_SERIES):
            raise(Exception("Depth series unsuported yet"))


        #==============================================
        if(reader.measurement_type == GRID_MAPPING):

            W = reader.xdata
            X = reader.spectra


            print(W.shape)
            print(X.shape)
            print(reader.ypos.shape)
            print(reader.xpos.shape)

            X = X.reshape(X.shape[0]*X.shape[1],X.shape[2])
            print(X.shape)
            
            yx = np.array([[reader.ypos[i],reader.xpos[i]] for i in range(len(reader.ypos))])
            
            print(yx.shape)
            
            return (X,W,yx)


    except Exception as e:
        print("Error: Can't load '%s'"%(path,))
        raise(e)


    return (X_list,W,yx)



    


def openWireDataHDF5_old(path, qt_mode = False):

    """
    basé sur openWireData2 mais travail avec et retourne un dataset HDF5
    """

    Map = win32com.client.Dispatch("Renishaw.WiREMemFileCom")


    try:
        t1 = time.time()
        print('Opening "%s"' % path)
        Map.OpenFile(path,0)

    except:
        print("Error: Can't load '%s'"%(path,))

        try:
            Map.CloseFile()
            Map.ReleaseStorage()
            Map.release()

        except:
            pass

        return False

        

    try:
        nCol = Map.NumberOfCollectedDataSets()

    except:
        nCol = 1

    #print "spectrum count:",nCol

    try:
        nOffset = Map.CollectedDataSetsFirstIndex()

    except:
        nOffset = 0

    #print "nOffset:",nOffset

    try:
        nOrigin = Map.GetElement('','dataOriginCount')

    except:
        nOrigin = 0

    #print "nOrigin:",nOrigin

    nLists = Map.NumberOfDataLists('DataSet'+str(nOffset))

    #print "nLists:",nLists

    

    #W est une liste contenant l'ensemble des longueurs d'ondes 

    W = Map.GetData('DataSet' + str(nOffset),'DataList'+str(nLists-2),0,-1);


    #==========================================================================
    # On supprime d'eventuels precedents fichiers temp encore sur le disque
    #==========================================================================
    _delTmpFiles(os.path.dirname(path),"tempWireData")

    #==========================================================================
    # On creer le fichier temporaire
    #==========================================================================

    temp_hdf5_file = "tempWireData%d.h5" % (np.random.randint(0, 1000000))


    with h5py.File(temp_hdf5_file) as h5wf: 

         datasetShape = (nCol-nOffset,len(W))

         h5wf.create_dataset("X", shape = datasetShape, dtype = 'f')

         X  = h5wf["X"]

         yx = np.array([(0,0)]) # sinon probleme var quand monospectre


         if nOrigin==2 or nOrigin==3:

             yx    = np.zeros((nCol-nOffset,2))

             #Unité de l'axe ex: X/micrometre
             axis1 = Map.GetElement('','dataOriginName0')

             #print axis1

             

             if axis1=='X':
                 x = 0
                 y = 1

             else:
                 x = 1
                 y = 0

             DataOriginListNotExist = 0

             try:

                 #contient les longueurs d'ondes
                 yx[:,0] = Map.GetData('','DataOriginList'+str(y),0,-1)

                 #contient les nombres de coups
                 yx[:,1] = Map.GetData('','DataOriginList'+str(x),0,-1)

                 if nOrigin==3:
                    yx[:,2] = Map.GetData('','DataOriginList2',0,-1) 

                    

             except Exception as e:
                  DataOriginListNotExist = 1


             #============== Chargement des données ============================

             #progress barr optionnel

             if qt_mode:

                 try:
                     #d_size = QRect(1000,1000,5000,1000)
                     print("inside qtdialog mode")

                     progressbar = QProgressDialog("Loading Wire data...",
                                                   "Cancel",
                                                    0,
                                                    nCol-1-nOffset)

                 except Exception as e:
                     print("Exception:",e)
                     d_size = None

                     progressbar = QProgressDialog(title = "Loading data...",
                                                   message = "Loading %d spectrums:" % (nCol-1-nOffset,),
                                                   max = nCol - 1 - nOffset,
                                                   show_time = True,
                                                   dialog_size = d_size,
                                                   can_cancel = False)
                  

                 print("Loading in progress, please wait...")             

                 progressbar.show()

 

             for n in range(nOffset,nCol):

                 if qt_mode:
                     if (progressbar.wasCanceled()):
                         mess = "Loading aborted by user"
                         print(mess)
                         raise(UserWarning,mess)

                 X[n-nOffset,:] = Map.GetData('DataSet' + str(n),'DataList' + str(nLists-1),0,-1)


                 if DataOriginListNotExist:

                     yx[n-nOffset,1] = Map.GetElement('DataSet' + str(n),'DataOriginValue'+str(y))
                     yx[n-nOffset,2] = Map.GetElement('DataSet' + str(n),'DataOriginValue'+str(x))


                 #Mise a jour de la barre de progression
                 if n%85 == 0: #85 arbitraire
                     if qt_mode: progressbar.setValue(n)
                     else:       print(".", end = ' ')


             try: progressbar.close()
             except Exception as e: pass

             t2 = time.time()

             print("Done!",datasetShape[0],"spectrums succesfully loaded in %.2f" % (t2-t1,),"s")

             

         else:
             X  = np.zeros((nCol-nOffset, len(W)), dtype='float32')
             yx = np.array([(0,0)])

             for n in range(nOffset,nCol):
                 #print("n:",n)
                 X[n-nOffset,:] = Map.GetData('DataSet' + str(n), 'DataList' + str(nLists-1),0,-1)


         print("hdf5 temp file to list conversion...", end = ' ')

         X_list = []

         for i in range(datasetShape[0]):

             if i%1000==0: print(".", end = ' ')
             X_list.append(X[i,:])

         print("done")


    #Les données de certains spectres sont rangées par ordre croissant, d'autres non
    #on remet à l'endroit si tel est le cas.



    if W[0] > W[-1]:

        W = W[::-1]

        for i in range(len(X)):
            X[i]  = X[i][::-1]



    try:
        os.remove(temp_hdf5_file)

    except Exception as e:
        print("can't remove temporary hdf5 file")


    return (X_list,W,yx)





if __name__=="__main__":   

    #openWireData2("C:\Users\mbouhier\Desktop\Nouveau dossier\Raw datas\SDM042_07_map1b.wxd")
    #openWireData2("C:\Users\mbouhier\Desktop\SDM042_04_map2_x20_2.55s_50%.wxd")
    #X,W,xy = openWireData2("C:\Users\mbouhier\Desktop\Bg-F-01_B_map3\Bg-F-01_B_map3_no-cosm.wxd")

    c_dir = os.path.dirname(__file__)

    print("======= Test version classique =======")
    print("======sans affichage ProgressDialog=====")
    
    filename = c_dir + "\\bin\\unit_test_datasets\\W-01-points1.wxd"

    X,W,xy = openWireData2(filename, qt_mode = False)

    
    print("type(X):",type(X))
    print("len(W):",len(W))
    print("shape(X):",len(X))

    print("========avec affichage ProgressDialog=======")
    
    X,W,xy = openWireData2(filename)
    
    print("type(X):",type(X))
    print("len(W):",len(W))
    print("shape(X):",len(X))
    

    print("======= Test version HDF5 avec prise en charge wdf =======")

    filename = c_dir + "\\bin\\spectra_files\\mapping.wxd"
    
    X,W,xy = openWireDataHDF5(filename)

    print("type(X):",type(X))
    print("len(W):",len(W))
    print("shape(X):",len(X))



    

