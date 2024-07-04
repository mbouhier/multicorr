# -*- coding: utf-8 -*-
"""
Created on Wed Jan 29 15:34:18 2014

@author: mbouhier
"""
import numpy as np

from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5 import uic
from PyQt5.QtWidgets import *

from itertools import chain



import matplotlib.pyplot as pl
import time



from numpy.random import randn

from threading import Thread, Timer

import scipy.io

from matplotlib.backends.backend_qt5agg import (FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure

from scipy.spatial import distance_matrix
from Orange.widgets.unsupervised.owhierarchicalclustering import DendrogramWidget,OWHierarchicalClustering
from Orange.misc.distmatrix import DistMatrix
from Orange.data import Table, Domain, ContinuousVariable, DiscreteVariable

import h5py
import sys

from Orange.widgets.utils import colorpalette, itemmodels



sys._excepthook = sys.excepthook


def exception_hook(exctype, value, traceback):
    sys._excepthook(exctype, value, traceback)
    sys.exit(1)


sys.excepthook = exception_hook


from Orange.clustering.hierarchical import \
    postorder, preorder, Tree, tree_from_linkage, dist_matrix_linkage, \
    leaves, prune, top_clusters




class InteractiveHAC(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("title")
        # =====================================
        p = uic.loadUi("interactiveHAC.ui")
        self.panel = p
        self.setCentralWidget(p)
        self.init_vars()
        self.init_gui()

        print("before")
        self.loadFile()
        print("after")

        #self.updateSpectrumPlot([])
        self.updateDendrogram()
        self.updateImage()

    def init_vars(self):
        # ======================================================================
        #     Initialisation des variables
        # ======================================================================
        self.maxSpToLoad = -1
        self.max_PCs = 30


    def loadFile(self):

        filename = "\\\\crabe\\communs\\LIDyL\\PCR\\Mickael Bouhier\\clustering_git_pyqt5_python3_latest\\testsMCR_14_02_18\\projet_avec_suppression_metal2.h5"

        ds_file = h5py.File(filename, 'r')
        datasetname = 'sans_metal'

        ds = ds_file[datasetname]
        self.ds = ds

        spectrums = ds['X']
        W = ds['W']
        xys = ds['xys']

        if self.maxSpToLoad != -1:
            projection = ds["projections"]["PCA"]["values"][:self.maxSpToLoad,1:self.max_PCs]
        else:
            projection = ds["projections"]["PCA"]["values"][:, 1:self.max_PCs]

        print("original shape",ds["projections"]["PCA"]["values"].shape)
        self.projection = projection

        self.backgroundImage = self._getBackgroundImage()

    def getOrangeDistanceMatrix(self):
        pc_nb = self.projection.shape[1]


        attributes = [ContinuousVariable("PC{}".format(i)) for i in range(pc_nb)]

        # class_var_list = [DiscreteVariable(classe_family, values = self.get_classe_names(classe_family=classe_family)) for
        #                   classe_family in classe_family_names]

        print("2")
        domain = Domain(attributes = attributes)#, class_vars = class_var_list)

        table = Table.from_list(domain, self.projection)

        raw_dm = distance_matrix(self.projection, self.projection)

        print("3")
        return DistMatrix(raw_dm, row_items = table)

    def init_gui(self):

        p = self.panel

        # ======================================================================
        #     Spectrum viewer
        # ======================================================================
        mpl_canvas  = FigureCanvas(Figure(figsize = (5, 3)))
        mpl_toolbar = NavigationToolbar(mpl_canvas, self)

        p.gridLayout.addWidget(mpl_toolbar, 0, 0)
        p.gridLayout.addWidget(mpl_canvas, 1, 0)

        mpl_ax = mpl_canvas.figure.add_subplot(111)

        self.mpl_toolbar = mpl_toolbar
        self.mpl_ax = mpl_ax

        # ======================================================================
        #     Image viewer
        # ======================================================================
        mpl_canvas_image  = FigureCanvas(Figure(figsize = (5, 3)))
        mpl_toolbar_image = NavigationToolbar(mpl_canvas_image, self)

        p.gridLayout.addWidget(mpl_toolbar_image, 2, 0)
        p.gridLayout.addWidget(mpl_canvas_image, 3, 0)

        mpl_ax = mpl_canvas_image.figure.add_subplot(111)

        self.mpl_toolbar_image = mpl_toolbar
        self.mpl_ax_image = mpl_ax

        # ======================================================================
        #     Dendrogram
        # ======================================================================
        dendrogram = OWHierarchicalClustering()

        p.gridLayout.addWidget(dendrogram, 0, 1,-1,1)
        self.dendrogram = dendrogram

        # ======================================================================
        #     Button
        # ======================================================================
        button = QtGui.QPushButton('Create Image', self)
        button.clicked.connect(self.updateImage)
        p.gridLayout.addWidget(button, 4, 1)

        # =======================================================================
        #     Configuration signaux/slots
        # =======================================================================
        self.makeConnections()


    def _getBackgroundImage(self):
        ds = self.ds

        height = ds["height"][()]#.value
        width  = ds["width"][()]#.value

        image = np.zeros((height, width))
        lut = ds["idx_to_img_coo"]

        #On prend la PC1 pour l'image de fond
        PC1 = ds["projections"]["PCA"]["values_by_vector"]["PC1"]

        for idx in range(len(ds["X"])):
            x,y = lut[idx]
            image[x,y] = PC1[idx]

        return image


    def updateImage(self):

        ax = self.mpl_ax_image
        ds = self.ds

        ax.clear()
        height = ds["height"][()]#.value
        width  = ds["width"][()]#.value

        image = np.zeros((height, width , 4), dtype = np.uint8)
        lut   = ds["idx_to_img_coo"]


        cluster_idxs  = getattr(self, "cluster_idxs", [])

        palette = colorpalette.ColorPaletteGenerator(len(cluster_idxs))

        for i, idxs in enumerate(cluster_idxs):
            color = palette[i]
            color.setAlpha(255)

            for idx in idxs:
                x,y = lut[idx]
                image[x,y][:] = color.getRgb()


        ax.imshow(self.backgroundImage, alpha = 0.3)
        ax.imshow(image)


        ax.figure.canvas.draw()


    def updateDendrogram(self):
        self.dendrogram.set_distances(self.getOrangeDistanceMatrix())

    def updateSpectrumPlot(self, idxs):

        ds = self.ds
        X  = ds["X"]
        W  = ds["W"]

        ax = self.mpl_ax
        ax.clear()

        if idxs is None: return


        cluster_mean_spectrum = np.mean(X[idxs], axis = 0)
        cluster_std_deviation = np.std(X[idxs], axis = 0)


        # x = np.linspace(0,2*np.pi,100)
        # y = np.sin(x)

        ax.plot(W, cluster_mean_spectrum)
        ax.plot(W, cluster_mean_spectrum - cluster_std_deviation, "r--")
        ax.plot(W, cluster_mean_spectrum + cluster_std_deviation, "r--")
        ax.grid()
        #ax.set_xticks(idxs, minor = False)
        # ax.set_xticklabels(["{}".format(i) for i in idxs], minor = False)
        ax.set_title("Spectrums in cluster")
        # ax.set_xlabel('Nombre d'onde')
        # ax.set_ylabel('Inertia')

        ax.figure.canvas.draw()


    def makeConnections(self):
        self.dendrogram.dendrogram.itemClicked.connect(self.clusterSelected)
        #self.dendrogram.Outputs.annotated_data.bound_signal(self.test)



    def test(self,a):
        print("a:",a)


    def clusterSelected(self, a):
        # print("rrrrrrrrrrrr")
        # print(a)
        out = self.dendrogram.dendrogram.selected_nodes()

        #print(out)

        #============================================================================
        #                  All Selection
        #============================================================================
        # selection = self.dendrogram.dendrogram.selected_nodes()
        # selection = sorted(selection, key=lambda c: c.value.first)
        #
        # print(self.dendrogram.root)
        # indices = [leaf.value.index for leaf in leaves(self.dendrogram.root)]
        #
        # cluster_indexes = [indices[node.value.first:node.value.last] for node in selection]
        #
        # print(cluster_indexes)
        # all_cluster_indexes = list(chain(*cluster_indexes))
        # print(all_cluster_indexes)
        #
        # return
        #

        # [Tree(value=ClusterData(range=(1, 3), height=31.995534896850586), branches=(
        # Tree(value=SingletonData(range=(1, 2), height=0.0, index=89), branches=()),
        # Tree(value=SingletonData(range=(2, 3), height=0.0, index=90), branches=()))),
        #  Tree(value=ClusterData(range=(7, 9), height=34.067447662353516), branches=(
        #  Tree(value=SingletonData(range=(7, 8), height=0.0, index=275), branches=()),
        #  Tree(value=SingletonData(range=(8, 9), height=0.0, index=535), branches=()))),
        #  Tree(value=ClusterData(range=(58, 60), height=14.914658546447754), branches=(
        #  Tree(value=SingletonData(range=(58, 59), height=0.0, index=923), branches=()),
        #  Tree(value=SingletonData(range=(59, 60), height=0.0, index=924), branches=())))]

        #============================================================================
        #                  Current Selection
        #============================================================================
        selection = self.dendrogram.dendrogram.selected_nodes()
        selection = sorted(selection, key=lambda c: c.value.first)

        print("selection:",selection)

        indices = [leaf.value.index for leaf in leaves(self.dendrogram.root)]

        cluster_indexes = [indices[node.value.first:node.value.last] for node in selection]

        print("cluster_indexes:", cluster_indexes)
        all_cluster_indexes = list(chain(*cluster_indexes))
        #all_cluster_indexes = [ idx - 1 for idx in all_cluster_indexes ]

        print("all_cluster_indexes:", all_cluster_indexes)

        all_cluster_indexes = sorted(all_cluster_indexes)

        self.cluster_names = ["current_cluster"]
        self.cluster_idxs  = cluster_indexes#[all_cluster_indexes]


        self.updateSpectrumPlot(all_cluster_indexes)
        self.updateImage()

        #print(out.selected_data.widget.Outputs.selected_data.items.ids)


def test():
    qtApp = QtWidgets.QApplication([''])
    gui = InteractiveHAC()
    gui.show()
    qtApp.exec_()


if __name__ == "__main__":
    test()
