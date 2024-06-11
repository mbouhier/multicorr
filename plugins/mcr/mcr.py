import threading

import numpy as np
from PyQt5 import QtGui, QtCore
from PyQt5 import uic
from PyQt5.QtWidgets import QPushButton, QFileDialog, QMessageBox

from plotpy.builder import make
from plotpy.plot import PlotDialog, PlotOptions

from helpers import mc_logging
from helpers.plots import plots

from threading import Thread

import io

import time

import matplotlib.pyplot as pl
from PyQt5.QtCore import pyqtSignal, QObject

from PyQt5 import QtWidgets



from pymcr.mcr import McrAR
from pymcr.regressors import OLS, NNLS
from pymcr.constraints import ConstraintNonneg, ConstraintNorm
from pymcr import constraints


from sklearn.linear_model import Ridge

import sys
import contextlib

from .error_functions import err_fcn_lof

@contextlib.contextmanager
def redirect_stdout(target):
    original = sys.stdout
    sys.stdout = target
    yield
    sys.stdout = original


class MultivariateCurveResolution(QObject):

    signal_displayCurrentIteration = pyqtSignal()

    def __init__(self, bl, mcData, gui):
        super().__init__()

        self.tab = "MCR"
        self.family = "representation_creation"
        self.name   = "Multivariate Curve Resolution"
        self.tooltip_text = "tooltip text..."

        self.menu_item = QPushButton("MCR",
                                      clicked = self.launchGUI)

        self.bl = bl
        self.mcData = mcData
        self.gui = gui

        self.mainWindow = self.gui.main.mainWindow

        self._verbose_catcher = io.StringIO()
        self.curveDialogs = dict()
        self.loadingWidgetNames = dict()

        self.signal_displayCurrentIteration.connect(self.update_displayed_loadings)


    def launchGUI(self):

        #=========================================================================
        # import GUI
        # =========================================================================
        #TODO rendre relatif
        d = uic.loadUi("plugins//mcr//mcr.ui")

        d.setWindowTitle("Multivariate Curve Resolution")

        self.mcr_panel = d

        #on lance l'interface
        d.setModal(True)
        ok = d.exec_()

        #=========================================================================
        # On recupere les donnees de la gui
        #=========================================================================
        if ok:
            nb_compo       = d.spinBox_nb_compo.value()
            max_iter       = d.spinBox_max_iter.value()
            tol_increase   = d.spinBox_tol_increase.value()
            tol_n_increase = d.spinBox_tol_n_increase.value()

            initial_estimates_mode = str(d.comboBox_initial_sp_estimates.currentText())

            st_regr = [str(item.text()) for item in d.listWidget_st_regr.selectedItems()]
            c_constraints_str    = [str(item.text()) for item in d.listWidget_c_constraints.selectedItems()]
            constraints_norm_str = [str(item.text()) for item in d.listWidget_constraints_norm.selectedItems()]

            constraints_lut = {
                               "ConstraintNonneg": ConstraintNonneg(),
                               "ConstraintNorm": ConstraintNorm(),
                               "Ordinary least squares": OLS(),
                               "Non-negative least squares": NNLS(),
                               "Non-negativity": ConstraintNonneg(),
                               "Normalisation": ConstraintNorm(),
                               }

            try:
                c_constraints    = [constraints_lut[c_str] for c_str in c_constraints_str]
                constraints_norm = [constraints_lut[c_str] for c_str in constraints_norm_str]
            except KeyError as e:
                print(e)
                print("Constraint not implemented!")
                return


            mcrals = McrAR(max_iter       = max_iter,
                           err_fcn        = err_fcn_lof,
                           tol_increase   = tol_increase,
                           tol_n_increase = tol_n_increase,
                           st_regr='NNLS',
                           c_regr='NNLS',
                           c_constraints=[ConstraintNonneg()],
                           # st_constraints = c_constraints,
                           # c_constraints  = constraints_norm,
                           tol_err_change = 1e-30)

            self.mcrals = mcrals
            self.parameters = {"nb_compo" : nb_compo,
                               "initial_estimates_mode": initial_estimates_mode}


            self.launch_fitting()
            self.launch_gui_live_view()


    def launch_fitting(self):
        #=========================================================================
        # Threads
        #=========================================================================
        timerThread = Thread(target = self._verbose_catcher_cb, args = ())
        timerThread.daemon = True
        timerThread.start()

        myThread = Thread(target = self.fit_thread, args = ())
        myThread.daemon = True
        myThread.start()

        self._fit_thread_refs = [myThread, timerThread]

    def launch_gui_live_view(self):
        #=========================================================================
        # import GUI
        #=========================================================================
        d = uic.loadUi("plugins//mcr//live_display.ui")
        d.setWindowTitle("Multivariate Curve Resolution - live view")

        self.mcr_live_view_panel = d

        #==========================================================================
        # Creation des conteneurs
        #==========================================================================
        layout = self._create_scroll_area_and_get_scroll_layout(d)
        nb_plot_by_line = 3

        nb_loadings = self.parameters["nb_compo"]


        # =============creation et affichage data widgets========================
        for i in range(nb_loadings):

            widget = PlotDialog(edit = False, toolbar = False, options = PlotOptions(type="curve"))

            widgetName = 'plotContainer_%d_%d' % (self.gui.main.graph_refs_counter, i,)

            widget.setObjectName(widgetName)
            widget.setFixedHeight(250)

            layout.addWidget(widget, i // nb_plot_by_line, i % nb_plot_by_line)
            self.curveDialogs[i] = widget
            self.loadingWidgetNames[i] = widgetName
            #=========================================================================
            # pour eviter wrapped c/c++ object of type QwtPlotCanvas has been deleted
            #=========================================================================
            self.gui.main.save_widget_ref(widget)

        #===========================================================================
        # Conteneur pour le graph de l'erreur
        #===========================================================================
        # widget = CurveDialog(edit=False, toolbar=False)
        # widgetName = 'errorPlot'
        # widget.setObjectName(widgetName)
        # widget.setFixedHeight(250)
        # layout.addWidget(widget)
        # self.errorPlotWidget = widget
        # self.gui.main.save_widget_ref(widget)

        #===========================================================================
        # On lance l'interface
        #===========================================================================
        d.setModal(False)
        ok = d.exec_()

        # if not ok:
        #     print("Stopping threads")
        #     for thread in self._fit_thread_refs:
        #         thread._stop()


    def update_displayed_loadings(self):

        nb_loadings = self.parameters["nb_compo"]
        mcr_components = self.mcrals.ST_.T
        ds = self.mcData.datasets.getDataset()

        for i in range(nb_loadings):
            title = "Loading %i"%(i,)
            widgetName = self.loadingWidgetNames[i]
            plots.displayAPlotInCurveWidget(curveWidget_name = widgetName,
                                            title = title,
                                            x = ds["W"],
                                            y =  mcr_components[..., i],
                                            panel = self.mcr_live_view_panel)

        #Display error evolution
        errors = self.mcrals.err

        # plots.displayAPlotInCurveWidget(curveWidget_name = "errorPlot",
        #                                 title = "error evolution",
        #                                 x = range(0,len(errors)),
        #                                 y = errors,
        #                                 panel = self.mcr_live_view_panel)

        if len(errors):
            self.mcr_live_view_panel.label_error_value.setText(str(errors[-1]))

    def _create_scroll_area_and_get_scroll_layout(self, p):

        scroll_layout = QtWidgets.QGridLayout()

        # le widget qui contiendra la scrollArea
        scroll_widget = QtWidgets.QWidget()
        scroll_widget.setLayout(scroll_layout)

        # la scrollArea
        scroll_area = QtWidgets.QScrollArea()

        scroll_area.setObjectName("MCRLoadingsScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setStyleSheet("QScrollArea {background-color:white;}")

        p.gridLayout_loadings.addWidget(scroll_area)

        return scroll_layout


    def _verbose_catcher_cb(self):
        self._verbose_catcher_stop = False
        while not self._verbose_catcher_stop:
            print("Catched!")
            #print(self._verbose_catcher.getvalue())
            self.signal_displayCurrentIteration.emit()
            time.sleep(1)

    def display_current_iteration(self):

        if not hasattr(self, "mcr_live_view_panel"):
            print("live gui not launched!")
            return
        else:
            print("live gui launched!")


        try:
            mcr_components = self.mcrals.ST_.T
            nb_compo = mcr_components.shape[1]
            compo_idx = 1

            if not hasattr(self, "fig"):
                print("in 1 ")
                self.fig = pl.figure(0)
                self.ax = self.fig.add_subplot(111)
                self.line, = self.ax.plot(mcr_components[..., compo_idx])
                pl.show(False)
            else:
                print("in 2")
                self.line.clear()
                self.line.set_ydata(mcr_components[..., compo_idx])
                pl.draw()
                pl.pause(1e-17)
        except AttributeError:
            pass




    def fit_thread(self):

        print("launching fit thread")

        ds = self.mcData.datasets.getDataset()

        if self.gui.spectrums.useNormalizedData:
            X = self.gui.datasets.getDataset_X_normalized()
        else:
            X = ds["X"]

        mcrals = self.mcrals

        nb_compo = self.parameters["nb_compo"]
        initial_estimates_mode = self.parameters["initial_estimates_mode"]

        print("initial_estimates_mode:", initial_estimates_mode)

        try:
            #===============================================================================
            #
            #===============================================================================
            if initial_estimates_mode == "nb_components random":

                random_indexes = np.random.randint(ds["size"], size = nb_compo)
                random_indexes = np.sort(random_indexes)

                print("random_indexes for MCR:")
                print(random_indexes)

                initial_spectra = X[random_indexes,:]

                #with redirect_stdout(self._verbose_catcher):
                #c_first: In first iteration, solve for C first(fixed St)?
                mcrals.fit(np.array(X, dtype = float), ST = initial_spectra, verbose = True, c_first=False)

            #===============================================================================
            #
            #===============================================================================
            if initial_estimates_mode == "spectrums picked in fit tab":
                if "references_sp" in ds["metadatas"]:
                    initial_spectra = [ref for ref in ds["metadatas"]["references_sp"].values()]
                    initial_spectra = np.array(initial_spectra, dtype = float)

                    #with redirect_stdout(self._verbose_catcher):
                    mcrals.fit(np.array(X, dtype = float),
                               ST = initial_spectra,
                               verbose = True)

                else:
                    mess = "Please pick-up at least one spectrum"
                    print(mess)
                    return

        except ValueError as e:
            mess = "Can't process MCR-ALS !"
            self._verbose_catcher_stop = True
            print(mess)
            print(e)
            return

        self._verbose_catcher_stop = True
        print("MCR Fit Done!")
        self._create_and_add_projections()



    def _create_and_add_projections(self):
        # ======================================================================
        #   On prepare l'enregistrement dans le dictionnaire des projections
        # ======================================================================
        mc_logging.debug("preparing projection...")

        mcrals = self.mcrals
        mcr_components = mcrals.ST_opt_.T

        nb_compo = mcr_components.shape[1]

        print("mcr_components.shape",mcr_components.shape)
        print("mcrals.C_opt_.shape", mcrals.C_opt_.shape)

        vectors_names = ["Component %i" % (i + 1,) for i in range(nb_compo)]

        print("vectors_names:", vectors_names)

        vectors = dict()
        values  = dict()

        print("debug")
        reconstructed_spectra = np.dot(mcrals.C_opt_,mcr_components.T)
        reconstructed_spectra_areas = np.sum(reconstructed_spectra,axis = 1)


        for compo_idx, v_name in enumerate(vectors_names):
            self.gui.main.displayProgressBar(100.0 * compo_idx / len(vectors_names))

            vectors[v_name] = mcr_components[...,compo_idx]

            # ================================================================================================
            # Quantification
            # ================================================================================================
            Ci  = mcrals.C_opt_[..., compo_idx, np.newaxis]
            SiT = mcr_components[..., compo_idx, np.newaxis].T
            component_contributions = np.dot(Ci, SiT)
            component_contributions_areas = np.sum(component_contributions, axis=1)

            quantitative_values_for_compo_i = np.divide(component_contributions_areas, reconstructed_spectra_areas)
            # ================================================================================================

            values[v_name] = quantitative_values_for_compo_i

        self.gui.main.resetProgressBar()

        mc_logging.debug("insert Projection in dict")
        # =====================================================================
        #      On insere  dans le dictionnaire des projections
        # =====================================================================
        self.gui.projections.insertProjectionInDatasetDict("MCR",
                                                           vectors_names,
                                                           vectors,
                                                           values,
                                                           parameters_names = [],
                                                           parameters_values = [],
                                                           parameters_units = [],
                                                           order_by = '',
                                                           override = True)

        mc_logging.debug("Projection insertion done")

        #======================================================================
        #  Affichage par defaut
        #======================================================================
        self.gui.representations.signal_updateRepresentationDisplay.emit("MCR", vectors_names[0], True)


        # =====================================================================
        #                 Affichage projection 2D
        # =====================================================================
        self.gui.projections.setCurrentProjection("MCR")
        #self.gui.projections.updateCurrentProjection()
        self.gui.projections.signal_update2DProjectionPlot.emit()