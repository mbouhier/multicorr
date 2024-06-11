# -*- coding: utf-8 -*-
"""
Created on Wed Jan 29 15:34:18 2014

@author: mbouhier
"""
import numpy as np

from PyQt5 import QtGui, QtWidgets

from PyQt5 import uic

from plotpy.items import RGBImageItem, ImageItem

from plotpy.plot import PlotDialog, PlotOptions


import matplotlib.pyplot as pl
import time


from PyQt5.QtCore import *

from numpy.random import randn

from threading import Thread, Timer

import scipy.io

import h5py
import pandas as pd
import datashader as ds
import datashader.transfer_functions as tf
import sys

import time
from datashader import reductions


sys._excepthook = sys.excepthook
def exception_hook(exctype, value, traceback):
    sys._excepthook(exctype, value, traceback)
    sys.exit(1)
sys.excepthook = exception_hook



class AdaptativePlotDisplay(QtWidgets.QMainWindow):
    
    def __init__(self):
            super().__init__()
            self.setWindowTitle("title")
            #=====================================
            p = uic.loadUi("test.ui")
            self.panel = p
            self.setCentralWidget(p)
            self.init_vars()
            self.init_gui()


    def init_vars(self):
        #======================================================================
        #     Initialisation des variables
        #======================================================================

        filename = "D:\\datasets.py\\test_pour_datashader5.h5"
        filename = "\\\\crabe\\communs\\LIDyL\\PCR\\Mickael Bouhier\\clustering_git_pyqt5_python3_latest\\todel_for_axiSignalOnPlot.h5"
        ds_name  = "Raman"

        print("opening",filename)

        f = h5py.File(filename, 'r')

        v = f[ds_name]["projections"]["PCA"]["values"][:]

        print(v)
        nb_values = v.shape[0]

        columns_ids = ["PC%d" % (i+1,) for i in range(v.shape[1] - 1)]
        columns_ids.insert(0,"mean_data")

        df = pd.DataFrame(data = v, index = range(nb_values), columns = columns_ids)


        #======================================================================
        # Ajout des groupes et de leurs couleurs respective
        #=======================================================================
        groups_id_list = ["no_group" for i in range(nb_values)]

        groups_colors = dict()

        for group_name, h in f[ds_name]["groups"].items():
            color = h["color"]
            groups_colors[group_name] = '#%02x%02x%02x' % (color[0], color[1], color[2])

            for idx in h["indexes"]:
                #print(idx,"assigned to",group_name)
                groups_id_list[idx] = group_name

        #on rajoute une couleur pour les points sans groupe
        groups_colors["no_group"] = '#%02x%02x%02x' % (168, 126, 0)

        print("groups_colors:",  groups_colors)
        print("groups_id_colums:", groups_id_list)


        df['group_id'] = pd.Series(groups_id_list, index = df.index, dtype = "category")



        print(df.head())
        print(df.tail())
        print(df.describe())

        plot_width = 1000
        plot_height = 1000

        dim1 = "PC4"
        dim2 = "PC1"

        x_range = [df[dim1].values.min(), df[dim1].values.max()]
        y_range = [df[dim2].values.min(), df[dim2].values.max()]


        #x_range = [-17,20]
        #y_range = [-5,5]


        print(x_range)
        print(y_range)

        cvs = ds.Canvas(plot_width  = plot_width,
                        plot_height = plot_height,
                        x_range = x_range,
                        y_range = y_range)
        #https: // anaconda.org / jbednar / pipeline / notebook
        #agg = cvs.line(df, dim1, dim2, ds.count(dim2)) #count,any,sum,...
        agg = cvs.points(df, dim1, dim2, reductions.count())  # count,any,sum,...

        self.agg = agg
        self.dim1 = dim1
        self.dim2 = dim2
        self.df = df
        print(self.df.group_id.cat.categories)
        print(self.df.head())
        print("groups_colors1", groups_colors)

        gc = groups_colors #alias
        self.groups_colors = [gc[group_name] for group_name in self.df.group_id.cat.categories]

        print("groups_colors1", self.groups_colors)


    def init_gui(self):
        #======================================================================
        #     Creation des widgets Plot et image
        #=======================================================================
        p = self.panel

        imgDialog = PlotDialog(edit    = False,
                                toolbar = True,
                                options = PlotOptions(show_contrast=False,type="image")
                               )


        p.gridLayout.addWidget(imgDialog)
        plot = imgDialog.get_plot()

        plot.SIG_PLOT_AXIS_CHANGED.connect(self.representation_axes_changed)



        df = self.df
        dim1 = self.dim1
        dim2 = self.dim2

        x_range = [df[dim1].values.min(), df[dim1].values.max()]
        y_range = [df[dim2].values.min(), df[dim2].values.max()]


        imageItem = ImageItem()


        plot.add_item(imageItem)



        bottom_id = plot.get_axis_id("bottom")
        left_id = plot.get_axis_id("left")

        plot.set_axis_direction('left', 0)

        x_range = plot.get_axis_limits(bottom_id)
        y_range = plot.get_axis_limits(left_id)


        self.plot = plot
        self.imageItem = imageItem

        #self.makeConnections()


    #=======================================================================
    #     Autres
    #=======================================================================
    def representation_axes_changed(self, plot):

        bottom_id = plot.get_axis_id("bottom")
        left_id   = plot.get_axis_id("left")



        # =======================================================================
        #     debouce
        # =======================================================================
        self.new_refresh_requested = True

        myThread = Thread(target = self.refresh_image, args = ( plot, ))
        myThread.daemon = True
        myThread.start()



    def refresh_image(self, plot):

        #=======================================================================
        #     Debounce
        #=======================================================================
        self.new_refresh_requested = False

        print("waiting before image processing...")
        while(time.time() - getattr(self, 'last_refresh', 0) < 0.8):
            if( self.new_refresh_requested):
                print("abort")
                return
        print("processing")
        # =======================================================================
        #     Debounce fin
        # =======================================================================

        agg = self.agg

        bottom_id = plot.get_axis_id("bottom")
        left_id   = plot.get_axis_id("left")

        x_range = plot.get_axis_limits(bottom_id)
        y_range = plot.get_axis_limits(left_id)
        #Si les axes ne sont pas encore initialisé

        if(x_range[1] - x_range[0]) == 0 :
            print("axis X not initialized...")
            return
        if(y_range[1] - y_range[0]) == 0:
            print("axis Y not initialized...")
            return

        print("xlimits:", x_range)
        print("ylimits:", y_range)

        print("plot screen width:", plot.frameGeometry().width())
        print("plot screen height:", plot.frameGeometry().height())

        cvs = ds.Canvas(plot_width = int(0.5*plot.frameGeometry().width()),
                        plot_height = int(0.5*plot.frameGeometry().height()),
                        x_range = [min(x_range), max(x_range)],
                        y_range = [min(y_range), max(y_range)])

        agg = cvs.points(self.df, self.dim1, self.dim2, reductions.count_cat('group_id'))  # count,any,sum,...


        cmap = ["lightblue", "darkred"]

        max_alpha = 255
        self.groups_colors
        #img = tf.shade(agg, cmap = ds.colors.inferno, alpha = max_alpha, how = 'eq_hist')

        # img = tf.shade(agg,
        #                cmap = ds.colors.inferno,
        #                alpha = max_alpha,
        #                color_key = self.groups_colors,
        #                how = 'eq_hist')

        img = tf.shade(agg,
                       alpha = max_alpha,
                       # cmap=["#1a01ff"],
                       color_key = self.groups_colors,
                       how = 'eq_hist')

        # mask = np.array([[1, 1, 1, 1, 1, 1, 1],
        #                  [1, 1, 0, 0, 0, 1, 1],
        #                  [1, 0, 1, 0, 1, 0, 1],
        #                  [1, 0, 0, 1, 0, 0, 1],
        #                  [1, 0, 1, 0, 1, 0, 1],
        #                  [1, 1, 0, 0, 0, 1, 1],
        #                  [1, 1, 1, 1, 1, 1, 1]])
        #img = tf.spread(img, mask = mask)

        img = tf.dynspread(img, shape = 'square', threshold = 0.80)


        self.imageItem.set_xdata(min(x_range), max(x_range))
        self.imageItem.set_ydata(min(y_range), max(y_range))
        self.imageItem.set_data(img.data)


        self.plot.replot()
        self.last_refresh = time.time()


    def makeConnections(self):
        pass
        
        
        
def test():
    qtApp = QtWidgets.QApplication([''])
    gui = AdaptativePlotDisplay()
    gui.show()
    qtApp.exec_()
    
    
if __name__ == "__main__":
    test()
 