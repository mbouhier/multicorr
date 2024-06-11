# -*- coding: utf-8 -*-

"""
Created on Wed Jan 29 15:34:18 2014

@author: mbouhier

"""

import numpy as np
from pprint import pprint


from PyQt5.QtWidgets import (QWidget, QProgressBar, QFileDialog, QDialog,
                             QMessageBox)


from PyQt5 import QtGui, QtWidgets
from PyQt5 import QtWidgets, uic


#import matplotlib.pyplot as pl
import time


from plotpy.items import RGBImageItem, ImageItem
from plotpy.builder import make
from plotpy.plot import PlotDialog, PlotOptions
from plotpy.tools import SelectPointTool
from plotpy.styles import ImageParam


from PyQt5.QtCore import *


from numpy.random import randn


from threading import Thread, Timer


import scipy.io
from functools import partial


import cv2
import copy


import logging
#v0.2: les images acceptées n'etaient que RGB, ajout du support des float32 1 cannal



class DatasetsMatcher(QtWidgets.QMainWindow):

    

    def __init__(self):

            super().__init__()

            self.setWindowTitle("DatasetMatcher v0.2")

            #=====================================

            p = uic.loadUi("assets\\ui_files\datasetsMatcherMulti.ui")

            self.panel = p
            self.setCentralWidget(p)
            self.init_vars()
            self.init_gui()



    def init_vars(self):

        #======================================================================
        #     Initialisation des variables
        #======================================================================

        self.match_points = dict()

        self.datasets = {"A" : dict(), "B" : dict()}
        

        #self.pointsCount    = 1

        self.check_mode     = False #visualisation de la correspondance A B
        self.overlap_mode   = False

        self.originalPointList = dict()

        self.useRGBImages = True


    def init_gui(self):

        p = self.panel

        #======================================================================
        #     Creation des widgets Plot et image
        #======================================================================

        #=====================Image A==========================================

        imgDialogA = PlotDialog(edit     = False,
                                 toolbar  = False,
                                 title = "Dataset A",
                                 options  = PlotOptions(show_contrast=False,type='image')) 

        imagePlotA = imgDialogA.get_plot()

        #-------------image par default----------------------------------------

        #imgA  = make.rgbimage(filename=defA, xdata=xdata_A, ydata=ydata_A)

        if self.useRGBImages:
            imgA  = RGBImageItem(np.zeros((5,5,3)))

        else:
            imgA  = ImageItem(np.zeros((5,5,3)))

        imagePlotA.add_item(imgA)

#        #------------points par defaut------------------------------------------
#        self.originalPointList["A"] = {"top left":    [xdata_A[0],ydata_A[0]],
#                                       "top right":   [xdata_A[1],ydata_A[0]],
#                                       "bottom right":[xdata_A[1],ydata_A[1]],
#                                       "bottom left": [xdata_A[0],ydata_A[1]]}
#                                       


        #=====================Image B==========================================

        imgDialogB = PlotDialog(edit     = False,
                                 toolbar  = False,
                                 title = "Dataset B",
                                 options  = PlotOptions(show_contrast=False,type='image'))

        imagePlotB = imgDialogB.get_plot()

        #-------------image par default----------------

        #imgB  = make.rgbimage(filename=defB, xdata=xdata_B, ydata=ydata_B)

        if self.useRGBImages:
            imgB  = RGBImageItem(np.zeros((5,5,3)))

        else:
            imgB  = ImageItem(np.zeros((5,5,3)))


        imagePlotB.add_item(imgB) 

        #------------points par defaut------------------------------------------

#        self.originalPointList["B"] = {"top left":    [xdata_B[0],ydata_B[0]],
#                                       "top right":   [xdata_B[1],ydata_B[0]],
#                                       "bottom right":[xdata_B[1],ydata_B[1]],
#                                       "bottom left": [xdata_B[0],ydata_B[1]]}

#                                       

        #=====================Image B projeté sur A============================

        #-------------image par default en RGBA de la taille de imgB-----------

        #imgData = np.zeros((ydata_B[1]-ydata_B[0],xdata_B[1]-xdata_B[0],4))
        imgData = np.zeros((5,5,4))


        #Utilisation d'un "imageParam" nescessaire à l'activation du mode alpha

        imageParams = ImageParam()
        imageParams.alpha_mask = True


        if self.useRGBImages:
            overlapImg  = RGBImageItem(imgData, imageParams)

        else:
            overlapImg  = ImageItem(imgData, imageParams)

        #on ajoute à l'imagePlot et on cache par defaut
        imagePlotA.add_item(overlapImg)
        imagePlotA.set_item_visible(overlapImg, False)

        

        #---------on charge les données originales de l'image B ---------------

        #------- pour une utilisation par drawOverlapimage()-------------------

        #originalImageB  = cv2.imread(defB)

        #originalImageB  = cv2.cvtColor(originalImageB, cv2.COLOR_BGR2RGBA)    

        originalImageB  = np.zeros((5,5,4))



        #==============Ajout de tools===========================================

        #dans quiwst attaché sur le dialog, dans plotpy, attaché sur le plot....

        # selectToolA = imgDialogA.add_tool(SelectPointTool,
        #                                   title = "Selection",
        #                                   on_active_item = False,
        #                                   mode = "create",
        #                                   end_callback = self.setPoint)

        # selectToolA.activate()

        # selectToolB = imgDialogB.add_tool(SelectPointTool,
        #                                   title = "Selection",
        #                                   on_active_item = False,
        #                                   mode = "create",
        #                                   end_callback = self.setPoint)


        # selectToolB.activate()
        selectToolA = imgDialogA.manager.add_tool(SelectPointTool,
                                          title = "Selection",
                                          on_active_item = False,
                                          mode = "create",
                                          end_callback = self.setPoint)

        selectToolA.activate()

        selectToolB = imgDialogB.manager.add_tool(SelectPointTool,
                                          title = "Selection",
                                          on_active_item = False,
                                          mode = "create",
                                          end_callback = self.setPoint)


        selectToolB.activate()
        

        #=====================Points sur image A===============================

        marker_size = 10

        curveA = make.curve([], [],
                            linestyle="NoPen",
                            marker = "o",
                            markersize = marker_size,
                            markerfacecolor = "red",
                            markeredgecolor = "black",
                            title = "selected point(s)")  

        imagePlotA.add_item(curveA)

        #=====================Points sur image B===============================

        curveB = make.curve([], [],
                            linestyle="NoPen",
                            marker = "o",
                            markersize = marker_size,
                            markerfacecolor = "red",
                            markeredgecolor = "black",
                            title = "selected point(s)")  

        imagePlotB.add_item(curveB)

        #====================Point de corespondance de B dans A ===============

        selection_curveA = make.curve([], [],
                                      linestyle="NoPen",
                                      marker = "o",
                                      markersize = marker_size,
                                      markerfacecolor = "green",
                                      markeredgecolor = "green",
                                      title = "selected point")

        imagePlotA.add_item(selection_curveA)                             

        #====================Point de corespondance de A dans B ===============

        selection_curveB = make.curve([],[],
                                      linestyle="NoPen",
                                      marker = "o",
                                      markersize = marker_size,
                                      markerfacecolor = "green",
                                      markeredgecolor = "green",
                                      title = "selected point")

        imagePlotB.add_item(selection_curveB)   

        p.mainLayout.addWidget(imgDialogA, 0, 0)
        p.mainLayout.addWidget(imgDialogB, 0, 1)


        #on enregistre tout en "interne"
        self.datasets["A"]  = {"name":"dsA",
                               "curvePlot":curveA,
                               "imageItem":imgA,
                               "imagePlot":imagePlotA,
                               "selectPointTool":selectToolA,
                               "pointsList":dict(),
                               "originalPointsList":dict(),
                               "selectionPoint":[],
                               "selectionPointCurvePlot":selection_curveA,
                               "overlapImageItem":overlapImg}

        self.datasets["B"]  = {"name":"dsB",
                               "curvePlot":curveB,
                               "imageItem":imgB,
                               "imagePlot":imagePlotB,
                               "selectPointTool":selectToolB,
                               "pointsList":dict(),
                               "originalPointsList":dict(),
                               "selectionPoint":[],
                               "selectionPointCurvePlot":selection_curveB,
                               "rawImage":originalImageB}


        #on trace les coins à leurs positions par defaut:
        #self.initPoints()

         #=======================================================================
        #     Configuration signaux/slots
        #=======================================================================
        self.makeConnections()

        

    def makeConnections(self):

        p = self.panel

        #p.button_addPoint.clicked.connect(self.addPoint)

        #p.button_delPoint.clicked.connect(self.delPoint)

        p.button_reinit.clicked.connect(self.initPoints)
        p.button_check.clicked.connect(self.setCheckMode)
        p.combo_dsA.currentIndexChanged.connect(partial(self.setDataset,"A"))
        p.combo_dsB.currentIndexChanged.connect(partial(self.setDataset,"B"))
        p.button_overlap.clicked.connect(self.setOverlapMode)
        p.slider_alpha.valueChanged.connect(self.drawOverlapImage)
        p.combo_dsA_repr.currentIndexChanged.connect(partial(self.setDatasetRepr,"A"))
        p.combo_dsB_repr.currentIndexChanged.connect(partial(self.setDatasetRepr,"B"))
        p.button_validate_matching.clicked.connect(self.validate_matching)
        p.button_ok.clicked.connect(self.validate_matching)
        p.pushButton_export.clicked.connect(self.exportMatrixs)
        p.button_test.clicked.connect(self.testPoints)

        

    def setDataset(self,dsId):
        """
        Methode appelée lorseque l'element selectionné dans les comboBoxs
        dsA ou dsB change. Avec dsId = A ou B
        """

        p  = self.panel

        di = self.datasets_infos

        print("Dataset",dsId,"changed")

        imagePlot = self.datasets[dsId]["imagePlot"]
        imgItem   = self.datasets[dsId]["imageItem"]

        #=====================================================================
        # Mise à jour de la liste des representations dispobibles pour ce ds
        #======================================================================          

        if dsId == "A":
            combo_repr = p.combo_dsA_repr
            combo_ds   = p.combo_dsA

        if dsId == "B":
            combo_repr = p.combo_dsB_repr
            combo_ds   = p.combo_dsB

        ds_name   = str(combo_ds.currentText())
        repr_name = str(combo_repr.currentText())

        if not (repr_name and ds_name):
            #print "combo en cours de remplissage"
            return

            

        #========   On vide la comboList de representation et on ==============
        #===== remplit avec les noms des representations associées à ce ds ====
        combo_repr.clear()

        for repr_name in list(di[ds_name]["representations"].keys()):
            combo_repr.addItem(repr_name)


        print("=========Dataset" , dsId , "changed===========")
        print("ds_name:  " , ds_name)


    def setDatasetRepr(self, dsId):
        """
        Methode appelée lorsque l'element selectionné dans les comboBoxs
        dsA_repr ou dsB_repr change. Avec dsId = A ou B
        """

        p  = self.panel
        di = self.datasets_infos
        rs = self.relationships
        ds = self.datasets #objet local contenant les infos sur A et B


        #======================================================================
        #   Lecture GUI
        #======================================================================
        dsA_name = str(p.combo_dsA.currentText())
        dsB_name = str(p.combo_dsB.currentText())

        dsA_repr_name = str(p.combo_dsA_repr.currentText())
        dsB_repr_name = str(p.combo_dsB_repr.currentText())

        

        if dsId == "A":
            repr_name = dsA_repr_name
            ds_name   = dsA_name

        if dsId == "B":
            repr_name = dsB_repr_name
            ds_name   = dsB_name

        if not (dsA_name and dsB_name and dsA_repr_name and dsB_repr_name):
           # print "combo en cours de remplissage"
            return

        ds_uid      = di[ds_name]["uid"]
        ds_repr     = di[ds_name]["representations"]
        ds_repr_img = ds_repr[repr_name]["image"]

        #======================================================================
        # Si image est en float32 ou grayscale, on convertit en RGB
        # necessaire pour utiliser la transparence (?)
        #======================================================================

#        if   len(ds_repr_img) == 2:
#            print "mono channel image for %s",repr_name
#        elif len(ds_repr_img) == 3:
#            nb_cannel = ds_rep_img.shape[2]
#            print "%d channels image for %s",nb_channel,repr_name

        #======================================================================
        #   On met à jour les images dans A ou dans B
        #======================================================================

        ds[dsId]["curvePlot"]

        image     = ds[dsId]["imageItem"]
        imagePlot = ds[dsId]["imagePlot"]


        ds[dsId]["selectPointTool"]
        ds[dsId]["pointsList"]
        ds[dsId]["selectionPoint"]


        if dsId =="B":
            ds["B"]["rawImage"] = ds_repr_img

            #dds["selectionPointCurvePlot"]
            #dds["overlapImageItem"]
        #======================================================================
        #   Points de correspondances par default
        #======================================================================
        xdataA, ydataA = di[dsA_name]["xdata"],di[dsA_name]["ydata"]
        xdataB, ydataB = di[dsB_name]["xdata"],di[dsB_name]["ydata"]

        if dsId == "A": xdata, ydata = xdataA, ydataA
        if dsId == "B": xdata, ydata = xdataB, ydataB

        print("xdata for dataset {}:{}".format(dsId,xdata))
        print("ydata for dataset {}:{}".format(dsId,ydata))

        

        originalPointListA  = {"top left":    [xdataA[0],ydataA[0]],
                               "top right":   [xdataA[1],ydataA[0]],
                               "bottom right":[xdataA[1],ydataA[1]],
                               "bottom left": [xdataA[0],ydataA[1]]}

        originalPointListB  = {"top left":    [xdataB[0],ydataB[0]],
                               "top right":   [xdataB[1],ydataB[0]],
                               "bottom right":[xdataB[1],ydataB[1]],
                               "bottom left": [xdataB[0],ydataB[1]]}


        ds["A"]["originalPointsList"] = originalPointListA
        ds["B"]["originalPointsList"] = originalPointListB    

        #======================================================================
        #   On charge les points de correspondance (si existent) depuis
        #   le dictionnaire "relationship", sinon on met ceux par defaut
        #======================================================================
        uidA = di[dsA_name]["uid"]
        uidB = di[dsB_name]["uid"]

        #print "(uidA,uidB):",uidA,uidB

        #les 2 clefs possibles sont 001,002 ou 002,001
        keyAB = "%s,%s" % (uidA,uidB)
        keyBA = "%s,%s" % (uidA,uidB)


        if keyAB in rs:

            mess = "Relationship '%s'->'%s' exists" % (dsA_name,dsB_name)

            print(mess)

            p.label_matching.setText(mess)

            if ("pointsPositionA" in rs[keyAB]) and ("pointsPositionB" in rs[keyAB]):
                ds["A"]["pointsList"] = rs[keyAB]["pointsPositionA"]
                ds["B"]["pointsList"] = rs[keyAB]["pointsPositionB"]

            else:
                self.initPoints()



        else:
            mess = "Relationship '%s'->'%s' doesn't exists yet" % (dsA_name,dsB_name)
            print(mess)
            p.label_matching.setText(mess)

            self.initPoints()

        #======================================================================
        #
        #======================================================================

        ds["A"]["name"] = dsA_name
        ds["B"]["name"] = dsB_name   


        #on enregistre, pas necessaire car dict modifier en live?
        self.datasets = ds 

        #======================================================================
        #   rafraichissement de l'affichage
        #======================================================================
        #print "ds_repr_img shape:",ds_repr_img.shape
        #print ds_repr_img[0,:,3]

        image.set_xdata(xdata[0],xdata[1])
        image.set_ydata(ydata[0],ydata[1])

        image.set_data(ds_repr_img)

        imagePlot.do_autoscale()
        imagePlot.replot()



        self.processTransformationMatrixs()
        self.drawCornersPoints()
        self.drawSelectionPoint()

        self.drawOverlapImage()#mise a jour de l'image overlap

        #======================================================================

        print("=========Dataset",dsId,"Repr changed===========")
        print("ds_name:  " , ds_name)
        print("ds_uid:   " , ds_uid)
        print("repr_name:" , repr_name)
        print("nbr repr: " , len(ds_repr))

        #print "repr img: " , ds_repr_img



    def set_datasets(self, datasets_infos, relationships = dict()):
        """
        On appelle cette methodes depuis le programme principal pour definir
        la liste des jdd "matchables"
        """

        p = self.panel

#        print "datasets_infos:"
#        pprint(datasets_infos)
#        print "datasets_relationship:\n",
#        pprint(relationships)

        #======================================================================
        # on garde datasets_infos et relationships en memoire
        #======================================================================
        self.datasets_infos = copy.deepcopy(datasets_infos)
        self.relationships  = copy.deepcopy(relationships)

        print("inside set_datasets:")

        print(list(self.relationships.keys()))

        #======================================================================
        # TODO, creer un setDatasetsInfos et setRelationships pour
        # verifier la validité des données
        #======================================================================
        for k in list(datasets_infos.keys()):

            print("xdatas for '%s':" % (k,), datasets_infos[k]["xdata"])
            print("ydatas for '%s':" % (k,), datasets_infos[k]["ydata"])

        #======================================================================
        #     Initialisation des comboLists
        #======================================================================

        p.combo_dsA.clear()
        p.combo_dsB.clear()

        for ds_name in list(datasets_infos.keys()):

            p.combo_dsA.addItem(ds_name)
            p.combo_dsB.addItem(ds_name)

#        p.combo_dsA_repr.clear()
#        p.combo_dsB_repr.clear()


        #======================================================================
        #     Initialisation des positions des points dans A et B
        #======================================================================
        if relationships:
            pass


        #======================================================================
        #     Mise à jour de l'affichage
        #======================================================================

        self.setDatasetRepr("A")
        self.setDatasetRepr("B")

        

    def validate_matching(self):
        """
        Ici on creer ou on modifie les données existantes de ds_infos
        """
        p  = self.panel
        di = self.datasets_infos
        rs = self.relationships
        ds = self.datasets

        dsA_name = ds["A"]["name"]
        dsB_name = ds["B"]["name"]

        uidA = di[dsA_name]["uid"]
        uidB = di[dsB_name]["uid"]

        keyAB = "%s,%s" % (uidA, uidB)
        keyBA = "%s,%s" % (uidB, uidA)

        logging.debug("keyAB: %s" % (keyAB,))
        logging.debug("keyBA: %s" % (keyBA,))


        #on cree un dictionnaire si l'entrée n'existe pas deja
        if keyAB not in rs:
            print("creating new entry for %s->%s" % (dsA_name, dsB_name))
            rs[keyAB] = dict()

        if keyBA not in rs:
            print("creating new entry for %s->%s" % (dsB_name,dsA_name))
            rs[keyBA] = dict()


        rs[keyAB]["Mab"] = self.Mab
        rs[keyAB]["pointsPositionA"] = copy.deepcopy(ds["A"]["pointsList"])
        rs[keyAB]["pointsPositionB"] = copy.deepcopy(ds["B"]["pointsList"])


        #=============== on calcule la relation inverse =======================
        rs[keyBA]["Mab"] = self.Mba

        rs[keyBA]["pointsPositionA"] = copy.deepcopy(ds["B"]["pointsList"])
        rs[keyBA]["pointsPositionB"] = copy.deepcopy(ds["A"]["pointsList"])


        #=====================GUI==============================================
        #QMessageBox.information(self,'info',"Relationship recorded")
        p.label_matching.setText('"%s" <-> "%s" matching recorded' % (dsA_name,dsB_name))
        #======================================================================

        self.relationships = rs

        

    def setPoint(self,tool):

        #TODO: empecher les setPoints d'être placés en dehors des images

        p = self.panel

        #======sur quel spectre a-t-on cliqué?========

        sptA = self.datasets["A"]["selectPointTool"]
        sptB = self.datasets["B"]["selectPointTool"]


        if tool is sptA: currentDataset = "A"
        else:            currentDataset = "B"

        #print "current dataset:",currentDataset

        plotX, plotY = tool.get_coordinates()

        #print "(plotX,plotY):", plotX, plotY


        #====si on est pas en mode "Check" ============
        if not self.check_mode:
            #print "Not checked"
            point_name  = p.comboBox_selectedPoint.currentText()
            #point_index = p.comboBox_selectedPoint.findText(point_name)

            if not point_name:
                print("No point selected!")
                return

            #liste des points
            ptslist = self.datasets[currentDataset]["pointsList"]    

            #On met à jour les coordonnées du point séléctionné
            ptslist[str(point_name)] = [plotX,plotY]



        #======si on est en mode check===========

        else:
            #print "checked"

            if currentDataset == "B":

                coo_inB = np.array([plotX,plotY,1])
                res     = np.dot(self.Mba,coo_inB.T)
                coo_inA = res/res[2]

            elif currentDataset == "A":

                coo_inA = np.array([plotX,plotY,1])
                res     = np.dot(self.Mab,coo_inA.T)
                coo_inB = res/res[2]


            self.datasets["A"]["selectionPoint"] = [coo_inA[0],coo_inA[1]]
            self.datasets["B"]["selectionPoint"] = [coo_inB[0],coo_inB[1]]
        

        self.processTransformationMatrixs()
        self.drawCornersPoints()
        self.drawSelectionPoint()

            



    def drawCornersPoints(self):

        for ds_name in ("A","B"):

            curve     = self.datasets[ds_name]["curvePlot"]
            imagePlot = self.datasets[ds_name]["imagePlot"]
            ptslist   = self.datasets[ds_name]["pointsList"]    


            #on met sous forme de liste pour tracer tout le monde...

            tmp = ([value[0] for value in ptslist.values()],
                   [value[1] for value in ptslist.values()])

            curve.set_data(tmp[0],tmp[1])
            imagePlot.replot()

    

        

    def drawSelectionPoint(self):
        #===== On trace dans A le point selectionné en B et vice-versa =======#

        for ds_name in ("A","B"):
            curve     = self.datasets[ds_name]["selectionPointCurvePlot"]
            imagePlot = self.datasets[ds_name]["imagePlot"]
            s_point   = self.datasets[ds_name]["selectionPoint"]

            if s_point:
                curve.set_data([s_point[0]],[s_point[1]])
                imagePlot.replot()

        #============================================================#


    def setCheckMode(self):
        self.check_mode = not self.check_mode

        

    def setOverlapMode(self):
        p = self.panel

        self.overlap_mode = not self.overlap_mode

        p.slider_alpha.setEnabled(self.overlap_mode)


        ds = self.datasets["A"]

        ds["imagePlot"].set_item_visible(ds["overlapImageItem"],self.overlap_mode)



        

    def testPoints(self):
        """
        Creer un placement de point de test
        """

        print("inside testPoints")

        p = self.panel

        dsA_name   = str(p.combo_dsA.currentText())
        dsB_name   = str(p.combo_dsB.currentText())

        xrangeA = self.datasets_infos[dsA_name]["xdata"]
        yrangeA = self.datasets_infos[dsA_name]["ydata"]

        xrangeB = self.datasets_infos[dsB_name]["xdata"]
        yrangeB = self.datasets_infos[dsB_name]["ydata"]

        wA = xrangeA[1] - xrangeA[0]
        hA = yrangeA[1] - yrangeA[0]


        self.datasets["A"]["pointsList"] = {"top left":    [xrangeA[0] + wA/2.5,        yrangeA[0] + hA/3],
                                            "top right":   [xrangeA[0] + wA/2.5 + wA/3, yrangeA[0] + hA/3],
                                            "bottom right":[xrangeA[0] + wA/2.5 + wA/3, yrangeA[0] + hA/3 + hA/3],
                                            "bottom left": [xrangeA[0] + wA/2.5,        yrangeA[0] + hA/3 + hA/3]}



        self.datasets["B"]["pointsList"] = copy.deepcopy(self.datasets["B"]["originalPointsList"])

        self.processTransformationMatrixs()
        self.drawCornersPoints()
        self.drawSelectionPoint()

        

        

    def initPoints(self):
        """
        points_in_base =  [[x1,x2,x3,...,x4]
                           [y1,y2,y3,...,y4]
                           [z1,z2,z3,...,z4] # optionnel
                           [1, 1 , 1,..., 1]]

        M : Matrice de passage A->B
        coo_baseB = M x coo_baseA
        M = matrice_coo_baseB x inv(matrice_coo_baseA)

        """
        print("Reset corners")


        #========On place les points par default=====================#
        #nb: dict1 = dict2 fait pointer sur le meme dict, pas de copie, dict.copy
        #fonctionnerais ici mais attention, si le dict contient des dict ou lists
        #on aurait encore des interaction, d'ou l'utilisation de deepcopy
        self.datasets["A"]["pointsList"] = copy.deepcopy(self.datasets["A"]["originalPointsList"])
        self.datasets["B"]["pointsList"] = copy.deepcopy(self.datasets["B"]["originalPointsList"])

        self.processTransformationMatrixs()
        self.drawCornersPoints()
        self.drawSelectionPoint()

        

    

    def processTransformationMatrixs(self):

        print("processTransformationMatrixs")

        #pour avoir les points dans le meme ordre car itervalues ne suis pas
        #l'ordre d'insertion dans le dict
        points_ids = list(self.datasets["B"]["pointsList"].keys())

        

        #============ Matrice de coordonnées base B =======================#
        points = self.datasets["B"]["pointsList"]

        points_in_baseB = [[points[point_id] for point_id in points_ids]]
        points_in_baseB = np.array(points_in_baseB,dtype=np.float32) 



        #============ Matrice de coordonnées base A =======================#
        points = self.datasets["A"]["pointsList"]

        points_in_baseA = [[points[point_id] for point_id in points_ids]]
        points_in_baseA = np.array(points_in_baseA,dtype=np.float32) 



        #============ Matrice de passage A->B =======================#
        Mab = cv2.getPerspectiveTransform(points_in_baseA, points_in_baseB)
        Mba = cv2.getPerspectiveTransform(points_in_baseB, points_in_baseA)
        # print("MBA1\n",Mba)
        # Mba = np.linalg.inv(Mab)
        # print("MBA2\n", Mba) il y a une inversion de signe

#        print "points_in_baseB:", points_in_baseB
#        print "points_in_baseA:", points_in_baseA

        #============ verification =======================#
#        cooA = np.array([0.67,0.67,1])
#        cooB = np.array([0.59,0.98,1])
#
#        print type(Mab)
#        print "---------------"
#        print "cooA:",cooA
#        res = np.dot(Mab,cooA.T)
#        print "cooB:",res/res[2]
#        print "---------------"
#        print "cooB:",cooB
#        res = np.dot(Mba,cooB.T)
#        print "cooA:",res/res[2]
#
        self.Mab = Mab
        self.Mba = Mba

        self.drawOverlapImage()

        #=====================================================================#

        


    def exportMatrixs(self):
        print("export Transformation Matrix")

        filename = str(QFileDialog.getSaveFileName(self, "Save Transformation Matrixs", "",".mat"))[0]
        if not filename:
            print("No filename specified, abort")
            return

        data = dict(Mab = self.Mab,
                    Mba = self.Mba,
                    a_name = "nom dataset A",
                    b_name = "nom dataset B")

        scipy.io.savemat(filename,data)

    

    def updateOverlapImageItem(self, imgA_item, imgB_item, overlapImg_item):
        """
        modify overlapImageItem from imageItem (Qwt) A and B
        imagePlot
        """
        pass

    


    def drawOverlapImage(self,opacity = None):
        """
        TODO: si possible, ne pas tout recalculer quand on touche juste au alpha
        """
        p       = self.panel
        opacity = p.slider_alpha.value()

        imgA         = self.datasets["A"]["imageItem"]
        imgB         = self.datasets["B"]["imageItem"]
        imagePlotA   = self.datasets["A"]["imagePlot"]

        overlapImage = self.datasets["A"]["overlapImageItem"]
        imgBraw      = self.datasets["B"]["rawImage"] #on charge l'image originale
        pointsListA  = self.datasets["A"]["pointsList"]

        #coordonnées coins images (rectangle) dans le referenciel Plot B
        xmin_B, xmax_B = imgB.get_xdata()
        ymin_B, ymax_B = imgB.get_ydata()

        data_width_B   = abs(xmax_B - xmin_B)
        data_height_B  = abs(ymax_B - ymin_B)
        imageB_data_range = (data_width_B, data_height_B)

        #Les coordonnées de ces points dans A permettront de definir celle de
        #la bounding-box de la projection de B dans A
        tlB = [xmin_B,ymin_B]
        trB = [xmax_B,ymin_B]
        brB = [xmax_B,ymax_B]
        blB = [xmin_B,ymax_B]

        #coordonnées coins images dans A forment un quadrilatère
        Mba = self.Mba
        cornersB = np.float32([tlB,trB,brB,blB]).reshape(-1,1,2)
        cornersA = cv2.perspectiveTransform(cornersB, Mba)

        tlA = cornersA[0][0]
        trA = cornersA[1][0]
        brA = cornersA[2][0]
        blA = cornersA[3][0]

        #on cherche les coordonnées de la "bounding-box" (bb) de ce quadrilatère
        bbox_xmin, bbox_xmax = min([tlA[0],blA[0]]), max([trA[0],brA[0]])
        bbox_ymin, bbox_ymax = min([tlA[1],trA[1]]), max([blA[1],brA[1]])

        xmin_A, xmax_A = imgA.get_xdata()
        ymin_A, ymax_A = imgA.get_ydata()

        data_width_A   = abs(xmax_A - xmin_A)
        data_height_A  = abs(ymax_A - ymin_A)
        imageA_data_range = (data_width_A, data_height_A)


        imgB_res = imgBraw.shape
        imgA_res = imgA.data.shape

        w_overlap = abs(bbox_xmax - bbox_xmin)
        h_overlap = abs(bbox_ymax - bbox_ymin)

        #on prend comme resolution de l'image Overlap un carré de max (res_x,res_y)
        #pour avoir une image correct même en cas de rotation à 90° de l'image init
        #limite de 2000px pour ne pas degrader trop les performances
        limit_res_x = 2000
        limit_res_y = 2000
        overlapImage_limit_res = (limit_res_x, limit_res_y)


        bbox_res_x = min(overlapImage_limit_res[0], max(imgBraw.shape))
        bbox_res_y = min(overlapImage_limit_res[1], max(imgBraw.shape))
        bbox_res = (bbox_res_x, bbox_res_y)

        print("originale res image B:",imgB_res)
#        print "resolution bounding_box:",bbox_res_x,bbox_res_y
#        print "resolution conteneur:",w_conteneur,h_conteneur





        #====================================================================
        # gardes-fous pour ne pas avoir une image trop lourde
        #====================================================================
        """
        TODO: affichage incorrect si on depasse les limites, ajuster
        MMmatch en consequence
        """
        if bbox_res[0] > overlapImage_limit_res[0] or bbox_res[1] > overlapImage_limit_res[1]:
            dsize = overlapImage_limit_res
            print("Image output too big (%d,%d)," % (bbox_res[0],bbox_res[1]))
            print("displaying at (%d,%d)" % (dsize[0], dsize[1]))
        else:
            dsize = bbox_res
        #====================================================================



        #TODO: a mettre en pixel si xdata pas en pixel
        dx, dy = bbox_xmin, bbox_ymin
        rx, ry = dsize[0]/data_width_A, dsize[1]/data_height_A


        dx_px = dsize[0] * (dx/data_width_A)
        dy_px = dsize[1] * (dy/data_height_A)

        #======================================================================
        # matrice de passage de A vers l'image HR incluse dans A
        #======================================================================
        #cv2.warpPerspective() transforme 2 images en pixel et suppose que les
        #le pixel est l'unité commune. Pour nous, les "pixels" ont des tailles
        #differentes. On prend donc les coordonnées data de l'imageB et on adapte
        #ces dernières pour mettre le pixel à la meme taille que ceux de
        #l'image A

        points = pointsListA
        points_in_baseA = [[coo for coo in points.values()]]    

        points_in_baseA = np.array(points_in_baseA, dtype=np.float32)


        #rapport d'echelle des axes de l'imageA et l'imageB
        w_overlap_px = (1.0*w_overlap/data_width_A)*imgA_res[0]
        h_overlap_px = (1.0*h_overlap/data_height_A)*imgA_res[1]

        rx_px = 1.0*dsize[0]/w_overlap_px
        ry_px = 1.0*dsize[1]/h_overlap_px

        Mac    = np.array([[rx, 0, -dx],
                           [0, ry, -dy],
                           [0,  0,  1]])

        print("Mac:\n", Mac)

        print("dx,dy,dx_px,dy_px,rx,ry,rx_px,ry_px",dx,dy,dx_px,dy_px,rx,ry,rx_px,ry_px)
        #=====================================================================
        #matrice de transformation pour l'utilisation avec cv2.warpPerspective
        Mtransfo = np.dot(Mac, Mba)

        Mtransfo = Mba

        #======================================================================
        # Si image est en float32 ou grayscale, on convertit en RGB
        # etape necessaire pour utiliser la transparence
        #======================================================================

        #on creer une image rgba à partir de la rgb

#        tmp = np.zeros((imgBraw.shape[0],imgBraw.shape[1],4))
#        tmp[:,:,0:2] = imgBraw[:,:,0:2]
#        imgBraw  = tmp

        #====================================================================
        # si on veux mettre en evidence la bounding_box
        #====================================================================
        show_bounding_border = True

        if show_bounding_border:
            borderValue = (255,0,0,120)

        else:
            borderValue = (255,0,0,0)
        #======================================================================

        w, h    = imgB_res[0], imgB_res[1]
        tmpImg = np.zeros((w,h,4), dtype = np.uint8)

        #print("imgBraw.shape",imgBraw.shape)
        #print imgBraw
        # Image rvb

        if len(imgBraw.shape) == 3:
            tmpImg[...,0:3] = imgBraw[...,0:3]

        # Image 1 channel
        elif len(imgBraw.shape) == 2:
            #on convertie en rvba à partir de la color_map et du lut 

            color_map = imgB.get_color_map()
            lut_range = imgB.get_lut_range()

            print("color_map",color_map)
            print("lut_range",lut_range)

            tmpImg[...,0:3] = imgB.get_lut_range()


        #On change l'opacité pour la superposition
        tmpImg[...,3]   = opacity


        try:
            tmpImg = cv2.warpPerspective(tmpImg,
                                         Mtransfo,
                                         dsize = dsize,
                                         borderValue = borderValue)


            print("setting x/y data of overlapimage")
            print("xmin_bbox,xmax_bbox:")
            print(bbox_xmin,bbox_xmax)
            print("ymin_bbox,ymax_bbox:")
            print(bbox_ymin,bbox_ymax)

            overlapImage.set_xdata(bbox_xmin,bbox_xmax)
            overlapImage.set_ydata(bbox_ymin,bbox_ymax)

            overlapImage.set_data(tmpImg)

        

        except MemoryError:
            print("Image output too big (%d,%d), display aborted" % (bbox_res_x,bbox_res_y))
            return


        imagePlotA.replot()

        

        

    def colorGenerator(self):
        COLORS = ["blue", "cyan", "magenta", "green", "yellow", "black", "gray", "darkMagenta", "darkCyan", "darkRed", "darkGreen"]
        #,(204,0,204),(153,102,204),(255,204,255),(204,255,255),(102,51,51),(153,153,51),

        while True:

          for color in COLORS:

             yield color

             

def test():

    qtApp = QtWidgets.QApplication([''])
    gui = DatasetsMatcher()
    gui.show()
    qtApp.exec_()



def test2():

    qtApp = QtWidgets.QApplication([''])

    gui = DatasetsMatcher()

    base_dir = "\\\crabe\\communs\\LIDyL\\PCR\\Mickael Bouhier\\datasetMatcher\\"


    #============representation des jdd =======================================

    #======"dataset 1 Raman" ====================================================

    img0  = cv2.imread(base_dir + "datas\\worldmap\\iceland_gmap_hd.jpg")
    img0  = cv2.cvtColor(img0, cv2.COLOR_BGR2RGBA) 

    img1  = cv2.imread(base_dir + "datas\\worldmap\\iceland_gmap_hd_PC1.jpg")
    img1  = cv2.cvtColor(img1, cv2.COLOR_BGR2RGBA)     

    img2  = cv2.imread(base_dir + "datas\\worldmap\\iceland_gmap_hd_PC2.jpg")
    img2  = cv2.cvtColor(img2, cv2.COLOR_BGR2RGBA)  

    img3  = cv2.imread(base_dir + "datas\\worldmap\\iceland_gmap_hd_PC3.jpg")
    img3  = cv2.cvtColor(img3, cv2.COLOR_BGR2RGBA)  


    repr_ds1 = dict()

    repr_ds1["PC0 test"]= {'image':img0}
    repr_ds1["PC1 test"]= {'image':img1}
    repr_ds1["PC2 test"]= {'image':img2}
    repr_ds1["PC3 test"]= {'image':img3}


    #======"dataset 2 Optique" ==================================================

    img1  = cv2.imread( base_dir + "datas\\worldmap\\wm_lr.jpg")
    img1  = cv2.cvtColor(img1, cv2.COLOR_BGR2RGBA)     

    

    repr_ds2 = dict()
    repr_ds2["raw"] = {'image':img1}


    #======"dataset 3 MEB" ================================================

    img1  = cv2.imread( base_dir + "datas\\worldmap\\wm_lr.jpg")
    img1  = cv2.cvtColor(img1, cv2.COLOR_BGR2RGBA)     

    

    repr_ds3 = dict()

    repr_ds3["element A"] = {'image':img1}
    repr_ds3["element B"] = {'image':img1}
    repr_ds3["element C"] = {'image':img1}
    repr_ds3["element D"] = {'image':img1}
    repr_ds3["element E"] = {'image':img1}

    

    #======"dataset 4 Optique" ================================================

    img4  = cv2.imread( base_dir + "datas\\worldmap\\europe_hd_45deg2.jpg")
    img4  = cv2.cvtColor(img4, cv2.COLOR_BGR2RGBA)     

    

    repr_ds4 = dict()    

    repr_ds4["element 1"] = {'image':img4}



    #======"blanc 800x600" ================================================

    img5  = cv2.imread( base_dir + "datas\\blanc.jpg")
    img5  = cv2.cvtColor(img5, cv2.COLOR_BGR2RGBA)     

    repr_ds5 = dict()        

    repr_ds5["element 1"] = {'image':img5}

    

    #======"ronds 3x2" ================================================

    img6  = cv2.imread( base_dir + "datas\\ronds_3x2.jpg")
    img6  = cv2.cvtColor(img6, cv2.COLOR_BGR2RGBA)     

    repr_ds6 = dict()     

    repr_ds6["element 1"] = {'image':img6}



    #======"rectangles 3x2" ================================================

    img7  = cv2.imread( base_dir + "datas\\rectangles_3x2.jpg")
    img7  = cv2.cvtColor(img7, cv2.COLOR_BGR2RGBA)     

    repr_ds7 = dict()
    repr_ds7["element 1"] = {'image':img7}

    

    #============liste de jeux de données:=====================================

    ds_infos = {
                 "dataset 1 Raman": {
                                     "uid" : '001',
                                     "xdata" : [0,833],
                                     "ydata" : [0,641],
                                     "representations":repr_ds1
                                     },

                 "dataset 2 Optique":{
                                      "uid" : '002',
                                      "xdata" : [0,800],
                                      "ydata" : [0,600],
                                      "representations":repr_ds2
                                     },

                 "dataset 3 MEB":{
                                      "uid" : '003',
                                      "xdata" : [0,800],
                                      "ydata" : [0,600],
                                      "representations":repr_ds3
                                     },

                 "dataset 4 Optique":{
                                      "uid" : '004',
                                      "xdata" : [0,515],
                                      "ydata" : [0,518],
                                      "representations":repr_ds4
                                     },

                 "blanc 800x600":{
                                      "uid" : '005',
                                      "xdata" : [0,800],
                                      "ydata" : [0,600],
                                      "representations":repr_ds5
                                     },

                 "ronds 3x2":{
                                      "uid" : '006',
                                      "xdata" : [0,800],
                                      "ydata" : [0,600],
                                      "representations":repr_ds6
                                     },

                 "rectangles 3x2":{
                                      "uid" : '007',
                                      "xdata" : [0,800],
                                      "ydata" : [0,600],
                                      "representations":repr_ds7
                                     },

                }

    #============dictionnaires des relations entre jdds========================

    relationships =  {
#                       "001,002":{
#                                            "Mab":0,
#                                            "pointsPositionA":{"top left":    [0,0],
#                                                               "top right":   [600,0],
#                                                               "bottom right":[600,800],
#                                                               "bottom left": [0,800]},
#                                            "pointsPositionB":{"top left":    [0,0],
#                                                               "top right":   [600,0],
#                                                               "bottom right":[600,800],
#                                                               "bottom left": [0,800]}
#                                           },
#                       "001,002":{
#                                            "Mab":0,
#                                            "pointsPositionA":{"top left":    [0,0],
#                                                               "top right":   [600,0],
#                                                               "bottom right":[600,800],
#                                                               "bottom left": [0,800]},
#                                            "pointsPositionB":{"top left":    [0,0],
#                                                               "top right":   [600,0],
#                                                               "bottom right":[600,800],
#                                                               "bottom left": [0,800]}
#                                           },
#                       "003,001":{
#                                            "Mab":0,
#                                            "pointsPositionA":{"top left":    [0,0],
#                                                               "top right":   [600,0],
#                                                               "bottom right":[600,800],
#                                                               "bottom left": [0,800]},
#                                            "pointsPositionB":{"top left":    [0,0],
#                                                               "top right":   [600,0],
#                                                               "bottom right":[600,800],
#                                                               "bottom left": [0,800]}
#                                           },
                      }

    gui.set_datasets(ds_infos,relationships)

    gui.show()
    qtApp.exec_()


if __name__ == "__main__":

    test2()

 
