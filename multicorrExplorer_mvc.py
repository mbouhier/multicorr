# -*- coding: utf-8 -*-

"""
Created on Wed Jan 29 15:34:18 2014

@author: mbouhier

"""

import time

import plotpy
import numpy as np
from PyQt5 import QtGui, QtWidgets
from PyQt5 import uic
from PyQt5.QtWidgets import *

import plotpy
from plotpy.builder import make
from plotpy.plot import PlotDialog
from numpy import sqrt, diff

from helpers.plots import plots

print("plotpy version:", plotpy.__version__)

from plotpy.items import RGBImageItem
from plotpy.interfaces import IImageItemType
from plotpy.items import PolygonShape
from plotpy.styles import ImageParam
from plotpy.plot import PlotOptions
import re

from plotpy.tools import SelectPointTool, FreeFormTool

#from guidata.qt import QtCore
from PyQt5 import QtCore


#from qwt.qt.QtGui import QFont
from PyQt5.QtGui import QFont

from PyQt5.QtCore import *

from numpy.random import randn
import random


from threading import Thread
import threading



#from scipy.interpolate import interp1d

#import matplotlib.pyplot as pl


from openWireData import openWireData2

from functools import partial

import cv2

from XMLModelLoader import XMLModelLoader


# pour accelerer les operation sur les array, voir https://github.com/pydata/numexpr
# import numexpr as ne


import os
os.system('')#enable VT100 emulation on windows 10 for colored output in console


# =====================    PCA     ==============================================
# from sklearn.decomposition import PCA, FastICA, RandomizedPCA, IncrementalPCA
from sklearn.decomposition import PCA, IncrementalPCA
# ===============================================================================


import sys
import traceback


from businessLogic.mainLogic import MCBusinessLogic

from helpers import mc_logging

from plugins.mcPlugins import Plugins

from safeprint import print


#==========================================================================
# On catch les exceptions dans le logger du programme
#===========================================================================
def exception_hook(exctype, value, traceback):
    mc_logging.error("exctype:",exctype)
    mc_logging.error("value:",value)
    #mc_logging.error("traceback: %s" % (''.join(traceback.format_stack()),))
    sys.__excepthook__(exctype, value, traceback)
    sys.exit(1)

sys.excepthook = exception_hook


# ==========================================================================
from dataAccess.mcData import McData

from helpers.bigDataTools import fillByChunk, getChunkSize, normalizeHDF5, stdHDF5, getMean

from presentation.controller import MCPresentationController

import helpers

from helpers.dialogs import InputDialogText
import datetime


class ClusterExplorer(QtWidgets.QMainWindow):
    # =========================================================================
    #             Liste des signaux QT
    # =========================================================================

    def __init__(self):
        super().__init__()

        version = "dev."

        self.title = self.setWindowTitle("Multicorr - Version {}".format(version))
        self.setWindowIcon(QtGui.QIcon('bin//icons//logo_reduced.png'))

        self.initVariables()
        self.initGui()

        mc_logging.setPath("bin//logs")

        # ============== Pour les tests, chargement auto ===================
        #self.gui.io.loadProject("pour_test_overlap.h5")

    def initGui(self):
        # ======================================================================
        #     Creation des widgets Plot et image
        # =======================================================================
        p = self.gui.panel

        # =======================================================================
        #     Configuration plot et image
        # =======================================================================
        #self.initRepresentationTab()
        self.initMultiDatasetExplorerTab()
        self.initOverviewTab()

        # =======================================================================
        #     Configuration signaux/slots
        # =======================================================================
        self.makeConnections()

        # =======================================================================
        #    Desactivation tant qu'il n'y à pas de jdd chargé
        # =======================================================================
        self.gui.datasets.signal_disableGuiActionsOnDataset.emit(True)

    def initVariables(self):
        '''
        Creation des variables principales utilisees par le programme
        '''
        temp_path = "bin//temp"

        self.mcData = McData(temp_path)

        self.bl = MCBusinessLogic(self.mcData)

        #====================================================================================
        #                Presentation MainController
        #====================================================================================
        self.gui = MCPresentationController(self.bl, self.mcData, mainWindow = self)


        #====================================================================================
        #                 Initialisation des Plugins
        #====================================================================================
        self.plugins = Plugins(self.bl, self.mcData, self.gui)

        self.display = dict()

        # ============= Contenant pour spectres importés =======================
        self.externalSpectrums = dict()


        self.mcData.currentSpectrumIndex = 0

        # ==========Specifique aux threads===================
        self.bl.threading.setProcessingThreadFlag(self.bl.threading.states.RESET)




    def makeConnections(self):

        p = self.gui.panel


        # ===========================Onglet PCA==================================
        p.pcaButton.clicked.connect(self.processPCA)
        # =======================================================================


        # =========================== Datasets ==================================
        #p.button_insertSpectrumInPCSpace.clicked.connect(self.insertSpectrumInPCSpace)


        # =========================  Display  ===================================
        p.combo_metadatas.currentIndexChanged.connect(self.comboMetadatasChanged)


        # =======================================================================
        #                                   Plugins
        # =======================================================================
        for plugin_name, plugin in self.plugins:
            menu_item = getattr(plugin, "menu_item", None)
            self.gui.menu.addMenu(menu_item, plugin.tab)


        # =========================== Infos Tab ================================
        #Maintenant dans self.gui.datasets.py
        p.infoProbeDx.returnPressed.connect(self.changeProbeParameters)
        p.infoProbeDy.returnPressed.connect(self.changeProbeParameters)
        p.combo_probeShape.currentIndexChanged.connect(self.changeProbeParameters)
        p.combo_probeOrigin.currentIndexChanged.connect(self.changeProbeParameters)


        p.checkBox_normalizeDatas.stateChanged.connect(self.setUseNormalizedData)
        p.combo_normalisation_type.currentIndexChanged.connect(self.setNormalizeType)

        # ======================== Representations==============================



        # ================== Signaux depuis les Threads/methodes =========================
        self.gui.main.signal_displayCoeffsHistogram.connect(self.displayCoeffsHistogram)
        self.gui.main.signal_updateRepresentationsDisplay_inMultiDatasetExplorer.connect(
            self.updateRepresentationsDisplay_inMultiDatasetExplorer)
        self.gui.main.signal_updateLinkedDatasetsList_inMultiDatasetExplorer.connect(
            self.updateLinkedDatasetsList_inMultiDatasetExplorer)

        self.gui.menu.display.signal_updateProbesShapesAndPlots_inMultiDatasetExplorer.connect(self.updateProbesShapesAndPlots_inMultiDatasetExplorer)

        self.gui.main.signal_updatePlots_inMultiDatasetExplorer.connect(self.updatePlots_inMultiDatasetExplorer)

        self.gui.main.signal_updateInfosTab.connect(self.updateInfosTab)




    # ==========================================================================
    #            Deboggage pyqtSlot
    # ==========================================================================
    def notify(self, obj, event):
        isex = False
        try:
            return QtGui.QApplication.notify(self, obj, event)
        except Exception:
            isex = True
            print("Unexpected Error")
            print(traceback.format_exception(*sys.exc_info()))
            return False
        finally:
            if isex:
                self.quit()



    def displayProgressPopup(self, progress):

        progressPopup = getattr(self,"_progress_popup", None)

        if not progressPopup:
            progressPopup = QtWidgets.QProgressDialog("Loading project file", "Stop", 0, 100, self)
            progressPopup.setWindowModality(QtCore.Qt.WindowModal)

            progressPopup.setValue(progress)
            progressPopup.show()
            self._progress_popup = progressPopup
        else:
            progressPopup.setValue(progress)

        if progress == -1:
            progressPopup.deleteLater()


    # ===========================================================================
    #           Changement de selection courante
    # ===========================================================================
    ##@my_pyqtSlot()
    def updateInfosTab(self):
        """
        Mise a jour des informations sur le dataset dans la GUI
        """

        p = self.gui.panel

        ds = self.mcData.datasets.getDataset()

        if not ds: return False

        # ==== Nom dans la GUI et correspondance dans dictionnaire ds ==========

        params = {"infoXunit": ds["x_unit"],
                  "infoYunit": ds["y_unit"],
                  "infoSpatialUnit": ds["spatial_unit"],
                  "infoDx": "%.2f %s" % (ds["dx"], ds["spatial_unit"]),
                  "infoDy": "%.2f %s" % (ds["dy"], ds["spatial_unit"]),
                  "infoDs": "%.2f %s" % (ds["dy"], ds["x_unit"]),
                  "infoImageWidth": "%d px" % (ds["image_width"],),
                  "infoImageHeight": "%d px" % (ds["image_height"],),
                  "infoSpectralLength": "%d" % (len(ds["W"])), #ds["x_unit"]),
                  "infoDatasetLength": ds["size"],
                  "combo_probeShape": ds["probe"]["shape"],
                  "combo_probeOrigin": ds["probe"]["origin"],
                  "infoProbeDx": ds["probe"]["dx"],
                  "infoProbeDy": ds["probe"]["dy"],
                  }

        self.gui.main.setWidgetsValuesFromDict(p, params)




    # def insertSpectrumInPCSpace(self):
    #     """
    #     Ajout d'un spectre exterieur dans le jdd
    #     """
    #
    #     print("inside insertSpectrumInPCSpace")
    #
    #     ds_name = self.mcData.datasets.currentDatasetName
    #
    #     ds = self.mcData.datasets.getDataset(ds_name)
    #
    #     filename = str(QFileDialog.getOpenFileName(self, "Open Wire Map File..."))[0]
    #
    #     if filename:
    #
    #         try:
    #             spectrum, W, _ = openWireData2(filename)
    #             spectrum = spectrum[0]  # car sous forme de liste même pour un spectre unique
    #
    #         except Exception as e:
    #             print(("Unable to open %s:" % (filename)))
    #             print(e)
    #             return
    #
    #         spectrum_name = filename.split('/')[-1].split('.wxd')[0]
    #
    #         print(("inserting '%s' in PC space" % (spectrum_name,)))
    #         print(("xrange: %.2f-%.2f   dataset xrange:%.2f-%.2f" % (W[0], W[-1], ds["W"][0], ds["W"][-1])))
    #
    #         # =======  On interpole le spectre pour coller au W du dataset ====
    #
    #         f = interp1d(W, spectrum, kind='linear')
    #
    #         spectrum = f(ds["W"])
    #
    #         # ==================================================================
    #
    #         normalized_spectrum = np.transpose(spectrum / max(spectrum))
    #
    #         centered_spectrum = normalized_spectrum - ds["mean_datas_normalized"]
    #
    #         centered_spectrum = np.transpose(centered_spectrum)
    #
    #         print(("mean_data_normalized shape:", ds["mean_datas_normalized"].shape))
    #         print(("normalized spectrum shape:", normalized_spectrum.shape))
    #         print(("spectrum shape:", spectrum.shape))
    #         print(("dataset W shape:", ds["W"].shape))
    #         print(("substract shape", centered_spectrum.shape))
    #
    #         # ==============on ajoute du bruit sur le normalisé======================
    #
    #         noise_level = 0.1
    #
    #         normalized_spectrum = normalized_spectrum[0, :] + noise_level * randn(ds["size"])
    #
    #         print(("spectrum shape:", spectrum.shape))
    #
    #         # ==================================================================
    #
    #
    #
    #         if ds_name not in self.externalSpectrums:
    #             self.externalSpectrums[ds_name] = dict()
    #
    #         self.externalSpectrums[ds_name][spectrum_name] = (W, spectrum, normalized_spectrum)
    #
    #         # ================Affichage en popup temporaire ====================
    #
    #         pl.figure(0)
    #         pl.subplot(131)
    #         pl.plot(ds["W"], spectrum)
    #         pl.subplot(132)
    #         pl.plot(ds["W"], centered_spectrum)
    #         pl.subplot(133)
    #         pl.plot(ds["W"], ds["X_normalized"][5073] - ds["mean_datas_normalized"])  # zone aka
    #         pl.show()






    def isOverlapThreadRunning(self):
        return getattr(self, 'overlapRunning', False) and not self.bl.threading.processingThreadFinishedEvent.is_set()




    # ============================================================================
    #                       Fonctions autres
    # ============================================================================

    def euclidian_distance(self, Q, C, precomputed_CE_Q = None, precomputed_CE_C = None):
        """
        Give similarity distance based on complexity invariance
        "A Complexity-Invariant Distance Measure for Time Series" Gustavo E.A.P.A. Batista
        """

        if precomputed_CE_Q is not None:
            CE_Q = precomputed_CE_Q

        else:
            CE_Q = sqrt(sum(diff(Q) ** 2))

        if precomputed_CE_C is not None:
            CE_C = precomputed_CE_C

        else:
            CE_C = sqrt(sum(diff(C) ** 2))

        return sqrt(sum((Q - C) ** 2)) * 1

    def complexity_invariant_distance(self, Q, C, precomputed_CE_Q = None, precomputed_CE_C = None):
        """
        Give similarity distance based on complexity invariance
        "A Complexity-Invariant Distance Measure for Time Series" Gustavo E.A.P.A. Batista
        """

        if precomputed_CE_Q is not None:
            CE_Q = precomputed_CE_Q

        else:
            CE_Q = sqrt(sum(diff(Q) ** 2))

        if precomputed_CE_C is not None:
            CE_C = precomputed_CE_C

        else:
            CE_C = sqrt(sum(diff(C) ** 2))

        return sqrt(sum((Q - C) ** 2)) * (max(CE_Q, CE_C) / min(CE_Q, CE_C))

    # ===========================================================================
    #
    # ===========================================================================


    # =====================================================================
    #           Partie specifique au multidataset viewer
    # =====================================================================

    def initMultiDatasetExplorerTab(self):
        """
        Methode initialisant l'interface graphique de l'explorateur de datasets.py
        """

        print("Creating MultiDatasetExplorerTab")

        p = self.gui.panel

        # on garde les references aux widgets la dedans

        multiDatasetExplorerTab = dict()

        # =======================================================================
        #                           Partie Droite
        # =======================================================================


        # ================== Creation d'un imageDialog ==========================

        imgDialog = PlotDialog(edit = False,
                                toolbar = True,
                                options = PlotOptions(show_contrast = False, type = "image")
                                )

        imgDialog.setObjectName("multiDatasetExplorerImage")  # pour le retrouver plus tard

        # =======================================================================



        # =========== ajout d'un item curve pour localisation de points =========

        imagePlot = imgDialog.get_plot()

        curve = make.curve([], [],
                           linestyle = "NoPen",
                           marker = "o",
                           markersize = self.gui.main.marker_size,
                           markerfacecolor = "red",
                           markeredgecolor = "black",
                           title = "selected point(s)")

        imagePlot.add_item(curve)

        # =======================================================================


        # ==============Ajout de tools===========================================

        selectTool = imgDialog.manager.add_tool(SelectPointTool,
                                                title = "Selection",
                                                on_active_item = False,
                                                mode = "create",
                                                end_callback = self.pickerSelectionChanged_inMultiDatasetExplorer)

        selectTool.activate()

        freeFormTool = imgDialog.manager.add_tool(FreeFormTool,
                                                  title = "Selection",
                                                  handle_final_shape_cb = self.freeFormSelectionChanged_inMultiDatasetExplorer)

        # =====================================================================

        # self.multiDatasetExplorerTab["curve_selected_points"] = curve

        multiDatasetExplorerTab["imageWidget"] = imgDialog

        # conteneur pour les references des plots images

        multiDatasetExplorerTab["imageItems"] = dict()

        # =======================================================================
        #                           Partie Gauche
        # =======================================================================





        # ======================================================================
        #      Preparation de la Scroll Area contenant les plots
        # ======================================================================

        # Le layout du scrollWidget

        scroll_layout = QtWidgets.QGridLayout()

        # le widget qui contiendra la scrollArea

        scroll_widget = QtWidgets.QWidget()

        scroll_widget.setLayout(scroll_layout)

        # la scrollArea

        scroll_area = QtWidgets.QScrollArea()

        scroll_area.setWidgetResizable(True)

        scroll_area.setWidget(scroll_widget)

        scroll_area.setStyleSheet("QScrollArea {background-color:white;}");

        # ======================================================================
        #      fin Scroll Area
        # ======================================================================
        # conteneur pour les references des plots curves
        multiDatasetExplorerTab["curveItems"] = dict()
        multiDatasetExplorerTab["SpectrumsContainerLayout"] = scroll_layout

        self.multiDatasetExplorerTab = multiDatasetExplorerTab

        # =======================================================================



        # =======================================================================
        #                        Connections
        # =======================================================================

        p.slider_probeOverlapAlpha.valueChanged.connect(self.updateProbesShapesAlpha_inMultiDatasetExplorer)

        p.slider_overlapThreshold.valueChanged.connect(self.updateProbesShapes_inMultiDatasetExplorer)

        p.slider_probeOverlapAlpha.valueChanged.connect(
            partial(self.updateRepresentationsDisplay_inMultiDatasetExplorer, do_autoscale=False))  # temporaire

        p.slider_refsAlpha.valueChanged.connect(self.updateSelectedRepresentationAlpha_inMultiDatasetExplorer)

        p.pushButton_processOverlap.clicked.connect(self.processCompleteOverlap_inMultiDatasetExplorer)

        # p.list_available_datasets.setMouseTracking(True)

        p.list_available_datasets.installEventFilter(self)

        p.button_CreateDatasetFromOverlapMap.clicked.connect(self.createDatasetFromOverlapMap_inMultiDatasetExplorer)

        # ================== Ajout au Layout ====================================

        p.multiViewerLayout.addWidget(imgDialog, 0, 0)
        p.multiViewerLayout.addWidget(scroll_area, 0, 1)

        self.gui.main.save_widget_ref(imgDialog)

        # =======================================================================

    def eventFilter(self, source, event):
        """
        Pour gerer les events non connectable comme DropEvent de QListWidget
        on se connect à cette methode par object.installEventFilter(self)
        http://stackoverflow.com/questions/13788452/pyqt-how-to-handle-event-without-inheritance
        """
        p = self.gui.panel

        # print "source, event:",source, event.type()

        #        if (event.type() == QtCore.QEvent.MouseMove and source is p.list_available_datasets):
        #            pos = event.pos()
        #            print('mouse move: (%d, %d)' % (pos.x(), pos.y()))



        if (event.type() == QtCore.QEvent.ChildRemoved and source is p.list_available_datasets):
            self.updateRepresentationsZOrder_inMultiDatasetExplorer()

        return QtWidgets.QWidget.eventFilter(self, source, event)

    def processCompleteOverlap_inMultiDatasetExplorer(self):

        print("processCompleteOverlap_inMultiDatasetExplorer")

        #=======================================================================
        # TODO: test à factoriser avec fit
        # ======================================================================

        threadRunning = self.isOverlapThreadRunning()

        print("threadRunning:", threadRunning)

        cancel = False

        if threadRunning:
            cancel = self.bl.threading.askForProcessThreadCanceling()

        else:
            self.bl.threading.setProcessingThreadFlag(self.bl.threading.states.RESET)

        if cancel:
            mc_logging.debug("user cancel overlap processing request")

            return

        # ======================================================================

        self.overlapRunning = True

        myThread = Thread(target = self.processCompleteOverlap_inMultiDatasetExplorer_Thread, args=())
        myThread.daemon = True
        myThread.start()

    #TODO : A mettre dans la bl
    def processCompleteOverlap_inMultiDatasetExplorer_Thread(self):

        """
        spatial_ref_ds_name: jeux de donnée servant de reference spatial (celui sur lequel sont callés les autres ds)
        data_space_ref_ds_name: jeux de donnée de reference pour lequel on veux une correspondance des pixels des autres ds
        on utilisait avant "bigger_ds"
        """
        stop_event = self.bl.threading.processingThreadStopEvent

        spatial_ref_ds_name = self.getReferenceDatasetName_inMultiDatasetExplorer()

        dataspace_ref_ds_name = self.mcData.datasets.currentDatasetName

        dss_selected = self.getSelectedDatasets_inMultiDatasetExplorer()

        #bigger_ds = self.bl.shapes.getDatasetNameWithBiggerProbeSize(dss_selected, spatial_ref_ds_name)

        other_ds = [n for n in dss_selected if n != dataspace_ref_ds_name]

        ds = self.mcData.datasets.getDataset(dataspace_ref_ds_name)

        points_to_process = len(other_ds) * ds["size"]

        for j, ds_name in enumerate(other_ds):

            if ds_name == dataspace_ref_ds_name: continue

            overlap_map = self.bl.shapes.getOverlapMap(ds_name, dataspace_ref_ds_name)

            for i in range(ds["size"]):

                if stop_event.is_set(): return

                spectrum_index_dataspace_ref_ds = i

                dataspace_ref_ds_shape = self.bl.shapes.getShapePointsFromSpectrumIndex(dataspace_ref_ds_name,
                                                                                        spectrum_index_dataspace_ref_ds,
                                                                                        output_space = spatial_ref_ds_name)

                # la shape est dans l'espace de ref_ds_name
                spectrum_indexes, ratios, total_ratio = self.bl.shapes.getIndexesInsideShape(ds_name,
                                                                                             dataspace_ref_ds_shape,
                                                                                             spatial_ref_ds_name,
                                                                                             callback_progress = None)

                # ==============================================================
                #  on enregistre pour ne pas à avoir à recalculer
                #  les entrées sont serialisées
                # ==============================================================

                spectrum_indexes = list(map(str, spectrum_indexes))

                ratios = list(map(str, ratios))

                overlap_map["indexes_inside"][spectrum_index_dataspace_ref_ds] = ",".join(spectrum_indexes)

                overlap_map["indexes_inside_ratios"][spectrum_index_dataspace_ref_ds] = ",".join(ratios)

                overlap_map["overlap_ratio"][spectrum_index_dataspace_ref_ds] = total_ratio

                progress = 100. * (i + j * ds["size"]) / points_to_process

                self.gui.main.displayProgressBar(progress)

        self.gui.main.resetProgressBar()

        mc_logging.info("overlap processing done!")

        self.overlapRunning = False

        self.bl.threading.setProcessingThreadFlag(self.bl.threading.states.FINISHED)

    def updateDatasetDisplayParameters_inMultiDatasetExplorer(self):

        """
        Mise a jour des ordres des representation, image opacity etc...
        TODO: enregistrer les parametres dans le projets pour qu'ils soient recharges
        """

        mc_logging.debug("INSIDE updateDatasetDisplayParameters_inMultiDatasetExplorer")

        p = self.gui.panel

        tab = self.multiDatasetExplorerTab

        lad = p.list_available_datasets

        selected_ds_name = self.getSelectedDatasetName_inMultiDatasetExplorer()

        print("selected_ds_name:", selected_ds_name)

        opacity = tab.get("display", {}).get(selected_ds_name, {}).get("opacity", 255)

        z_order = tab.get("display", {}).get(selected_ds_name, {}).get("z_order", None)

        p.slider_refsAlpha.setValue(opacity)

    def getSelectedDatasetName_inMultiDatasetExplorer(self):

        p = self.gui.panel

        lad = p.list_available_datasets

        if lad.currentItem():

            selected_ds_name = str(lad.currentItem().text())

            return selected_ds_name

        else:
            return None

    def updateSelectedRepresentationAlpha_inMultiDatasetExplorer(self):

        # print "inside updateSelectedRepresentationAlpha_inMultiDatasetExplorer"

        p = self.gui.panel

        tab = self.multiDatasetExplorerTab

        selected_ds_name = self.getSelectedDatasetName_inMultiDatasetExplorer()

        imageItems = self.getMultiDatasetExplorerImageItems()

        plot = self.getMultiDatasetExplorerImagePlot()

        opacity = p.slider_refsAlpha.value()

        # on enregistre la valeur pour plus tard

        # TODO, notation tres moche

        tab.setdefault("display", {}).setdefault(selected_ds_name, {})["opacity"] = opacity

        alpha_mask = tab.get("display", {}).get(selected_ds_name, {}).get("alpha_mask", None)

        for repr_id, imageItem in imageItems.items():

            ds_name, repr_family, repr_name = self.getInfosFromReprId(repr_id)

            if ds_name == selected_ds_name:

                # pour ne pas changer l'opacity a 255 des "borders" d'une image warped

                if alpha_mask is not None:
                    imageItem.orig_data[~alpha_mask, 3] = opacity

                else:
                    imageItem.orig_data[..., 3] = opacity

                #                imageItem.imageparam.alpha_mask = True
                #                imageItem.imageparam.alpha = opacity

                imageItem.recompute_alpha_channel()

        plot.replot()

    def updateRepresentationsZOrder_inMultiDatasetExplorer(self, replot=True):

        print("inside updateRepresentationsZOrder_inMultiDatasetExplorer")

        p = self.gui.panel

        tab = self.multiDatasetExplorerTab

        selected_ds_name = self.getSelectedDatasetName_inMultiDatasetExplorer()

        imageItems = self.getMultiDatasetExplorerImageItems()

        plot = self.getMultiDatasetExplorerImagePlot()

        # =====================================================================
        #                         Ordre souhaité
        # =====================================================================

        ds_names_ordered = []

        for index in range(p.list_available_datasets.count()):
            ds_name = str(p.list_available_datasets.item(index).text())
            ds_names_ordered.append(ds_name)

        print("New representations Order:", ds_names_ordered)

        # =====================================================================
        #                    on supprime tous les precedents items
        # =====================================================================
        for key in imageItems:

            try:
                plot.del_item(imageItems[key])

            except ValueError as e:
                print("can't delete object:", end=' ')
                print(e)

        # =====================================================================
        #                  On les reinserre dans l'ordre
        # =====================================================================

        for ds_name in reversed(ds_names_ordered):

            for repr_id, imageItem in imageItems.items():

                ds_name_non_ordered, repr_family, repr_name = self.getInfosFromReprId(repr_id)

                if ds_name == ds_name_non_ordered:
                    plot.add_item(imageItem)

        if replot:
            plot.replot()

    # @my_pyqtSlot(bool)
    def updateRepresentationsDisplay_inMultiDatasetExplorer(self, do_autoscale=True):
        """
        Mise a jour des xdata,ydata et data de toutes les images
        """

        print("updateRepresentationsDisplay_inMultiDatasetExplorer")

        # mc_logging.debug("updateRepresentationsDisplay_inMultiDatasetExplorer")

        p = self.gui.panel

        self.plot = self.getMultiDatasetExplorerImagePlot()
        plot = self.plot

        imageItems = self.getMultiDatasetExplorerImageItems()

        ref_ds_name = self.getReferenceDatasetName_inMultiDatasetExplorer()

        tab = self.multiDatasetExplorerTab

        # ======================================================================
        # On supprime les representations si les datasets.py ont été supprimés
        # ======================================================================
        for repr_id in imageItems:

            ds_name, repr_family, repr_name = self.getInfosFromReprId(repr_id)

            if ds_name not in list(self.mcData.datasets.names()):
                self.removeRepresentation_inMultiDatasetExplorer(repr_id)

        # ======================================================================
        # Mise à jour des positions des representation et du warping eventuel
        # ======================================================================
        imageItems = self.getMultiDatasetExplorerImageItems()

        for repr_id, imageItem in imageItems.items():

            ds_name, repr_family, repr_name = self.getInfosFromReprId(repr_id)

            transformationMatrix = self.bl.coordinates.getTransformationMatrix(ds_name, ref_ds_name)

            opacity = tab.get("display", {}).get(ds_name, {}).get("opacity", 255)

            #            if ds_name == ref_ds_name:
            #                opacity = 255
            #            else:
            #                opacity = p.slider_refsAlpha.value()


            ds = self.mcData.datasets.getDataset(ds_name)
            if not ds:
                #TODO: on ne devrait pas arrivé à ce cas de figure, il faut supprimer les repr à la suppression du ds
                #TODO: grace à l'appel de self.getMultiDatasetExplorerImageItems(), le probleme doit etre reglé
                print("TODO: WARNING '{}' doesn't exists anymore, repr should have been deleted".format(ds_name))
                continue

            xdata = ds["x_range"]
            ydata = ds["y_range"]

            tl = np.array([xdata[0], ydata[0], 1])
            br = np.array([xdata[1], ydata[1], 1])

            tl_trans = transformationMatrix.dot(tl)
            br_trans = transformationMatrix.dot(br)

            xdata_transf = [tl_trans[0] / tl_trans[2], br_trans[0] / br_trans[2]]
            ydata_transf = [tl_trans[1] / tl_trans[2], br_trans[1] / br_trans[2]]

            print("   ")
            print("For %s in %s space" % (ds_name, ref_ds_name))
            print("repr_id", repr_id)
            print("xdata:", xdata, "  ->  ", xdata_transf)
            print("ydata:", ydata, "  ->  ", ydata_transf)
            print("   ")

            image_data = self.bl.representations.getRepresentationImage(ds_name,
                                                     repr_family,
                                                     repr_name,
                                                     version = "rgb")

            # image_data = ds["representations"][repr_family][repr_name]["image"]



            # ==================================================================
            # Warping image
            # ==================================================================

            # on prend comme resolution un carré de max (res_x,res_y) pour avoir
            # une image correct même en cas de rotation à 90° de l'image init
            # limite de 2000px pour ne pas degrader trop les performances

            # TODO: mettre ces limites ailleurs
            limit_res_x = 2000
            limit_res_y = 2000

            w, h = image_data.shape[1], image_data.shape[0]

            #            print "np.diag(np.ones(3):",np.diag(np.ones(3))
            #
            #            print "transformationMatrix:",transformationMatrix
            #
            #            print "np.all()", np.all(transformationMatrix == np.diag(np.ones(3)))

            if np.all(transformationMatrix == np.diag(np.ones(3))):

                bbox_res_x = min(limit_res_x, w)
                bbox_res_y = min(limit_res_y, h)

            else:

                bbox_res_x = min(limit_res_x, max(w, h))
                bbox_res_y = min(limit_res_y, max(w, h))

            if bbox_res_x > limit_res_x or bbox_res_y > limit_res_y:

                dsize = (limit_res_x, limit_res_y)

                print("Image output too big (%d,%d)," % (bbox_res_x, bbox_res_y), end=' ')
                print("displaying at (%d,%d)" % (limit_res_x, limit_res_y))

            else:
                dsize = (bbox_res_x, bbox_res_y)

            # =========== si on veux mettre en evidence la bounding_box============

            show_bounding_border = False  # a True pour debug

            if show_bounding_border:
                borderValue = (0, 255, 0, opacity)

            else:
                borderValue = (0, 0, 255, 0)

            # print "borderValue",borderValue


            tmpImg = np.zeros((h, w, 4), dtype = np.uint8)

            tmpImg[..., 0:3] = image_data[..., 0:3]

            # On change l'opacité pour la superposition

            tmpImg[..., 3] = opacity

            #            print "image_data dtype:",image_data.dtype
            #            print "image_data shape:",image_data.shape
            #            print "dsize:",dsize
            #            print "transformationMatrix dtype:",transformationMatrix.dtype
            #            print "transformationMatrix :",transformationMatrix


            warpingTransformationMatrix, xmin_bbox, xmax_bbox, ymin_bbox, ymax_bbox = self.bl.coordinates.getWarpingTransformationMatrix(ds_name, ref_ds_name)
            # TODO: ça bug quand meme en cas d'exception

            try:

                # TODO: probleme ici avec le warping de original1 en ds de ref
                warped_image = cv2.warpPerspective(tmpImg,
                                                   warpingTransformationMatrix,
                                                   dsize = dsize,
                                                   borderValue = borderValue)

                # warped_image =  tmpImg
                # on enregistre un masque pour ne pas toucher au zone de border lors
                # du recalcul du alpha de l'image

            except Exception as e:

                print("ERROR during image warping")
                print(e)
                mc_logging.error("failed to process warpPerspective")
                return

            alpha_mask = warped_image[..., 3] == borderValue[3]  # point ayant le alpha de la border (0)

            tab.setdefault("display", {}).setdefault(ds_name, {})["alpha_mask"] = alpha_mask

            # ==================================================================
            #
            # ==================================================================

            imageItem.set_xdata(xmin_bbox, xmax_bbox)
            imageItem.set_ydata(ymin_bbox, ymax_bbox)

            print("xmin_bbox, xmax_bbox:", xmin_bbox, xmax_bbox)
            print("ymin_bbox, ymax_bbox:", ymin_bbox, ymax_bbox)

            # les xydata ne sont pas actualisées si pas de set_data APRES
            #            imageItem.set_xdata(xdata_transf[0], xdata_transf[1])
            #            imageItem.set_ydata(ydata_transf[0], ydata_transf[1])

            imageItem.set_data(warped_image)  # imageItem.set_data(image_data)

        self.updateRepresentationsZOrder_inMultiDatasetExplorer(replot=False)

        replot = True

        if do_autoscale:
            plot.do_autoscale()

        if replot:
            print("reploting")

            plot.replot()

        print("done! updateRepresentationsDisplay_inMultiDatasetExplorer")

    def getTransformedRepresentation_inMultiDatasetExplorer(self, ds_name, ref_ds_name):

        """
        transformation de l'espace B à l'espace A
        """

        dsA = self.mcData.datasets.getDataset(ref_ds_name)
        dsB = self.mcData.datasets.getDataset(ds_name)

        # coordonnées coins images (rectangle) dans le referenciel de B

        xmin_B, xmax_B = dsB["x_range"]
        ymin_B, ymax_B = dsB["y_range"]

        # Les coordonnées de ces points dans A permettront de definir celle de

        # la bounding-box de la projection de B dans A

        tlB = [xmin_B, ymin_B]
        trB = [xmax_B, ymin_B]
        brB = [xmax_B, ymax_B]
        blB = [xmin_B, ymax_B]

        # Transformation Matrix

        transformationMatrix = self.bl.coordinates.getTransformationMatrix(ds_name, ref_ds_name)

        # coordonnées coins images dans A forment un quadrilatère

        cornersB = np.float32([tlB, trB, brB, blB]).reshape(-1, 1, 2)

        cornersA = cv2.perspectiveTransform(cornersB, transformationMatrix)

        tlA = cornersA[0][0]
        trA = cornersA[1][0]
        brA = cornersA[2][0]
        blA = cornersA[3][0]

        # on cherche les coordonnées de la "bounding-box" (bbox) de ce quadrilatère
        xmin_bbox, xmax_bbox = min([tlA[0], blA[0]]), max([trA[0], brA[0]])
        ymin_bbox, ymax_bbox = min([tlA[1], trA[1]]), max([blA[1], brA[1]])

        # print "corners base A:",xmin_bbox,xmax_bbox,ymin_bbox,ymax_bbox

        xmin_A, xmax_A = dsA["x_range"]
        ymin_A, ymax_A = dsA["y_range"]

        # translation origine

        dx_ba = - (xmin_bbox - xmin_A)

        dy_ba = - (ymin_bbox - ymin_A)

        return image_data, x_range, y_range

    def addRepresentation_inMultiDatasetExplorer(self, repr_id, z_index=-1):
        """
        Cette methode ajoute un item image dans multidatasetExplorer
        """

        p = self.gui.panel

        plot = self.getMultiDatasetExplorerImagePlot()

        imageItems = self.getMultiDatasetExplorerImageItems()

        ds_name, repr_family, repr_name = self.getInfosFromReprId(repr_id)

        ref_ds_name = self.getReferenceDatasetName_inMultiDatasetExplorer()

        image_data = self.bl.representations.getRepresentationImage(ds_name, repr_family, repr_name, version="rgb")

        print("image_data.shape:", image_data.shape)

        mc_logging.debug("adding '%s' from '%s' in MultiDatasetExplorer at index %d" % (repr_name, ds_name, z_index))

        print("ref_ds_name is", ref_ds_name)

        # ===============positionnement=========================================

        # ======================================================================

        #        transformationMatrix = self.bl.coordinates.getTransformationMatrix(ds_name,ref_ds_name)
        #
        #        tl_coo = transformationMatrix.dot(np.array([ds["x_range"][0],ds["y_range"][0],1]).T)
        #        br_coo = transformationMatrix.dot(np.array([ds["x_range"][1],ds["y_range"][1],1]).T)
        #
        #        xmin = tl_coo[0]/tl_coo[2]
        #        xmax = br_coo[0]/tl_coo[2]
        #        ymin = tl_coo[1]/tl_coo[2]
        #        ymax = br_coo[1]/tl_coo[2]
        #
        #
        #        print "xmin,xmin",xmin,xmax
        #        print "ymin,xmin",ymin,ymax


        # ======================================================================

        # ======================================================================

        if repr_id not in imageItems:
            # Utilisation d'un "imageParam" nescessaire à l'activation du mode alpha

            imageParams = ImageParam()

            imageParams.alpha_mask = True

            # print "imageParams.interpolation", imageParams.interpolation


            repr_image = RGBImageItem(image_data, imageParams)

            repr_image.setTitle(repr_id)

            #            repr_image = make.rgbimage(image_data,
            #                                       title = repr_id,
            #                                       alpha_mask = True,
            ##                                      xdata = [xmin, xmax],
            ##                                      ydata = [ymin, ymax],
            #                                       interpolation = 'nearest')

            plot.add_item(repr_image)


        #        else:
        #            imageItems[repr_id].set_data(image_data)
        #            imageItems[repr_id].set_xdata(xmin, xmax)
        #            imageItems[repr_id].set_ydata(ymin, ymax)

        self.gui.main.signal_updateRepresentationsDisplay_inMultiDatasetExplorer.emit(True)
        # plot.replot()

    def removeRepresentation_inMultiDatasetExplorer(self, repr_id=None, ds_name=None):

        plot = self.getMultiDatasetExplorerImagePlot()

        imageItems = self.getMultiDatasetExplorerImageItems()

        assert (repr_id is not None or ds_name is not None)

        for key in imageItems:

            del_key = False

            # Suppression d'un plot à partir du ds_name uniquement

            if ds_name and key.split(" -")[0] == ds_name: del_key = True

            # Suppression d'un plot en particulier grace a son repr_id

            if repr_id and key == repr_id: del_key = True

            if del_key:

                try:
                    mc_logging.debug("removing '%s' repr image in MultiDatasetExplorer" % (key))
                    plot.del_item(imageItems[key])

                except ValueError as e:

                    print("can't delete object:", end=' ')
                    print(e)

        plot.replot()

    def createDatasetFromOverlapMap_inMultiDatasetExplorer(self):

        p = self.gui.panel

        print("inside createDatasetFromOverlapMap_inMultiDatasetExplorer")

        d = uic.loadUi("assets//ui_files//dataset_creation_from_overlap.ui")

        d.setWindowTitle("Please select data to use for dataset creation")

        # ==================================================================
        #    On remplit la listBox avec les representations disponibles
        # ==================================================================
        ds_names = self.bl.relationships.getAvailableRelationships()

        datasets = self.bl.mcData.datasets

        # ==================================================================
        #    Preparation Layout
        # ==================================================================

        # Le layout du scrollWidget

        scroll_layout = QtWidgets.QHBoxLayout()

        # le widget qui contiendra la scrollArea

        scroll_widget = QtWidgets.QWidget()

        scroll_widget.setLayout(scroll_layout)

        # la scrollArea

        scroll_area = d.scrollArea

        scroll_area.setWidgetResizable(True)

        scroll_area.setWidget(scroll_widget)

        scroll_area.setStyleSheet("QScrollArea {background-color:white;}");

        # ==================================================================
        #
        # ==================================================================

        repr_lists_refs = {}

        for i, ds_name in enumerate(ds_names):
            # ==================================================================
            #    Representation Disponibles
            # ==================================================================

            list_reprs = ["whole data"]

            list_reprs += ["%s - %s" % (family, repr_name) for family, repr_name in
                           self.bl.representations.getAvailableRepresentations(ds_name)]

            # ==================================================================
            #    Widget
            # ==================================================================

            name_widget = QtWidgets.QLabel(ds_name)

            repr_list_widget = QtWidgets.QListWidget()

            name_widget.setFont(QFont("Times", 12, QFont.Bold))

            name_widget.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)

            repr_list_widget.addItems(list_reprs)

            repr_list_widget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

            repr_list_widget.setStyleSheet(""" QListWidget:item:selected:active {
                                                 background: #87cefa;
                                                 }
                                                QListWidget:item:selected:!active {
                                                     background: gray;
                                                }
                                                QListWidget:item:selected:disabled {
                                                     background: gray;
                                                }
                                                QListWidget:item:selected:!disabled {
                                                     background: #87cefa;
                                                }
                                            """)

            widget = QtWidgets.QWidget()

            widget.setFixedHeight(250)
            widget.setFixedWidth(300)

            widget_layout = QtWidgets.QVBoxLayout()

            widget.setLayout(widget_layout)

            widget_layout.addWidget(name_widget)
            widget_layout.addWidget(repr_list_widget)
            scroll_layout.addWidget(widget)

            repr_lists_refs[ds_name] = repr_list_widget

            # ==================================================================
            #
            # ==================================================================

        ok = d.exec_()

        # =====================================================================
        #               On recupere les donnees de la gui
        # =====================================================================

        if ok:
            min_overlap = float(d.spinbox_minOverlap.value())

            name = str(d.datasetName.text())

            print("min_overlap:", min_overlap)
            print("name:", name)

            # =====================================================================
            #               conteneur final
            # =====================================================================
            channels_counter = 0

            for ds_name in ds_names:

                ds = datasets.getDataset(ds_name)

                repr_list = repr_lists_refs[ds_name]

                selected_reprs = [str(repr_list.item(i.row()).text()) for i in repr_list.selectedIndexes()]

                print("selected representations for %s:" % (ds_name,))
                print(selected_reprs)

                if 'whole data' in selected_reprs:
                    channels_counter += len(ds["W"])
                    print("whole data selected")

                else:
                    channels_counter += len(selected_reprs)

            print("channels count for new dataset:", channels_counter)



            # TODO, lancer dans un thread avec callback d'avancement

            relationship_name = "%s,%s" % (ds_names[0],ds_names[1])
            relationship = self.mcData.relationships.relationships_dict[relationship_name]

            spectrums_of_ds2_overlapping_spectrums_of_ds1 = relationship["overlap_map"]["indexes_inside"]
            overlap_ratios = relationship["overlap_map"]["indexes_inside_ratios"]

            for i in range(ds["size"]):
                summed_spectrum = np.zeros((1, len(ds["W"])))

                spectrums_of_ds2_overlapping_spectrums_of_ds1[i]
                #
                # for j in range(overlapping_indexes_in_ds2):
                #     summed_spectrum += 0

    # ==========================================================================





    # ==========================================================================
    #                 Methodes realitives à la probe
    # ==========================================================================
    def changeProbeParameters(self):
        """
        callback method called when changing probe shape/size/position in GUI
        """
        p = self.gui.panel

        ds = self.mcData.datasets.getDataset()

        ds["probe"]["shape"] = p.combo_probeShape.currentText()
        ds["probe"]["dx"] = float(p.infoProbeDx.text())
        ds["probe"]["dy"] = float(p.infoProbeDy.text())
        ds["probe"]["origin"] = p.combo_probeOrigin.currentText()

        self.updateProbesShapes_inMultiDatasetExplorer()

        mc_logging.debug("Probe parameters updated")

    def getImageItem_inMultiDatasetExplorer(self):
        tab = self.multiDatasetExplorerTab
        return tab["imageWidget"]

    def getImagePlot_inMultiDatasetExplorer(self):
        img_item = self.getImageItem_inMultiDatasetExplorer()
        return img_item.get_plot()

    def updateProbesShapesAlpha_inMultiDatasetExplorer(self, replot = True):
        """
        callback method called when requested alpha value change
        """

        p = self.gui.panel

        alpha = p.slider_probeOverlapAlpha.value()

        plot = self.getImagePlot_inMultiDatasetExplorer()

        items = [item for item in plot.get_items() if "Probe sp." in item.title().text()]

        for shape in items:

            for brush in (shape.brush, shape.sel_brush, shape.pen, shape.sel_pen):
                c = brush.color()
                c.setAlpha(alpha)
                brush.setColor(c)

        if replot:
            plot.replot()
            self.gui.main.signal_updatePlots_inMultiDatasetExplorer.emit()

    def updateProbesShapes_inMultiDatasetExplorer(self):
        """
        update probes shapes around selected spectrums in MultiDatasetExplorer
        on appelle cette methode quand on insert une nouvelle representation
        pour que les shapes soient toujours au premier plan
        """

        p = self.gui.panel

        lad = p.list_available_datasets  # alias

        tab = self.multiDatasetExplorerTab

        autosum = p.checkBox_autoSumDatas.isChecked()

        ds_names = self.getSelectedDatasets_inMultiDatasetExplorer()

        overlap_threshold = (p.slider_overlapThreshold.value()) / 100.

        ref_ds_name = self.getReferenceDatasetName_inMultiDatasetExplorer()

        ds_selected = self.getSelectedDatasets_inMultiDatasetExplorer()

        if not ds_names:
            print("no dataset selected")

            return

        plot = self.getImagePlot_inMultiDatasetExplorer()

        # ======================================================================
        # On commence par supprimer les shapes precedentes
        # ======================================================================

        items = [item for item in plot.get_items() if "Probe sp." in item.title().text()]

        plot.del_items(items)

        # ======================================================================
        dataX, dataY = tab.get("clickCoordinates", (0, 0))

        bigger_ds = self.bl.shapes.getDatasetNameWithBiggerProbeSize(ds_selected, ref_ds_name)

        # ======================================================================
        # On commence par la shape du plus gros
        # ======================================================================

        spectrum_index_bigger_ds = self.bl.coordinates.getSpectrumIndexFromXY(bigger_ds, dataX, dataY, xy_space = ref_ds_name)

        #        print "getSpectrumIndexFromXY of bigger_ds:",spectrum_index
        #        print "bigger_ds name:", bigger_ds
        #        print "dataX, dataY:", dataX, dataY



        # on definit l es valeurs des differentes couleurs

        bigger_color_rgb   = [238, 130, 238]
        good_overlap_color = [0,   255,   0]
        bad_overlap_color  = [255,  0,    0]

        if spectrum_index_bigger_ds or spectrum_index_bigger_ds == 0:

            print("bigger index:", spectrum_index_bigger_ds)

            bigger_shape = self.bl.shapes.getShapePointsFromSpectrumIndex(bigger_ds,
                                                                          spectrum_index_bigger_ds,
                                                                          output_space = ref_ds_name)

            inside_color = bigger_color_rgb

            # TODO, mettre color en echelle jet en fonction de r_coeff (0 à 1)

            self.addShapeInPlot(plot, bigger_shape, bigger_color_rgb,
                                 "Probe sp. %d (%s)" % (spectrum_index_bigger_ds, bigger_ds), replot = False)

            # ======================================================================
            # Puis les shapes des autres jeux de données
            # ======================================================================

            other_ds = [n for n in ds_names if n != bigger_ds]

            # print "other_ds:",other_ds

            # Chargement de la map des overlaps pour mise à jour des infos ou

            # creation si n'existe pas

            for ds_name in other_ds:
                # ==============================================================
                # si on ne veux que le plus proche dans chaque dataset
                # ==============================================================

                if not autosum:

                    spectrum_index = self.bl.coordinates.getSpectrumIndexFromXY(ds_name,
                                                                                dataX,
                                                                                dataY,
                                                                                xy_space = ref_ds_name)

                    # TODO: pas propre

                    if not spectrum_index and spectrum_index != 0:
                        continue

                    probe_shape = self.bl.shapes.getShapePointsFromSpectrumIndex(ds_name,
                                                                                 spectrum_index,
                                                                                 output_space = ref_ds_name)

                    ratio = self.bl.shapes.getOverlapRatio(bigger_shape,
                                                           probe_shape,
                                                           ref_ds_name,
                                                           ref_ds_name)

                    spectrum_indexes = [spectrum_index]

                    ratios = [ratio]


                # ==============================================================
                # si on somme tous les pixels qui se recouvrent
                # ==============================================================

                else:

                    # la shape est dans l'espace de ref_ds_name

                    spectrum_indexes, ratios, total_ratio = self.bl.shapes.getIndexesInsideShape(ds_name,
                                                                                                 bigger_shape,
                                                                                                 ref_ds_name)

                    # print "spectrum_indexes inside bigger shape for '%s'" % (ds_name), spectrum_indexes


                    # ==============================================================
                    #  on enregistre pour ne pas à avoir à recalculer
                    # ==============================================================

                    print("overlapMap requested spectrum_index:", spectrum_index_bigger_ds)

                    overlap_map = self.bl.shapes.getOverlapMap(ds_name, bigger_ds)

                    if overlap_map:

                        print("overlapMap size:", len(overlap_map))

                        # La taille de overlap_map est definit par celle de biger_ds

                        overlap_map["indexes_inside"][spectrum_index_bigger_ds] = ",".join(map(str, spectrum_indexes))

                        overlap_map["indexes_inside_ratios"][spectrum_index_bigger_ds] = ",".join(map(str, ratios))

                        overlap_map["overlap_ratio"][spectrum_index_bigger_ds] = total_ratio

                        # ==============================================================

                    else:

                        print("no overlap_map available")

                # ==============================================================
                # On trace toutes les shapes avec codes couleurs
                # ==============================================================

                for i, spectrum_index in enumerate(spectrum_indexes):

                    if ratios[i] >= overlap_threshold:
                        inside_color = good_overlap_color

                    else:
                        inside_color = bad_overlap_color

                    probe_shape = self.bl.shapes.getShapePointsFromSpectrumIndex(ds_name,
                                                                                 spectrum_index,
                                                                                 output_space = ref_ds_name)

                    self.addShapeInPlot(plot,
                                        probe_shape,
                                        inside_color,
                                         "Probe sp. %d (%s)" % (spectrum_index, ds_name),
                                        replot = False)

                    self.gui.main.displayProgressBar(100.0 * i / len(spectrum_indexes))

                self.gui.main.resetProgressBar()

            plot.replot()

    def addShapeInPlot(self, plot, shape_points, inside_color_rvb, title ="Probe sp. X (xxx)", outside_color_rvb = None,
                       replot = True):

        """
        Methode ajoutant une shape a un plot d'apres une liste de coordonnées de points
        """

        # on creer une forme PolygonShape guiQwt pour mettre sur le plot

        shape = PolygonShape(shape_points)

        irvb = inside_color_rvb

        orvb = outside_color_rvb

        # ==================================================================
        #               Couleur de la shape
        # ==================================================================

        r_coeff = np.random.rand()

        inside_color = QtGui.QColor(irvb[0], irvb[1], irvb[2], 255)

        shape.brush = QtGui.QBrush(inside_color)

        shape.sel_brush = QtGui.QBrush(inside_color)

        shape.set_movable(False)

        shape.set_private(True)  # Affichage ou non dans la liste des objets

        shape.setTitle(title)

        # ==================================================================
        plot.add_item(shape)

        self.updateProbesShapesAlpha_inMultiDatasetExplorer(replot=False)

        if replot: plot.replot()

    # ==========================================================================


    def getInfosFromReprId(self, repr_id):

        """
        Convenient Method to retrieve ds_name, repr_family and repr_name from
        it's "id"
        "%s - %s (%s)" % (ds_name, repr_name, repr_family)
        return ds_name, repr_family, repr_name
        """

        repr_id = str(repr_id)

        ds_name = repr_id.split(" - ")[0]

        repr_name   = repr_id.split(" - ")[1].split(" (")[0]
        repr_family = repr_id.split(" - ")[1].split(" (")[1].split(")")[0]

        return ds_name, repr_family, repr_name

    # =====================================================================
    #          Partie specifique au multidataset viewer
    # =====================================================================
    # @my_pyqtSlot()
    def updateLinkedDatasetsList_inMultiDatasetExplorer(self):

        """
        Methode appellée lorseque de nouvelles representations ou datasets.py sont disponibles
        Mise a jour des listes
        """

        p = self.gui.panel

        mc_logging.debug("inside updateLinkedDatasetsList_inMultiDatasetExplorer")

        # imagePlot = self.getMultiDatasetExplorerImagePlot()


        # ======================================================================
        # Available datasets.py
        # ======================================================================

        ds_names = self.bl.relationships.getAvailableRelationships()

        lad_list = p.list_available_datasets  # alias

        if not ds_names:
            lad_list.clear()

            self.updateSpectrumViewers_inMultiDatasetExplorer()

            return

        # on garde les noms des items selected pour les remettre ensuite

        old_selected = [item.text() for item in lad_list.selectedItems()]

        print("old_selected:", old_selected)

        lad_list.clear()
        lad_list.addItems(ds_names)

        for i in range(lad_list.count()):

            if lad_list.item(i).text() in old_selected:
                lad_list.item(i).setSelected(True)

        # ======================================================================
        # Available representations
        # ======================================================================

        p.list_available_datasets.contextMenuEvent = self.contextMenuEventDsChoice__inMultiDatasetExplorer

        # ======================================================================
        # Coordinate Reference
        # ======================================================================

        p.combo_referenceDataset.clear()

        p.combo_referenceDataset.addItems(ds_names)

        # ======================================================================
        # Mise en place des callbacks de deplacement des representations et datasets
        # ======================================================================
        p.list_available_datasets.itemClicked.connect(self.updateDatasetDisplayParameters_inMultiDatasetExplorer)

        p.combo_referenceDataset.currentIndexChanged.connect(
            lambda index: self.updateRepresentationsDisplay_inMultiDatasetExplorer())



    def updateSpectrumViewers_inMultiDatasetExplorer(self):

        """
        methode appelée lors de la selection/deselection d'un dataset
        mise à jour de l'affichage des données
        """

        mc_logging.debug("INSIDE updateSpectrumViewers_inMultiDatasetExplorer")

        p = self.gui.panel

        lad = p.list_available_datasets  # alias

        all_items = [lad.item(i) for i in range(lad.count())]

        all_items_names = [str(item.text()) for item in all_items]

        previous_ds_in_multiviewer = self.getDatasetNamesDisplayedInSpectrumsViewers_inMultiDatasetExplorer()

        # print "previous_ds_in_multiviewer:",previous_ds_in_multiviewer
        # print "all_items_names",all_items_names

        all_ds_names = set(previous_ds_in_multiviewer + all_items_names)

        # print "all_ds_names:",all_ds_names


        for ds_name in all_ds_names:
            # On ajoute tout les viewers associés au dataset selectionnés

            if ds_name in all_items_names:

                mc_logging.debug("Dataset '%s' selected" % (ds_name,))
                self.addSpectrumViewer_inMultiDatasetExplorer(ds_name)

            # On supprime tous les autres viewers

            else:
                mc_logging.debug("Dataset '%s' unselected" % (ds_name,))

                self.removeSpectrumViewer_inMultiDatasetExplorer(ds_name)

                # self.emit(SIGNAL("updatePlots_inMultiDatasetExplorer"))



    def pickerSelectionChanged_inMultiDatasetExplorer(self, tool):

        mc_logging.debug("inside pickerSelectionChanged_inMultiDatasetExplorer")

        """
        Methode appelee lorsque l'on clique sur l'image de representation avec l'outil
        selection de point

        On vas seulement enregistrer la coordonnée spatial, le calcul de correspondante
        se fera dans updatePlots_inMultiDatasetExplorer car assez compliqué
        """

        tab = self.multiDatasetExplorerTab

        dataX, dataY = tool.get_coordinates()

        print("pickerSelectionChanged_inMultiDatasetExplorer")

        print("dataX, dataY", dataX, dataY)

        tab["clickCoordinates"] = dataX, dataY

        self.updateProbesShapesAndPlots_inMultiDatasetExplorer()

    def updateProbesShapesAndPlots_inMultiDatasetExplorer(self):

        self.updateProbesShapes_inMultiDatasetExplorer()

        self.gui.main.signal_updatePlots_inMultiDatasetExplorer.emit()

    def freeFormSelectionChanged_inMultiDatasetExplorer(self, shape):

        mc_logging.debug("inside freeFormSelectionChanged_inMultiDatasetExplorer A IMPLEMENTER")

        plot = self.getMultiDatasetExplorerImagePlot()

        plot.del_item(shape)

        plot.replot()

    def getReferenceDatasetName_inMultiDatasetExplorer(self):

        p = self.gui.panel

        return str(p.combo_referenceDataset.currentText())

    def addSpectrumViewer_inMultiDatasetExplorer(self, ds_name, z_index=-1):

        mc_logging.debug("adding spectrum viewer in MultiDatasetExplorer")

        mc_logging.debug("z_index: %d" % (z_index,))

        p = self.gui.panel

        tab = self.multiDatasetExplorerTab

        scroll_layout = tab["SpectrumsContainerLayout"]

        # ======================================================================
        # Creation d'un CurveWidget et ajout au ScrollLayout si n'existe pas deja
        # ======================================================================

        widgetName = 'plotContainer_multiDatasetViewer_%s' % (ds_name,)

        # on cherche avec findChild car le widget peux etre supprimer en decallé

        # par rapport a la reference enregistrée dans le dict

        cw = p.findChild(PlotWidget, name=widgetName)

        if not cw:

            widget = PlotWidget()

            widget.setObjectName(widgetName)

            widget.setFixedHeight(250)

            scroll_layout.addWidget(widget)

            self.gui.main.save_widget_ref(widget)

            tab["curveItems"][ds_name] = widget

            widget.contextMenuEvent = partial(self.addContextMenuForSpectrumViewer_inMultiDatasetExplorer,
                                              ds_name = ds_name, widget = widget)

        else:
            mc_logging.debug("'%s' spectrum viewer already in MultiDatasetExplorer" % (ds_name,))

    def addContextMenuForSpectrumViewer_inMultiDatasetExplorer(self, event, ds_name, widget):

        p = self.gui.panel

        menu = QtWidgets.QMenu(self)

        mc_logging.debug("context menus, right click on %s" % (event,))

        # actions pour chacune des representations de ce dataset

        self.addContextMenuActionsForSpectrumViewer_inMultiDatasetExplorer(menu, ds_name)

        parentPosition = widget.mapToGlobal(QtCore.QPoint(0, 0))

        menu.move(parentPosition + event.pos())

        menu.show()




    def addContextMenuActionsForSpectrumViewer_inMultiDatasetExplorer(self, menu, ds_name):
        """
        create a context menus for each datasetViewer for choosing spectrums displayMode
        """

        for disp_id, disp_name in self.gui.spectrums.getDisplayModes():

            action = QtWidgets.QAction(disp_name, self)

            callback = partial(self.gui.spectrums.setDisplayMode, display_mode = disp_id, ds_name = ds_name)

            action.triggered.connect(callback)

            menu.addAction(action)

        meta_datas_menu = QtWidgets.QMenu('Metadatas', self)

        for metadatas_mode in self.gui.menu.display.metadatasDisplayModes:
            action = QtWidgets.QAction(metadatas_mode, self)

            callback = partial(self.gui.menu.display.setMetadataDisplayedMode, display_mode = metadatas_mode, ds_name = ds_name)

            action.triggered.connect(callback)

            meta_datas_menu.addAction(action)

        menu.addSeparator()

        menu.addMenu(meta_datas_menu)

    def removeSpectrumViewer_inMultiDatasetExplorer(self, ds_name):

        mc_logging.debug("removing spectrum viewer '%s' in MultiDatasetExplorer" % (ds_name,))

        p = self.gui.panel

        tab = self.multiDatasetExplorerTab

        # ==============suppression du widget existant======================

        if ds_name in list(tab["curveItems"].keys()):

            try:

                tab["curveItems"][ds_name].deleteLater()

                del tab["curveItems"][ds_name]

            except ValueError as e:

                print("can't delete object:", end=' ')

                print(e)

        else:

            print("error, %s not in tab['curveItems']" % (ds_name,))

            # ======================================================================

    def getDatasetNamesDisplayedInSpectrumsViewers_inMultiDatasetExplorer(self):

        tab = self.multiDatasetExplorerTab

        return list(tab["curveItems"].keys())

    # @my_pyqtSlot()
    def updatePlots_inMultiDatasetExplorer(self):

        """
        Rafraichissement/creation de curves widget en fonction des datasets.py et
        options selectionnées
        affiche les spectres associé à la selection (click ou groupe) dans les
        differents datasets.py.
        Ici on commence  par associer spatialement les differents spectres
        et à les afficher en fonction du type d'affichage souhaité (clicked, mean group, all_selected...)
        on appelle donc la fonction d'affichage de spectres () avec differents indices
        """

        mc_logging.debug("updating plots in MultiDatasetExplorer")

        # Ne faire l'update ci-dessous que si le tab affiché est le mutidatasetExplorer (gain de temps)
        if self.gui.main.getCurrentTabIndex() != self.gui.main.getTabIndexByName("MultiViewer"): return


        p = self.gui.panel

        tab = self.multiDatasetExplorerTab

        autosum = p.checkBox_autoSumDatas.isChecked()

        ref_ds_name = self.getReferenceDatasetName_inMultiDatasetExplorer()

        overlap_threshold = p.slider_overlapThreshold.value() / 100.

        # plot = tab["imageWidget"].get_plot()



        # coordonnées ecran du point selectionné

        dataX, dataY = tab.get("clickCoordinates", (0, 0))

        # jdd selectionnés

        # ds_selected = self.getSelectedDatasets_inMultiDatasetExplorer()

        ds_selected = self.getDatasetNamesDisplayedInSpectrumsViewers_inMultiDatasetExplorer()

        print("ds_selected!!!!!!!!!!:", ds_selected)

        bigger_ds = self.bl.shapes.getDatasetNameWithBiggerProbeSize(ds_selected, ref_ds_name)

        print("bigger_ds is:", bigger_ds)

        # ======================================================================
        # Mise à jour des plots dans les curveWidgets
        # ======================================================================

        for i, ds_name in enumerate(ds_selected):

            # bigger_ds = ref_ds_name #TODO, faire autrement

            title_sufix = ""

            # ==================================================================
            # Les differents types d'affichage
            # ==================================================================



            # On affiche que le spectres le plus proche du point cliqué dans chaque ds

            if not autosum:

                spectrum_indexes = self.bl.coordinates.getSpectrumIndexFromXY(ds_name, dataX, dataY, xy_space = ref_ds_name)



            # On affiche tous les spectres (ou moyenne en fonction de l'option dans display) contenus

            # dans la shape du plus gros jdd

            else:

                spectrumIndex_bigger_ds = self.bl.coordinates.getSpectrumIndexFromXY(bigger_ds, dataX, dataY, xy_space = ref_ds_name)

                print("spectrumIndex_bigger_ds:", spectrumIndex_bigger_ds)

                if ds_name == bigger_ds:

                    spectrum_indexes = spectrumIndex_bigger_ds



                else:

                    if spectrumIndex_bigger_ds is not None and spectrumIndex_bigger_ds != []:

                        #                        print "spectrumIndex_bigger_ds:",spectrumIndex_bigger_ds

                        overlap_map = self.bl.shapes.getOverlapMap(ds_name, bigger_ds)

                        # RENVOI NONE

                        if overlap_map is None:
                            print("error: overlap_map is None")

                            continue

                        spectrum_indexes_inside = np.fromstring(overlap_map["indexes_inside"][spectrumIndex_bigger_ds],
                                                                dtype = int,
                                                                sep=',')

                        indexes_inside_ratios = np.fromstring(overlap_map["indexes_inside_ratios"][spectrumIndex_bigger_ds],
                                                              dtype = float,
                                                              sep = ',')

                        #                        print "spectrum_indexes_inside:",spectrum_indexes_inside
                        #                        print "indexes_inside_ratios:",indexes_inside_ratios
                        #                        print "len(spectrum_indexes_inside):",len(spectrum_indexes_inside)

                        if len(spectrum_indexes_inside) == 0:
                            spectrum_indexes = []

                        else:
                            # print "spectrum_indexes_inside[indexes_inside_ratios > overlap_threshold]:",
                            # print spectrum_indexes_inside[indexes_inside_ratios > overlap_threshold]

                            spectrum_indexes = spectrum_indexes_inside[indexes_inside_ratios > overlap_threshold]

                            spectrum_indexes = list(spectrum_indexes)

                            overlap_ratio = overlap_map["overlap_ratio"][spectrumIndex_bigger_ds]

                            title_sufix = " - %d cumulated (%.2f%% overlap)" % (
                            len(spectrum_indexes), 100. * overlap_ratio)

                    else:

                        spectrum_indexes = []
                        # print "spectrum_indexes:",spectrum_indexes

            # ==============================================================





            # print "spectrumIndex inside updatePlots_inMultiDatasetExplorer:",spectrum_indexes

            self.gui.spectrums.updateDisplayedSpectrumsInWidgetByDsName(tab["curveItems"][ds_name],
                                                                        ds_name,
                                                                        spectrum_indexes = spectrum_indexes,
                                                                        title_prefix = ds_name + " - ",
                                                                        title_sufix = title_sufix)

    def getSelectedDatasets_inMultiDatasetExplorer(self):

        p = self.gui.panel

        lad = p.list_available_datasets

        ds_selected = [str(lad.item(i).text()) for i in range(lad.count())]

        # ds_selected   = [str(lad.item(i).text()) for i in range(lad.count()) if lad.item(i) in lad.selectedItems()]



        return ds_selected

    # ==================Context Menus===================================

    def contextMenuEventDsChoice__inMultiDatasetExplorer(self, event):

        """

        Methode appellée lors du click droit sur un dataset du multidatasetExplorer

        Creation d'un contextMenu contenant la liste des representations disponibles

        pour chaque dataset du projet

        """

        p = self.gui.panel

        widget = p.list_available_datasets

        menu = QtWidgets.QMenu(self)

        index = widget.indexAt(event.pos())

        clicked_item = widget.itemFromIndex(index)

        if not clicked_item: return

        ds_name = str(clicked_item.text())

        mc_logging.debug("context menus, right click on %s" % (ds_name,))

        # action neutre pemettant d'enlever toute representation pour ce dataset

        self.contextMenuEventDsChoice_addActionNoDisplay__inMultiDatasetExplorer(menu, ds_name)

        # actions pour chacune des representations de ce dataset

        self.contextMenuEventDsChoice_addActionForRepresentations__inMultiDatasetExplorer(menu, ds_name)

        parentPosition = widget.mapToGlobal(QtCore.QPoint(0, 0))

        menu.move(parentPosition + event.pos())

        menu.show()

    def contextMenuEventDsChoice_addActionNoDisplay__inMultiDatasetExplorer(self, menu, ds_name):

        """

        Add Neutral action removing any displayed representation of ds_name if selected

        """

        action = QtWidgets.QAction('No display', self)

        callback1 = partial(self.removeRepresentation_inMultiDatasetExplorer, ds_name=ds_name)

        callback2 = partial(self.removeSpectrumViewer_inMultiDatasetExplorer, ds_name=ds_name)

        action.triggered.connect(callback1)

        action.triggered.connect(callback2)

        menu.addAction(action)

    def contextMenuEventDsChoice_addActionForRepresentations__inMultiDatasetExplorer(self, menu, ds_name):

        """

        Add actions for all representations of ds_name

        """

        repr_names = self.bl.representations.getAvailableRepresentations(ds_name, output_type="tuples")

        for family, repr_name in repr_names:
            action = QtWidgets.QAction('%s (%s)' % (repr_name, family), self)

            repr_id = "%s - %s (%s)" % (ds_name, repr_name, family)

            callback1 = partial(self.contextMenuEventDsChoiceItemClicked__inMultiDatasetExplorer, repr_id)

            callback2 = partial(self.addSpectrumViewer_inMultiDatasetExplorer, ds_name=ds_name)

            action.triggered.connect(callback1)

            action.triggered.connect(callback2)

            menu.addAction(action)

    def contextMenuEventDsChoiceItemClicked__inMultiDatasetExplorer(self, repr_id):

        """

        Methode appellée lors du click sur une representation du contextMenu

        associé à un dataset du multidatasetExplorer

        """

        imageItems = self.getMultiDatasetExplorerImageItems()

        # On restreint l'affichage à une representation par dataset

        if repr_id in imageItems:

            self.removeRepresentation_inMultiDatasetExplorer(repr_id)

        else:

            ds_name, _, _ = self.getInfosFromReprId(repr_id)

            self.removeRepresentation_inMultiDatasetExplorer(ds_name=ds_name)

            self.addRepresentation_inMultiDatasetExplorer(repr_id)

    # ======================================================================


    # =====================================================================
    #          Methodes relatives à l'objet DatasetS (Model)
    # =====================================================================







    # @my_pyqtSlot(str)
    def displayCoeffsHistogram(self, method = "pca"):
        # ==== on s'assure qu'une PCA à bien été effectué avant l'affichage =====
        try:
            R, pca = self.getDatasetPCA()

        except Exception as e:
            print("PCA not launched yet")
            return
        # =======================================================================


        if method == "pca":
            components = pca.components_
            variance_ratios = pca.explained_variance_ratio_

        elif method == "ica":
            components = pca.components_
            variance_ratios = pca.explained_variance_ratio_

        else:
            mc_logging.error("method not implemented", method)
            return

        # ======================================================================
        #
        # ===================================================================

        max_components_nb = min(21, len(components) - 1) #21 pour avoir des abscisses entier

        #TODO: choisir le mode d'affichage
        title  = "variance vs component"
        x = range(1, max_components_nb + 1)
        y = variance_ratios[:max_components_nb]

        title  = "log10(variance) vs component"
        x = range(1, max_components_nb + 1)
        y = np.log10(variance_ratios[:max_components_nb])


        print("TITLE:",title)
        self.lines = "Lines"
        plots.displayAPlotInCurveWidget(curveWidget_name ='coeffsHistogram',
                                        title = title,
                                        style =self.lines,
                                        x = x, y = y,
                                        panel = self.gui.panel)  # ,



    # =====================================================================
    #          Methodes relatives à l'objet DatasetS (GUI)
    # =====================================================================


    # =======================================================================




    # ==============================================================================#
    #        Methodes specifiques aux projections (model)                           #
    # ==============================================================================#

    def getDatasetPCA(self, dataset_name = ""):

        if not dataset_name:
            dataset_name = self.mcData.datasets.currentDatasetName

        ds = self.mcData.datasets.getDataset(dataset_name)

        if "pca" in ds:

            R = ds["pca"]["R"]
            pca = ds["pca"]["pca"]

            return R, pca

        else:

            print("PCA not launched yet (getDatasetPCA)")
            raise

    def processPCA(self):

        myThread = Thread(target=self._processPCA, args=())
        myThread.daemon = True
        myThread.start()

    def _processPCA(self):
        """
        Cette methode calcule les vecteurs de base par PCA en prenant comme
        base de calcul:

        - l'ensemble des spectres du jdd
        - x spectres aleatoires dans le jdd
        - tout les spectres compris dans les groupes selectionnés

        Puis reprojete l'emsemble du jdd sur la base trouvée
        """
        p = self.gui.panel
        dname = self.mcData.datasets.currentDatasetName
        ds = self.mcData.datasets.getDataset(dname)

        mean_datas = ds["mean_datas"]
        dataset = ds["X"]
        W = ds["W"]

        ds_size = ds["size"]

        centerDatas = p.checkBox_centerDatas.isChecked()
        reduceDatas = p.checkBox_reduceDatas.isChecked()

        dataset_std = stdHDF5(dataset, axis=0)

        if self.gui.spectrums.useNormalizedData:
            dataset_normalized = self.gui.datasets.getDataset_X_normalized()
            mean_datas_normalized = self.gui.datasets.getDataset_MeanDatas_normalized()
            dataset_normalized_std = stdHDF5(dataset, axis=0)

        # ======================================================================
        # Sur quelle partie du jdd fait-on la PCA
        # ======================================================================
        pcaType = p.PCATypeCombo.currentText()

        if pcaType == "whole dataset":
            sampleSize    = ds_size
            sampleIndexes = list(range(0, ds_size))

        elif pcaType == "x size random set":

            sampleSize    = p.PCASampleSize.value()
            sampleIndexes = random.sample(list(range(ds_size)), sampleSize)
            sampleIndexes = np.sort(sampleIndexes)

        elif pcaType == "selected group":

            # TODO: faire selection de groupes multiples

            selected_group = self.bl.groups.getCurrentGroup()

            if not selected_group:
                QtWidgets.QMessageBox.warning(self, 'Error', "No group selected")
                return

            group = ds["groups"][selected_group]

            sampleIndexes = group["indexes"]
            sampleIndexes = np.sort(sampleIndexes)

            sampleSize = len(sampleIndexes)


        # ======================================================================
        # Affichage des informations
        # ======================================================================

        if sampleSize != ds_size:
            sample_size_info = "(%.1f%% on a total of %d)" % (100.0 * sampleSize / ds_size, ds_size)

        else:
            sample_size_info = "(whole dataset)"

        mc_logging.info("Processing PCA")
        mc_logging.debug("type: '%s'" % (pcaType,))
        mc_logging.info("sample size: %d %s" % (sampleSize, sample_size_info))
        # ======================================================================


        # ======================================================================
        # Preparation des données et instanciation PCA
        # ======================================================================
        useIncrementalPCA = True

        batch_size = getChunkSize(dataset.shape)

        if not useIncrementalPCA:
            n_components = min(len(W), sampleSize)
            pca = PCA()

        else:
            n_components = min(sampleSize, batch_size, len(W))
            pca = IncrementalPCA(n_components = n_components)

        # ======================================================================
        # conteneur des projections
        # ======================================================================
        R = None

        if self.gui.spectrums.useNormalizedData:
            dataset_normalized = self.gui.datasets.getDataset_X_normalized()

            if sampleSize != ds_size:
                X = dataset_normalized[...][sampleIndexes]  # attention ici, conversion en array depuis DatasetHDF5
            else:
                X = dataset_normalized

        else:
            if sampleSize != ds_size:
                X = dataset[...][sampleIndexes]  # attention ici, conversion en array depuis DatasetHDF5
            else:
                X = dataset

        X_mean = getMean(X, axis = 0)
        X_std  = stdHDF5(X, axis=0)

        # ======================================================================
        # preparation des données, centrage et suppression des nan ou inf
        # ======================================================================
        datas = self.bl.io.workFile.getTempHolder(datasetShape=X.shape)

        # ===========Partie à optimiser==========
        try:
            # en deux etapes car X - X_mean creerai un nouveau array

            datas[...] = X

            if centerDatas:
                datas[...] -= X_mean

            if reduceDatas:
                datas[...] /= X_std

        except MemoryError as e:

            mc_logging.debug("Memory error while preparing data for PCA, trying to process by chunks...")

            for i in range(0, len(X), batch_size):

                i_min = i

                i_max = max(len(X), i + batch_size)

                if i % 1000 == 0: print(".", end=' ')

                try:
                    datas[i_min: i_max] = X[i_min: i_max]

                    if centerDatas:
                        datas[i_min: i_max] -= X_mean

                    if reduceDatas:
                        datas[i_min: i_max] /= X_std

                except Exception as e:
                    print("except")
                    pass

                mc_logging.debug("done")


        #======================================================================
        print("converting nan to num...")#TODO:a optimiser

        print("batch_size:",batch_size)
        for i in range(0, len(datas), batch_size):
            np.nan_to_num(datas[i: i + batch_size])
        print("nan to num conversion done")
        #======================================================================

        # ======================================================================
        # Recherche des vecteurs de bases
        # ======================================================================
        if not useIncrementalPCA:

            try:
                pca.fit(datas[...])

            except MemoryError as e:
                msg = "Error: can't fit data, try to use smaller dataset sample"
                QtWidgets.QMessageBox.critical(self, 'Error', msg)

                mc_logging.info(msg)
                mc_logging.debug(e.message)

                print("datashape:", datas.shape)
                return

        else:
            mc_logging.info("using incrementalPCA")

            for i in range(0, datas.shape[0], batch_size):

                pca.partial_fit(datas[i:i + batch_size])

                if i % 1000 == 0: print(".", end=' ')

                self.gui.main.displayProgressBar(100.0 * i / datas.shape[0])

            print("\n")
            mc_logging.info("partialFit done")

            self.gui.main.resetProgressBar()

        # ======================================================================
        # Reprojection de tout le jdd sur les vecteurs de base
        # ======================================================================

        # =========Version directe=====================
        try:
            if self.gui.spectrums.useNormalizedData:
                dataset_pre_processed = dataset_normalized

                if centerDatas:
                    dataset_pre_processed -= mean_datas_normalized

            else:
                dataset_pre_processed = dataset

                if centerDatas:
                    dataset_pre_processed -= mean_datas

            if reduceDatas:
                dataset_pre_processed /= stdHDF5(dataset_pre_processed, axis=0)

            R = pca.transform(dataset_pre_processed)


        # ========Version par etapes, pour ne pas saturer la mémoire============

        except MemoryError:

            mc_logging.warning("Memory error while projecting dataset on base vector, trying to process by chunks...")

            R = self.bl.io.workFile.getTempHolder(datasetShape = (ds_size, n_components))

            assert (ds_size > batch_size), "chunk_size must be < ds_size"

            for i in range(0, ds_size, batch_size):

                idx_min = i
                idx_max = min(i + batch_size, ds_size)

                if self.gui.spectrums.useNormalizedData:

                    dataset_chunk_pre_processed = dataset_normalized[idx_min:idx_max, :]

                    if centerDatas:
                        dataset_chunk_pre_processed -= mean_datas_normalized

                    if reduceDatas:
                        dataset_pre_processed /= dataset_normalized_std

                    R[idx_min:idx_max, :] = pca.transform(dataset_chunk_pre_processed)


                else:

                    dataset_chunk_pre_processed = dataset[idx_min:idx_max, :]

                    if centerDatas:
                        dataset_chunk_pre_processed -= mean_datas

                    if reduceDatas:
                        dataset_pre_processed /= dataset_std

                    R[idx_min:idx_max, :] = pca.transform(dataset_chunk_pre_processed)

        mc_logging.info("PCA done!")

        # ======== on enregistre pour affichage ulterieur ===========

        # TODO: supprimer cette dependance a l'objet pca
        ds = self.mcData.datasets.getDataset(dname)
        ds["pca"] = dict()
        ds["pca"]["R"] = R
        ds["pca"]["pca"] = pca
        # ==========================================================

        # ======================================================================
        # On prepare l'enregistrement dans le dictionnaire des projections
        # ======================================================================
        mc_logging.debug("preparing projection...")

        vectors_names = ["PC%d" % (i + 1,) for i in range(len(pca.components_))]

        vectors = dict()
        values  = dict()

        for pc_idx, v_name in enumerate(vectors_names):
            self.gui.main.displayProgressBar(100.0 * pc_idx / len(vectors_names))

            vectors[v_name] = pca.components_[pc_idx]

            values[v_name] = R[:, pc_idx]

        self.gui.main.resetProgressBar()

        if centerDatas:
            if self.gui.spectrums.useNormalizedData:
                vectors["mean_data"] = mean_datas_normalized
            else:
                vectors["mean_data"] = mean_datas

            values["mean_data"]  = [1 for __ in range(ds_size)]

            # on ajoute mean_data en première place
            vectors_names.reverse()
            vectors_names.append("mean_data")
            vectors_names.reverse()

        # on ajoute les valeurs des variances

        parameters_names = ["variance", ]
        parameters_units = ["%", ]
        parameters_values = [[variance * 100, ] for variance in pca.explained_variance_ratio_.tolist()]

        if centerDatas:
            parameters_values.insert(0, [np.nan, ])  # traitement particulier pour mean_data

        parameters_values = np.array(parameters_values)

        mc_logging.debug("insert Projection in dict")

        # =====================================================================
        #      On insere  dans le dictionnaire des projections
        # =====================================================================
        self.gui.projections.insertProjectionInDatasetDict("PCA",
                                                           vectors_names,
                                                           vectors,
                                                           values,
                                                           parameters_names,
                                                           parameters_values,
                                                           parameters_units,
                                                           order_by = '',
                                                           override = True)

        mc_logging.debug("Projection insertion done")

        # On affiche par default PC1
        self.gui.representations.signal_updateRepresentationDisplay.emit("PCA", "PC1", False)

        # =====================================================================
        #                 Affichages specifiques à la PCA
        # =====================================================================
        self.gui.main.signal_displayCoeffsHistogram.emit("pca")

        # =====================================================================
        #                 Affichage projection 2D
        # =====================================================================
        self.gui.projections.signal_update2DProjectionPlot.emit()

        return pca, R




    # ==============================================================================#
    #        Methodes specifiques aux projections (GUI)                           #
    # ==============================================================================#
    def initOverviewTab(self):
        print("===== Overview tab initialisation =====")
        p = self.gui.panel
        self.overviewTab = dict()

        # =======================================================================
        #     Creation des widgets
        # =======================================================================
        layout = p.overviewLayout

        widget1 = PlotDialog(edit = False, toolbar = False)
        widget1.setObjectName('coeffsHistogram')

        widget2 = PlotDialog(edit = False, toolbar = False)
        widget2.setObjectName('meanData')

        layout.addWidget(widget1, 1, 0)
        layout.addWidget(widget2, 1, 1)

        self.gui.main.save_widget_ref(widget1)
        self.gui.main.save_widget_ref(widget2)


    # ==============================================================================#
    #        Methodes specifiques aux representations (model)                       #
    # ==============================================================================#


    # ==============================================================================#
    #        Methodes specifiques aux representations (GUI)                         #
    # ==============================================================================#




    def getMultiDatasetExplorerImagePlot(self):

        tab = self.multiDatasetExplorerTab

        return tab["imageWidget"].get_plot()

    def getMultiDatasetExplorerImageItems(self):

        plot = self.getMultiDatasetExplorerImagePlot()

        items = dict()

        for item in plot.get_items(item_type = IImageItemType):

            item_title = item.title().text()

            # TODO: un peu bizar comme façon de faire mais toute les repr on ( et )
            # dans leurs title

            if "(" and ")" in item_title:
                items[item_title] = item

        return items



    def comboMetadatasChanged(self):
        self.gui.signals.signal_spectrumsToDisplayChanged.emit([])

    # ==============================================================================#
    #  Update display in GUI
    # ==============================================================================#

    # @my_pyqtSlot(bool)

    def setUseNormalizedData(self):
        self.gui.datasets.signal_updateDisplayOnDatasetChange.emit(False)

    def setNormalizeType(self):
        """
        On calcul ou recalcul le mean data
        """

        ds_name = self.mcData.datasets.currentDatasetName
        ds =      self.mcData.datasets.getDataset(ds_name)

        datas_normalized = normalizeHDF5(ds["X"], self.bl.io.workFile, self.gui.spectrums.normalizeMethod)

        print("type(datas_normalized)", type(datas_normalized))

        ds["mean_datas_normalized"] = getMean(datas_normalized, axis=0)
        ds["X_normalized"] = datas_normalized

        self.gui.datasets.signal_updateDisplayOnDatasetChange.emit(False)


    def closeEvent(self, event):
        """
        Surcharge QWidget
        Methode appellee lors de la fermeture du programme
        """
        quit_msg = "Do you want to save current project before closing?"

        reply = QtWidgets.QMessageBox.question(self,
                                               'Message',
                                               quit_msg,
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No |
                                               QtWidgets.QMessageBox.Cancel)

        if reply == QtWidgets.QMessageBox.Yes:

            self.bl.io.deleteWorkFile()

            if self.gui.io.saveProject():
                self.bl.io.projectFile.close()
                event.accept()

            else:
                print("close event canceled")
                event.ignore()


        elif reply == QtWidgets.QMessageBox.No:
            self.bl.io.deleteWorkFile()
            self.bl.io.deleteProjectFile()

            event.accept()

        else:
            event.ignore()




def getTxtFromCss(path):
    """
    Ouvre la feuille de style et renvoie un string
    """

    css = QtCore.QFile(path)

    css.open(QtCore.QIODevice.ReadOnly)

    txt = ''

    if css.isOpen():
        print("css file opened")

        txt = css.readAll().data().decode("utf-8")

    css.close()

    return txt



class CustomFilter(QObject):

    def __init__(self):
        # http://enki-editor.org/2014/08/23/Pyqt_mem_mgmt.html
        super().__init__()

    def eventFilter(self, receiver, event):

        if (event.type() == QEvent.KeyPress):

            # print "Key '%s' pressed" % (event.text(),)
            # QMessageBox.information(None,"Filtered Key Press Event!!","You Pressed: "+ event.text())

            if event.key() == QtCore.Qt.Key_Escape:
                # On evite ainsi le probleme du escape cassant les images/curveDialogs
                return True

            else:
                return False
                # return True

        else:
            # Call Base Class Method to Continue Normal Event Processing
            return super(CustomFilter, self).eventFilter(receiver, event)


def launchApp():
    qtApp = QtWidgets.QApplication([''])

    QtGui.QFontDatabase.addApplicationFont('bin/fonts/Sacramento-Regular.ttf')

    txt = getTxtFromCss('bin/css/global.css')
    qtApp.setStyleSheet(txt)

    customFilter = CustomFilter()
    qtApp.installEventFilter(customFilter)

    gui = ClusterExplorer()

    gui.show()

    qtApp.exec_()


if __name__ == "__main__":

    try:
        launchApp()
    finally:
        import sys
        import traceback

        print("=" * 40 + "\n" + " " * 15 + "DEBUG" + "\n" + "=" * 40)
        print(sys.exc_info()[0])
        print(traceback.format_exc())
        print("=" * 40 + "\n" + " " * 5 + "Press enter to close..." + "\n" + "=" * 40)

        input()
