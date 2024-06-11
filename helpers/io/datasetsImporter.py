# -*- coding: utf-8 -*-

"""

Created on Mon May 18 14:58:49 2015



@author: mbouhier

"""

import csv
import os

import h5py
import numpy as np
import scipy.io
from psd_tools import PSDImage
from scipy import misc

from helpers import mc_logging
from openWireData import openWireDataHDF5

try:
    import spc
except ImportError as e:
    print("Can't import spc loader")


try:
    from nexusformat.nexus import *
except ImportError as e:
    print("Can't load nexus module")


from PyQt5 import uic
from helpers.bigDataTools import getChunkSize
from dataAccess.mcWorkFile import McWorkFile




class DatasetsImporter(object):

    #=========================================================================#
    #                    Methodes de base                                     #
    #=========================================================================#

    def __init__(self, workFile = None, callbackProgress = None, callbackDone = None):

        #self.output_type = 'numpy' #PAS UTILISE, TODEL?

        if workFile: self.workFile = workFile

        if callbackProgress: self.callbackProgress = callbackProgress
        if callbackDone:     self.callbackDone     = callbackDone

        self.images_extentions = ["jpeg", "jpg", "tif", "tif", "tiff", "bmp"]


    def updateProgress(self, progress):

        if self.callbackProgress: self.callbackProgress(progress)



    def notifyLoadingDone(self):
        if self.callbackDone: self.callbackDone()


    # def setOutputType(self,output_type):
    #
    #     self.output_type = output_type



    def useWorkFile(self):
        return hasattr(self, "workFile")

        

    #TODO: mettre plutot un args

    def loadFile(self, path, qt_mode = False):#, convertToHdf5 = False):

        if not path:
            print("no path specified")
            return 0

        if len(path) == 1: path = path[0]


        if self.hasMultipleFile(path):

            path = [os.path.normpath(f) for f in path]

            #TODO: on verifie que toutes les extensions sont identiques

            ext = path[0].split(".")[-1] #extension du fichier
            ext = ext.lower()         #on met tout en minuscule

            mc_logging.info('Loading %s files...' % (len(path),))

            

        else:

            path = os.path.normpath(path)
            
            ext = path.split(".")[-1] #extension du fichier
            ext = ext.lower()         #on met tout en minuscule

            mc_logging.info('Loading file..."%s"' % (path,))

        mc_logging.debug("extension: %s" % (ext,))
        #mc_logging.debug("output type: '%s'" % (self.output_type))

        if ext == "h5":
            return self.loadHDF5(path)

        elif ext.lower() in self.images_extentions:
            return self.loadImage(path)

        elif ext == "mat":
            return self.loadMat(path)

        elif ext == "psd":
            return self.loadPSD(path)

        elif ext == "raw":
            return self.loadRawMEB(path)

        elif ext == "wxd" or ext == "wdf":
            return self.loadRamanWire(path, qt_mode)

        elif ext =="csv":
            return self.loadMebCSVs(path)

        elif ext =="spc":
            return self.loadSPC(path)

        elif ext =="txt":
            return self.loadTxt(path)

        elif ext =="nxs":
            return self.loadNxs(path)


    def  loadNxs(self, path, experiment_name = ''):

        # if self.useWorkFile():
        #
        #     print("creating xys in work file, dtype=i8", end=' ')
        #
        #     xys = self.workFile.getTempHolder((w*h,2), dtype = 'i8')

        nxs_file = nxload(path)

        exp_nb = len(nxs_file.keys())

        if not exp_nb:
            mc_logging.error("No experiment detected in NXS file")
            return [], [], [], {}


        else:

            if exp_nb == 1:
                exp_name = list(nxs_file.keys())[0]

            #=========================================================================
            #  GUI de selection de l'experience
            #=========================================================================
            else:
                # =====================================================================
                #  List available experiments
                # =====================================================================
                mc_logging.info("%d experiment detected:" % (exp_nb,))

                for exp_name in nxs_file.keys():
                    mc_logging.info("   -%s" % (exp_name,))


                d = uic.loadUi("assets\\ui_files\datasetsImporter_nxs.ui")
                d.setWindowTitle("Please give some informations...")

                ok = d.exec_()

                if ok:
                    exp_name = str(d.experiments_list.currentItem().text())

                else:
                    mc_logging.warning("NXS loading aborted by user")
                    return [],[],[],{}


            # =========================================================================
            #  Chargement au format Slicy
            # =========================================================================
            w, h, channels_nb = nxs_file[exp_name].scan_data.channel00.shape

            xpos = nxs_file[exp_name].scan_data.xpos #relecture deplacement horizontaux (x)
            ypos = nxs_file[exp_name].scan_data.zpos #relecture deplacement verticaux (y)
            deadtime00 = nxs_file[exp_name].scan_data.deadtime00 #deadtime00
            clock_period = nxs_file[exp_name].scan_data.clock_period #Temps d'acquisition
            incident_flux = nxs_file[exp_name].scan_data.counter1 #Io flux inciedent
            raw_spectrums = nxs_file[exp_name].scan_data.channel00


            mc_logging.info('experiment "%s" selected:' % (exp_name,))
            mc_logging.info('   - width: %d' % (w,))
            mc_logging.info('   - height: %d' % (h,))
            mc_logging.info('   - channels: %d' % (channels_nb,))
            #mc_logging.info('   - deadtime: %f' % (deadtime00,))
            # mc_logging.info('   - acquisition delay: %f' % (clock_period,))
            # mc_logging.info('   - incident flux: %f' % (incident_flux,))


            new_shape =(w*h,channels_nb)
            mc_logging.info("unfolding matrix...", raw_spectrums.shape)
            spectrums = raw_spectrums.reshape(new_shape)

            mc_logging.info("done unfolding", spectrums.shape)
            W = range(channels_nb) #TODO, y a t'il acces aux energies des canaux?

            #xpos = np.array(xpos.reshape((w*h,1)))
            #ypos = np.array(ypos.reshape((w*h,1)))

            #xys = np.dstack((xpos,ypos))
            #xys = xys.round()

            #print(np.unique(xys[:,0]))
            #print(len(np.unique(xys[:, 0])))
            indexes_layout = "top_left_to_bottom_column_by_column"
            args = {"indexes_layout": indexes_layout} # TODO, "x_unit": "nm", "y_unit": y_unit}

            spectrums = spectrums.tolist()

            #TODO: On pourrais prendre les vrais xys, mais il y a un decallage qui fait trop de valeurs uniques
            #pour des points cencés êtr sur une meme ligne
            xys = [(i%h,i//h) for i in range(w*h)]

            return spectrums, W, xys, args


    def loadPSD(self,path):

        mc_logging.info("Loading psd file...")

        if self.hasMultipleFile(path): 

            mc_logging.warning("Multiple File loading unsupported for this type of files")

            return

        psd       = PSDImage.load(path)
        layerList = []
        W         = []
        datas     = []

        default_representations = []


        #Correspondance entre type de format et nbr de canaux

        format_lut = {"1" : 1,
                      "L" : 1,
                      "P" : 1,
                      "RGB" : 3,
                      "RGBA" : 4,
                      "CMYK" : 4,
                      "YCbCr" : 3,
                      "I" : 1,
                      "F" : 1
                      }

                      

        for layer in psd.layers:

            print("processing layer", layer.name)

            if layer.visible:

                layerList.append(layer.name)
                layerPIL = layer.as_PIL()

                w, h = layerPIL.size
                nb_channel = format_lut[layerPIL.mode]

                #try:

                layer_image = None

                layer_image = np.asarray(layerPIL)

                print("type(layer_image):", type(layer_image))

#                except MemoryError:
#                    print "workfile"
#                    layer_image = self.workFile.getTempHolder((h, w, nb_channel))
#                    print "chunks"
#                    fillByChunk(layerPIL.getdata(), layer_image)
#                    print "done"

                #===============Creation des images par default===============

                #TODO: envoyer layer_image tel quel et reussir a l'afficher dans cluster

                #default_image = layer_image[:,:,0] + layer_image[:,:,1] + layer_image[:,:,2]

                

                default_image = layer_image

                default_representations.append({"image" : default_image, "name" : layer.name})

                

                print("for layer '%s'" % (layer.name), "(w,h):", w,h, "nb_channel:", nb_channel)
                print("dring",np.asarray(layerPIL))


                if nb_channel == 1:

                    datas.append(layer_image.reshape((w*h, 1)))
                    #spectrums = spectrums.reshape((w*h,1))
                    W.append(layer.name)

                    

                elif nb_channel == 3: 

                    W.append("%s (R)" % (layer.name,))
                    W.append("%s (G)" % (layer.name,))
                    W.append("%s (B)" % (layer.name,))
                    datas.append(layer_image[...,0].reshape((w*h)))
                    datas.append(layer_image[...,1].reshape((w*h)))
                    datas.append(layer_image[...,2].reshape((w*h)))

                elif nb_channel == 4: #rgba TODO, ou CMYK etc...

                    W.append("%s (R)" % (layer.name,))
                    W.append("%s (G)" % (layer.name,))
                    W.append("%s (B)" % (layer.name,))
                    W.append("%s (A)" % (layer.name,))
                    datas.append(layer_image[...,0].reshape((w*h)))
                    datas.append(layer_image[...,1].reshape((w*h)))
                    datas.append(layer_image[...,2].reshape((w*h)))
                    datas.append(layer_image[...,3].reshape((w*h)))


        print("layers list (visible only):")

        for name in layerList:

            print('     -%s' % name)


        spectrums = np.array(datas).transpose()
        W         = np.array(W)
        xys       = np.array([(i//w, i%w) for i in range(w*h)])

        indexes_layout = "left_to_right_line_by_line"

        args = {"indexes_layout":indexes_layout,"default_representations":default_representations,"x_unit":"Layer","y_unit":"u.a."}


        #TODO: creer une representation par default

        return spectrums, W, xys, args


    def loadImage(self,path):

        print("loading image...")

        image = misc.imread(path, flatten = False)

        print("shape", image.shape)
        print("dtype", image.dtype)

        shape = image.shape

        if len(shape) == 2:

            print("gray image")
            h, w = image.shape
            spectrums = image.reshape((w*h,1))
            W = np.array(["G"])

        elif len(shape) == 3:

            h, w, nb_channels = shape
            spectrums = image.reshape((w*h,nb_channels))

            if shape[2] == 3: #rgb

                print("rgb image")
                W = np.array(["R","G","B"]) 

            if shape[2] == 4: #rgba

                print("rgba image")
                W = np.array(["R","G","B","A"])

        #======================================================================
        #                        on creer des xys
        #=======================================================================

        if self.useWorkFile():

            print("creating xys in work file, dtype=i8", end=' ')

            xys = self.workFile.getTempHolder((w*h,2), dtype = 'i8')

            #TODO: pas optimiser! faire des chunks

            chunk = getChunkSize(xys.shape)

            

            for i in range(0, w*h, chunk):

                i_min = i
                i_max = min(w*h, i + chunk)          

                print(".", end=' ')

                xys[i_min:i_max,:] = np.array([(j/w,j%w) for j in range(i_min,i_max)])

        else:
            xys = [(i/w,i%w) for i in range(w*h)]

            

        indexes_layout = "left_to_right_line_by_line"

        args = {"indexes_layout":indexes_layout,
                "default_representations":[{"image":image,"name":"raw"}],
                "x_unit":"Channel","y_unit":"u.a."}

        return spectrums, W, xys, args


    def loadHDF5(self, path):

        print("opening hdf5 file...")

        if self.hasMultipleFile(path):
            mc_logging.warning("Multiple File loading unsupported for this type of file")
            return


        fhdf5 = h5py.File(path, "r")


        if 'dataset' not in fhdf5:
            mess = "Missing 'dataset' key, loading aborted"
            mc_logging.info(mess)
            raise(IOError(mess))

        #On renvoie direct les ref hdf5
        spectrums = fhdf5['dataset']['X']
        W         = fhdf5['dataset']['W']
        xys       = fhdf5['dataset']['xys']

        #unitées, retrocompatibilité
        x_unit = fhdf5['dataset'].get("x_unit","u.a")
        y_unit = fhdf5['dataset'].get("y_unit","u.a")

        #conversion bytes en str, compatibilité python 2->3
        if(hasattr(W[0],'dtype') and np.issubdtype(W[0].dtype, np.bytes_)):
            W = [c.decode('utf8') for c in W]

        #=======================Test sur l'ordre des données===========
        #TODO: capitaliler ce bout de code redondant avec wxd...

        indexes_layout = ''
        detect_indexes_layout_type = False

        if len(xys)>1 and detect_indexes_layout_type:

            #TODO verifier ça
            if xys[0,0] == xys[1,0]:

                print("'point' type dataset detected")

                indexes_layout = "left_to_right_line_by_line"

            #cas des carto streamline y0!=y1
            elif  xys[0,1] == xys[1,1]:

                print("'streamline' type dataset detected", end=' ')

                if xys[0,0] > xys[1,0]: #y decroissants
                    indexes_layout = "bottom_left_to_top_column_by_column"
                    print("(bottom to top)")

                else:
                    indexes_layout = "top_left_to_bottom_column_by_column"
                    print("(top to bottom)")

            else:
                print("none condition")


        else:
            print("indexes_layout irrelevant, only one position in dataset")


        print("hdf5 opening done!")

        args = {"indexes_layout" : indexes_layout, "x_unit" : x_unit, "y_unit" : y_unit}


        return spectrums, W, xys, args


    def loadRawMEB_AncienFormatTODEL(self,path):
        #==============================================================
        # On ouvre le fichier .raw et le .rpl correspondant pour determiner w,h,x
        # autre type que little indian non implementés pour le moment
        #==============================================================

        if self.hasMultipleFile(path): 

            mc_logging.warning("Multiple File loaing unsupported for this type of files")

            return



        #TODO: lecture des rpl ancienne + nouvelle version à prendre en charge!!

        try:                

            f_raw = open(path,'r')

        except Exception as e:

            msg = "Error while opening raw data"

            print(msg,e)

            raise IOError

            

        try:

            #TODO, probleme si nom de fichier ou dossier contenant ".raw"

            #(mais bon, quelle idée aussi)

            f_rpl   = open(path.replace(".raw",".rpl"),'r')

            content = f_rpl.read()

            lines   = content.split("\n")

            w, h, x, rb = 0,0,0,0   

            offset = 0

            

            #==================================================================
            ###-200 si 20keV à 2048 canaux et -100 si 10keV à 2048 canaux
            #TODO: choix en interactif
            #Ces 2 parametres se lisent pas le logiciel Oxford
            #==================================================================
            Ecanal = 5
            offsetE = -100  

            #==================================================================
            # nouveau format de rpl commencent et finissent par des parentheses
            #sinon rangement standard          param value
            #==================================================================

            new_format = (lines[0]=='(')

            print("MLX format:",new_format)

            for line in lines:

                if new_format:

                    s = line.split("::")

                    if len(s)==2:

                        s = s[1].split(")")[0]

                        param, value = s.split()

                        if   'WIDTH'     in param :    w  = int(value)
                        elif 'HEIGHT'    in param :    h  = int(value)
                        elif 'DEPTH'     in param :    x  = int(value)
                        elif 'DATA-LENGTH' in param :  dataL  = int(value)
                        elif 'OFFSET' in param :       offset  = int(value)
                        elif 'RECORD-BY' in param :    rb = value.split(":")[-1]

                else:

                    s = line.split()

                    if len(s)==2:

                        param,value = s

                        if   'width'     in param :   w  = int(value)
                        elif 'height'    in param :   h  = int(value)
                        elif 'depth'     in param :   x  = int(value)
                        elif 'data-length' in param : dataL = int(value)
                        elif 'record-by' in param : rb = value

                     

            mc_logging.debug("Parameters from rpl:")
            mc_logging.debug("    - Width:       %d" % (w,))
            mc_logging.debug("    - Height:      %d" % (h,))
            mc_logging.debug("    - Depth:       %d" % (x,))
            mc_logging.debug("    - Record-by:   %s" % (rb,))

                

        except Exception as e:

            msg = "Can't open rpl file"
            print(msg)
            print(e)
            raise IOError

        #10 eV par canal

        Ecanal = 10

        print("creating array from file (%d,%d,%d)..." % (w,h,x), end=' ')

#                MAX_SIZE_IN_MEMORY = 100663296

#                if w*h*x > MAX_SIZE_IN_MEMORY: count =

#                    print "size > max memory, splitting data"

        

        a = np.fromfile(f_raw,dtype=np.dtype('<i4'),count=-1)

        print("done")

        f_raw.close()
        f_rpl.close()

        

        b = np.reshape(a,[w*h,x])

        

        print("original shape: ",a.shape)

        print("final shape:    ",b.shape)

        

        W = np.linspace(0,x*Ecanal,x)

        

        #=====binning matrice=======
        n = 4
        b = np.sum([b[:,i::n] for i in range(n)], 0)
        W = np.linspace(0, x*Ecanal, x/n)
        #==== fin test ================

        

        #TODO: indexes_layout = ??

        indexes_layout = ""

        spectrums = b

        xys = np.array([(i/w,i%w) for i in range(w*h)])

        

        args = {"indexes_layout":indexes_layout,"x_unit":"eV","y_unit":"count"}



        return spectrums,W,xys,args

        
    def loadRawMEB(self, path, Ecanal = 5, offsetE = -100, spectral_binning_if_not_hdf5=4):
        #==============================================================
        # On ouvre le fichier .raw et le .rpl correspondant pour determiner w,h,x
        # autre type que little indian non implementés pour le moment
        # Ecanal et offsetE sont obtenus dans le logiciel Oxford
        #Si on utilise pas de workFile, spectral_binning_if_not_hdf5 somme des canaux spectraux
        # ==================================================================
        if self.hasMultipleFile(path):
            mc_logging.warning("Multiple File loading unsupported for this type of files")
            return



        #TODO: lecture des rpl ancienne + nouvelle version à prendre en charge!!
        try:
            f_raw = open(path,'rb')

        except Exception as e:
            msg = "Error while opening raw data"
            print(msg,e)
            raise IOError 

        try:
            #TODO, probleme si nom de fichier ou dossier contenant ".raw"
            #(mais bon, quelle idée aussi)

            f_rpl   = open(path.replace(".raw",".rpl"),'r')
            content = f_rpl.read()
            lines   = content.split("\n")

            w, h, dataL, rb = 0, 0, 0, 0   

            offset = 0

            #==================================================================
            # nouveau format de rpl commencent et finissent par des parentheses
            #sinon rangement standard          param value
            #==================================================================
            new_format = (lines[0]=='(')

            print("MLX format:",new_format)

            for line in lines:

                if new_format:

                    s = line.split("::")

                    if len(s)==2:

                        s = s[1].split(")")[0]

                        param, value = s.split()

                        if   'WIDTH'     in param :    w  = int(value)
                        elif 'HEIGHT'    in param :    h  = int(value)
                        elif 'DEPTH'     in param :    sp_len  = int(value)
                        elif 'DATA-LENGTH' in param :  dataL  = int(value)
                        elif 'OFFSET' in param :       offset  = int(value)
                        elif 'RECORD-BY' in param :    rb = value.split(":")[-1]

                else:

                    s = line.split()

                    if len(s)==2:

                        param,value = s

                        if   'width'     in param :   w  = int(value)
                        elif 'height'    in param :   h  = int(value)
                        elif 'depth'     in param :   sp_len  = int(value)
                        elif 'data-length' in param : dataL = int(value)
                        elif 'record-by' in param : rb = value

            mc_logging.debug("Parameters from rpl:")
            mc_logging.debug("    - Width:       %d" % (w,))
            mc_logging.debug("    - Height:      %d" % (h,))
            mc_logging.debug("    - Depth:       %d" % (sp_len,))
            mc_logging.debug("    - Record-by:   %s" % (rb,))

        except Exception as e:

            msg = "Can't open rpl file"

            print(msg)
            print(e)
            raise IOError

        print("creating array from file (%d,%d,%d)..." % (w,h,sp_len), end=' ')

        byte_by_sp    = dataL * sp_len
        byte_by_image = w*h*dataL

        W = np.linspace(0 + offsetE, dataL*Ecanal, sp_len)
        
        #======================================================================
        # Lecture iterative avec transfert dans un fichier hdf5
        #======================================================================
        if self.useWorkFile():
            xys       = self.workFile.getTempHolder((w*h,2))
            spectrums = self.workFile.getTempHolder((w*h,sp_len))

            counter = 0
            
            bytes_to_read = byte_by_image


            while(1):
                #la prochaine lecture avec read se fera automatiquement bytes_to_read plus loin
                data = f_raw.read(bytes_to_read)

                #si plus rien a lire, on sort de la boucle
                if not data:
                    print("EOF reached")
                    break

                if counter >= sp_len:
                    print("counter>sp_len")
                    break

                #on converti ce block de données binaire en matrices numpy
                data = np.frombuffer(data, dtype='<i4', count = w*h, offset = offset)


                #pourcentage d'avancement
                if (counter % 20)==0:

                    progress = 1.0*counter/sp_len
                    print('%.2f%%' % (progress*100,))

                spectrums[:, counter] = data #canal numero N
                
                counter = counter + 1

            print('%d channels processed!' % (counter,))



        #======================================================================
        # Lecture standard avec copie dans un nparray: soumis à MemoryError
        #======================================================================
        else:
            a = np.fromfile(f_raw, dtype = np.dtype('<i4'), count=-1)

            print("done")

            f_raw.close()
            f_rpl.close()

            b = np.reshape(a,[w*h,sp_len])

            print("original shape: ",a.shape)
            print("final shape:    ",b.shape)


            #=====binning matrice=======
            n = spectral_binning_if_not_hdf5 #POUR reduire la taille en memoire
            b = np.sum([b[:,i::n] for i in range(n)], 0)
            W = np.linspace(0 + offsetE, dataL*Ecanal,sp_len/n)

            #==== fin test ================
            spectrums = b

        

        #======================================================================
        # Index layout en fonction du record by
        #======================================================================

        if rb =='image': indexes_layout = 'left_to_right_line_by_line'
        else:            indexes_layout = ''


        xys = np.array([(i//w,i%w) for i in range(w*h)])
        args = {"indexes_layout" : indexes_layout, "x_unit" : "eV", "y_unit" : "count"}


        return spectrums, W, xys, args


    def loadMebCSVs(self, path, delimiter = ','):
        """
        Load .csv
        """
        default_representations = []

        if self.hasMultipleFile(path): 

            print("multiple csv loading")
            paths = path
            filenames_wt_ext = [p.split("\\")[-1].split('.')[0] for p in paths]
            spectral_dim = len(filenames_wt_ext)

        else:
            print("single csv loading")
            filenames_wt_ext = path.split("\\")[-1].split('.')[0]
            paths = [path]
            spectral_dim = 1


        #======================================================================
        #         Calcul de la taille de l'image
        #   on suppose que tout les fichier on la meme taille....
        #======================================================================
        w, h = 0, 0

        with open(paths[0], 'r') as csvfile:

            csvreader = csv.reader(csvfile, delimiter = delimiter, quotechar = '|')

            first_row = True

            for row in csvreader:
                h += 1

                if first_row:
                    first_row = False

                    for v in row:
                        try:# si on a bien une valeur
                            v = float(v)
                            w += 1

                        except ValueError as k:
                            continue

        #======================================================================
        #                 Conteneur pour les spectres
        #======================================================================
        spectrums = np.zeros((w*h,spectral_dim))
        i_column_max = 0

        #======================================================================
        #                 On itere sur tout les fichiers
        #======================================================================
        is_first_file = True

        for i_file, path in enumerate(paths):

            with open(path, 'r') as csvfile:

                csvreader = csv.reader(csvfile, delimiter = delimiter, quotechar = '|')

                is_first_line = True        

                
                for i_row, row in enumerate(csvreader):

                    for i_column, value in enumerate(row):

                        #les 0,00 deviennent 0.00
                        #e = e.replace(",",".") 

                        try:
                            value = float(value)

                        except ValueError as k: #si e est ==""
                            continue

                        sp_idx = i_row*w + i_column
                        spectrums[sp_idx][i_file] = value


                default_image = np.array([sp[i_file] for sp in spectrums]).reshape(h,w)

                default_representations.append({"image":default_image,"name":filenames_wt_ext[i_file]})

                is_first_file = False

                

        xys = np.array([(i//w,i%w) for i in range(w*h)])

        indexes_layout = "left_to_right_line_by_line"

        W = filenames_wt_ext


        print('w,h',w,h)
        print('len(xys),len(spectrums)',len(xys),len(spectrums))
        print('W,spectrums.shape',W,spectrums.shape)    


        args = {"indexes_layout":indexes_layout, "default_representations":default_representations, "x_unit":"eV","y_unit":"count"}


        return spectrums, W, xys, args 


    def loadMat(self,path):

        mat = scipy.io.loadmat(path)

        W, spectrums, xys = mat["W"],mat["X"],mat["xys"] 

#        # ===Fix temporaire
#        #mat_type = 0 pour lire les fichiers pm et mat_type=1 pour les fichiers de soustraction de pente ====
#
#        print type(spectrums)
#        print len(spectrums)
#        print spectrums.shape
#        mat_type = 1
#
#        #Fix temporaire pour le probleme d'incompatibilité des types de .mat (traitement fluo vs datasetComposer)
#        if(mat_type==0):
#            W = np.array(W)
#        else:
#            W = np.array(W[0])
#
#        indexes_layout = ""
#
#        if(mat_type==0):
#            if len(W.shape) == 2: W = W[:,0]
#            else:                 W = W[:]

        print("type(W):",type(W))
        print("len(W):",len(W))
        print("W.shape",W.shape)


        #W rangé sous forme de ligne ou de collonne
        if len(W.shape) == 1:
            #type(nb_channels,) ou en list
            W = np.array(W)

        else:
            #type (nb_channels, 1)
            if W.shape[0] > W.shape[1]:
                W = W[:,0]

            #type (1, nb_channels)
            else:
                W = W[0,:]

                



        args = {"indexes_layout":"","x_unit":"cm-1","y_unit":"count"}

                

        return spectrums,W,xys,args


    def loadRamanWire(self, path, qt_mode = True):
        """
        Load Renishaw Wire .wxd and wxf
        """
        spectrums, W, xys = openWireDataHDF5(path, qt_mode)


        W = np.array(W)


        indexes_layout = ''


        if len(spectrums) > 1: #cas de toutes les carto, mais au cas ou...

            #cas des pointés raman x0=x1

            indexes_layout = ''

            if xys[0,0] == xys[1,0]:
                print("'point' type wire file detected")
                indexes_layout = "left_to_right_line_by_line"

            #cas des carto streamline y0!=y1

            elif  xys[0,1] == xys[1,1]:

                print("'streamline' type wire detected", end=' ')

                if xys[0,0] > xys[1,0]: #y decroissants
                    indexes_layout = "bottom_left_to_top_column_by_column"
                    print("(bottom to top)");

                else:
                    indexes_layout = "top_left_to_bottom_column_by_column"
                    print("(top to bottom)")

            else:
                print("none condition")


        args = {"indexes_layout" : indexes_layout, "x_unit" : "cm-1", "y_unit" : "count"}


        return spectrums, W, xys, args


    def loadSPC(self, path):
        """
        Load SPC "galactic" file
        """

        f = spc.File(path)

        sp_number = len(f.sub)
        

        #====on demande quelques infos pour continuer  GUI=====================

        d = uic.loadUi("assets\\ui_files\datasetsImporter_spc.ui")

        d.setWindowTitle("Please give some informations...")



        ok = d.exec_()

        # ============= On recupere les donnees de la gui =======================

        if ok:      

            width  = int(d.points_nb_x.text())
            height = int(d.points_nb_y.text())

            try:

                #test de coherence
                assert sp_number == width*height

            except AssertionError:

                mess = "width (%d) height (%d) combinaison doesn't match with spectrums number (%d)" % (width,height,sp_number)

                print(mess)

                #QtGui.QMessageBox.warning("Error",mess )

                raise IOError

                

            #on creer les données

            W = np.array(f.x)

            

            xys = np.array([[i/width, i%width] for i in range(sp_number)])

            spectrums = np.zeros((sp_number,len(W)))

            spectrums = [f.sub[i].y for i in range(sp_number)]

            spectrums = np.array(spectrums)

            

            indexes_layout = "left_to_right_line_by_line"#"top_left_to_bottom_column_by_column"

            args = {"indexes_layout":indexes_layout,"x_unit":f.xlabel,"y_unit":f.ylabel}

            

            return spectrums,W,xys,args

            

        else:

            return [],[],[],{}


    def loadTxt(self, path, delimiter=','):     

        """

        TODO, charger un  spectre sous forme de txt nb_onde, intensity

        """

        

        if 1:

#            xys            = np.array([(i/w,i%w) for i in range(w*h)])

#            indexes_layout = "left_to_right_line_by_line"

#            W              = filenames_wt_ext

#            spectrums      = np.array(spectrums)

#            return spectrums,W,xys,args

            pass

        

        else:

            return [],[],[],{}

    
    def hasMultipleFile(self,path):

        if type(path) is str:

            return False 

            

        elif type(path) is list: 

            return True

            

            

def testLoading():

    """
    Test d'import des differents types de fichiers
    """
    workFile = McWorkFile("bin\\temp")

    importer = DatasetsImporter(workFile)

    cdir = os.path.dirname(os.path.abspath(__file__)) + "\\"


    #==========================================================================
    # Chargement fichier Synchrotron NXS
    #==========================================================================
    print(10 * "=", "Testing NXS loading", 10 * "=")
    test_file = cdir + 'bin\\unit_test_datasets\\test_04901_trou.nxs'
    spectrums, W, xys, indexes_layout = importer.loadFile(test_file)

    assert(len(spectrums)==18471)
    assert(len(W)==4096)
    assert(len(xys)==len(spectrums))
    print("NXS file testing done!")
    return
    #==========================================================================
    # Chargement images .jpg, .jpeg
    #==========================================================================

    print(10*"=","Testing Image loading",10*"=")

    test_file = cdir + 'bin\\unit_test_datasets\\Penguins.jpg'

    spectrums,W,xys,indexes_layout = importer.loadFile(test_file)

    print("Image .jpg file testing done!")    



    #==========================================================================
    # Chargement images multilayer psd
    #==========================================================================

    print(10*"=","Testing PSD multilayer image loading",10*"=")

    test_file = cdir + 'bin\\unit_test_datasets\\phases_mixees_LD.psd'

    spectrums,W,xys,indexes_layout = importer.loadFile(test_file)

    print("Multilayer .psd file testing done!")    



    #==========================================================================
    # Chargement fichier hdf5 (formatage specifique au programme) .h5
    #==========================================================================

    print(10*"=","Testing h5 file loading",10*"=")

    test_file = cdir + 'bin\\unit_test_datasets\\Donnees_EDS_256x192_(40_channels_from_1800_to_2200eV)_256x192.h5'

    spectrums,W,xys,indexes_layout = importer.loadFile(test_file)

    print("HDF5 file testing done!")   

    

    #==========================================================================
    # Chargement fichier hdf5 (formatage specifique au programme) .h5
    #==========================================================================

    print(10*"=","Testing mat file loading",10*"=")

    test_file = cdir + 'bin\\unit_test_datasets\\z15G_20x20_p05_10s_points_200900_nc.mat'

    spectrums,W,xys,indexes_layout = importer.loadFile(test_file)

    print("Matlab file testing done!")   



    #==========================================================================
    # Chargement fichier .csv du MEB
    #==========================================================================

    print(10*"=","Testing csv file loading",10*"=")

    test_file = cdir + 'bin\\unit_test_datasets\\fichiers_csv\\Fe % masse.csv'

    spectrums,W,xys,indexes_layout = importer.loadFile(test_file)

    print("CSV file testing done!")   



    #==========================================================================
    # Chargement liste de fichier .csv du MEB
    #==========================================================================

    print(10*"=","Testing csv file list loading",10*"=")

    f_names = ["Fe % masse.csv","Ca % masse.csv","K % masse.csv","Cl % masse.csv","S % masse.csv","P % masse.csv","Si % masse.csv","Al % masse.csv","Mg % masse.csv","Na % masse.csv","O % masse.csv"]

    test_files = [cdir + 'bin\\unit_test_datasets\\fichiers_csv\\' + f_name for f_name in f_names]

    spectrums,W,xys,indexes_layout = importer.loadFile(test_files)

    print("CSV file list testing done!")   


    #==========================================================================
    # Chargement fichier .raw ancien format
    #==========================================================================

    print(10*"=","Testing raw file loading",10*"=")

    test_file = cdir + 'bin\\unit_test_datasets\\xl9.raw'

    spectrums,W,xys,indexes_layout = importer.loadFile(test_file)

    print("Raw file (old format) testing done!")    


    #==========================================================================
    # Chargement fichier .raw nouveau format
    #==========================================================================

    print(10*"=","Testing raw file loading",10*"=")

    test_file = cdir + 'bin\\unit_test_datasets\\Donnees_EDS_512x384.raw'

    spectrums,W,xys,indexes_layout = importer.loadFile(test_file)

    print("Raw file (format MLX) testing done!")    


    #==========================================================================
    # Chargement fichier spc
    #==========================================================================

    print(10*"=","Testing SPC file loading",10*"=")

    test_file = cdir + 'bin\\unit_test_datasets\\area3.spc'

    spectrums,W,xys,indexes_layout = importer.loadFile(test_file)

    print("SPC  file testing done!")   


    #==========================================================================
    # Chargement jeux de données Renishaw Wire .wxd
    #==========================================================================

    print(10*"=","Testing Renishaw .wxd file loading",10*"=")

    #TODO: faire des jdd de test de petite taille    

    test_file_points     = cdir + 'bin\\unit_test_datasets\\W-01-points1.wxd'

    test_file_streamline = cdir + 'bin\\unit_test_datasets\\GL10-3B-Streamline-40s.wxd'

    test_file_1_spectrum = cdir + 'bin\\unit_test_datasets\\11.wxd'

    spectrums, W, xys, indexes_layout = importer.loadFile(test_file_points)

#    assert(len(spectrums) == 2376)
#    assert(len(xys) == 2376)
#    assert(len(W) == 1015)
#    assert(len(indexes_layout) == 'bottom_left_to_top_column_by_column')
#    spectrums,W,xys,indexes_layout = importer.loadFile(test_file_streamline)
#    print len(W)
#    assert(len(spectrums) == 2145)
#    assert(len(xys) == 2145)
#    assert(len(W) == 2144)
#    assert(len(indexes_layout) == 'bottom_left_to_top_column_by_column')

    spectrums, W, xys, indexes_layout = importer.loadFile(test_file_1_spectrum)

    print("Renishaw .wxd file testing done!")

    

if __name__ == "__main__":

    testLoading()



    

    

    
