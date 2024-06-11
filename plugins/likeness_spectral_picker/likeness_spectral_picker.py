import threading

import numpy as np
from PyQt5 import QtGui, QtCore
from PyQt5 import uic
from PyQt5.QtWidgets import QPushButton, QFileDialog, QMessageBox

from plotpy.builder import make
from plotpy.plot import PlotDialog,PlotOptions

from helpers import mc_logging
from helpers.plots import plots
from plotpy.tools import SelectPointTool
from threading import Thread
import scipy
import io

import time

import matplotlib.pyplot as pl
from PyQt5.QtCore import pyqtSignal, QObject

from PyQt5 import QtWidgets



from sklearn.linear_model import Ridge


class LikenessSpectralPicker(QObject):


    def __init__(self, bl, mcData, gui):
        super().__init__()

        self.tab = "MCR"
        self.family = "None"
        self.name   = "Likeness spectral picker"
        self.tooltip_text = "tooltip text..."

        self.menu_item = QPushButton("LikenessPicker",
                                      clicked = self.launchGUI)

        self.bl = bl
        self.mcData = mcData
        self.gui = gui

        self.mainWindow = self.gui.main.mainWindow


    def createLikenessImage_thread(self):
        ds = self.mcData.datasets.getDataset()

        X_norm_max_to_1 = self.gui.datasets.getDataset_X_normalized("max")
        X_norm = X_norm_max_to_1

        # X_norm = self.gui.datasets.getDataset_X_normalized()
        # X_norm = X_norm[:800]

        compared_to_index = 190

        self.datas = X_norm

        # if self.gui.spectrums.useNormalizedData:
        #     self.datas = ds["X"]
        # else:
        #     self.datas = X_norm

        self.W = ds["W"]


        metric_list = [""]
        print("calculating distances, please wait.....")
        distances = scipy.spatial.distance.pdist(X_norm, metric = "correlation")
        distances = scipy.spatial.distance.squareform(distances)

        #print(scipy.spatial.distance.squareform(distances))

        print("distances", distances)
        print("len distances", len(distances))
        print("distances processed!")
        indexes_sorted = np.argsort(distances[:,compared_to_index])
        print("ids_sorted:",indexes_sorted)

        self.idxs_sorted = indexes_sorted


        imagePlot = self.imageDialog.get_plot()


        reordered = X_norm_max_to_1[...][indexes_sorted,:]

        # par defaut, pas d'interpolation
        imageItem = make.image(reordered,
                               interpolation = 'nearest',
                               title = "Representation"
                               )

        imagePlot.add_item(imageItem)

        plots.displayAPlotInCurveWidget(curveWidget_name = "plotContainer_spectrum",
                                        title = "distances",
                                        x = range(len(distances)),
                                        y = distances[self.idxs_sorted,compared_to_index],
                                        panel = self.lsp_panel)




    def launchGUI(self):

        #=========================================================================
        # import GUI
        # ========================================================================
        #TODO rendre relatif
        d = uic.loadUi("plugins//likeness_spectral_picker//liknesss_picker.ui")

        d.setWindowTitle("LikenessSpectralPicker")

        self.lsp_panel = d


        #=========================================================================
        # Create curves
        #=========================================================================
        widget = PlotDialog(edit = False, toolbar = False, options=PlotOptions(type="image"))
        widget.setObjectName('plotContainer_image')
        widget.setFixedWidth(600)

        self.imageDialog = widget

        d.horizontalLayout.insertWidget(0,widget)
        self.gui.main.save_widget_ref(widget)

        selectTool = widget.manager.add_tool(SelectPointTool,
                                             title = "Selection (point)",
                                             on_active_item = False,
                                             mode = "create",
                                             end_callback = self.pickerSelectionChanged)

        selectTool.activate()



        widget = PlotDialog(edit = False, toolbar = False, options=PlotOptions(type="curve"))
        widget.setObjectName('plotContainer_spectrum')
        widget.setFixedHeight(250)

        d.verticalLayout.insertWidget(0,widget)
        self.gui.main.save_widget_ref(widget)


        #========================================================================
        # On lance le calcul de l'image
        #========================================================================
        myThread = Thread(target = self.createLikenessImage_thread,)
        myThread.deamon = True
        myThread.start()



        #on lance l'interface
        d.setModal(True)
        ok = d.exec_()

        #=========================================================================
        # On recupere les donnees de la gui
        #=========================================================================
        if ok:
            pass


    def pickerSelectionChanged(self, tool):
        dataX, idx = tool.get_coordinates()
        # print("pickerSelectionChanged")
        # print("dataX, dataY", dataX, idx)
        idx = int(idx)

        if not hasattr(self,"idxs_sorted"):
            print("Distance calculation not done yet!")
            return

        try:
            idx = self.idxs_sorted[idx]
        except IndexError:
            return

        if 0 <= idx < len(self.datas):
            plots.displayAPlotInCurveWidget(curveWidget_name = "plotContainer_spectrum",
                                            title = "spectrum {}".format(idx),
                                            x = self.W,
                                            y =  self.datas[idx],
                                            panel = self.lsp_panel)
        else:
            print("out of range idx")


    def update_displayed_spectrum(self):

        ds = self.mcData.datasets.getDataset()

        index = 10
        plots.displayAPlotInCurveWidget(curveWidget_name = "plotContainer_spectrum",
                                        title = "spectrum %d",
                                        x = ds["W"],
                                        y =  ds["X"][index],
                                        panel = self.lsp_panel)


