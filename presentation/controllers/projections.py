import random
from functools import partial

import numpy as np
import qwt as Qwt
from PyQt5 import QtWidgets
from PyQt5 import uic
from PyQt5.QtCore import QPointF
from PyQt5.QtCore import Qt
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QFileDialog

from PyQt5.QtGui import QFont
from PyQt5.QtGui import QPolygonF

import plotpy

from plotpy.plot import PlotDialog, PlotOptions
from plotpy.builder import make
from plotpy.tools import PointTool, FreeFormTool, SelectPointTool


from helpers import mc_logging
from helpers.bigDataTools import getChunkSize
from helpers.data import singleton
from helpers.plots import plots
from helpers.plots.plots import getItemsInPlotMatchingName
from presentation.controllers import main, signals, spectrums, representations

import h5py
import helpers
from helpers.dialogs import InputDialogText


@singleton
class MCPresentationController_projections(QObject):


    signal_updateProjectionList = pyqtSignal()
    signal_update2DProjectionPlot = pyqtSignal()
    signal_updateCurrentProjection = pyqtSignal()


    projectionTab = dict()


    def __init__(self, qt_panel, mcBusinessLogic, mcData, mainWindow):
        super().__init__()
        print(type(self).__name__ + " initialized (id:{})".format(id(self)))

        self.panel  = qt_panel
        self.bl     = mcBusinessLogic
        self.mcData = mcData
        self.mainWindow = mainWindow

        self.spectrums = spectrums.MCPresentationController_spectrums(qt_panel, mcBusinessLogic, mcData, mainWindow)
        self.main = main.MCPresentationController_main(qt_panel, mcBusinessLogic, mcData, mainWindow)
        self.signals   = signals.MCPresentationController_signals()
        self.representations = representations.MCPresentationController_representations(qt_panel, mcBusinessLogic, mcData, mainWindow)

        self.init2DProjectionView()
        # self.view  = mcPresentationView
        # self.model = mcPresentationModel



    def makeConnections(self):
        print("inside makeConnections in MCPresentationController_projections")
        p = self.panel

        self.signal_updateProjectionList.connect(self.updateProjectionList)
        self.signal_update2DProjectionPlot.connect(self.update2DProjectionPlot)
        self.signal_updateCurrentProjection.connect(self.updateCurrentProjection)

        p.combo_representations_family.currentIndexChanged.connect(self.updateCurrentProjection)

        p.comboBox_vectorOnX.setEnabled(False)
        p.comboBox_vectorOnY.setEnabled(False)

        p.comboBox_vectorOnX.currentIndexChanged.connect(self.update2DProjectionPlot)
        p.comboBox_vectorOnY.currentIndexChanged.connect(self.update2DProjectionPlot)

        p.button_importProjection.clicked.connect(self.importProjection)


    def makeConnections_menuItems(self):

        p = self.panel

        p.combo_dispSpectrums.currentIndexChanged.connect(
            partial(self.signals.signal_spectrumsToDisplayChanged.emit, []))

        p.combo_std_deviation.currentIndexChanged.connect(
            partial(self.signals.signal_spectrumsToDisplayChanged.emit, []))

        p.combo_projections.currentIndexChanged.connect(lambda val: self.updateCurrentProjection())
        # temporaire, mise a jour de l'affichage des vecteur de base quand le nbr de composantes demandées change
        p.selectedBaseVectorsNb.returnPressed.connect(self.selectedProjectionVectorsChanged)
        p.showSelectedBaseVectorsDialog.clicked.connect(self.chooseSelectedProjectionVectors)


    def getExplorerWidgetRef(self):
        return self.projectionTab["explorerWidget"]

    def init2DProjectionView(self):
        """
        Cette methode crée le graph qui contiendra les projections en 2D
        Et connect les combo de choix des axes aux methodes de mise a jour
        """
        print("===== Clouds tab initialisation =====")

        p = self.panel

        # =======================================================================
        #     Creation des widgets cloud et spectrum explorer
        # =======================================================================
        layout = p.cloudsLayout

        widget1 = PlotDialog(edit = False, toolbar = True, options=PlotOptions(type="curve"))
        widget1.setObjectName('plotContainer_cloud')

        widget2 = PlotDialog(edit = False, toolbar = False, options=PlotOptions(type="curve"))
        widget2.setObjectName('plotContainer_spectrumExplorer')

        layout.addWidget(widget1, 1, 0)
        layout.addWidget(widget2, 1, 1)

        self.main.save_widget_ref(widget1)
        self.main.save_widget_ref(widget2)

        self.projectionTab["cloudWidget"]    = widget1
        self.projectionTab["explorerWidget"] = widget2

        self.makeConnections_menuItems()

        # p.combo_currentSelectionGroup.currentIndexChanged.connect(self.gui.signals.signal_spectrumsToDisplayChanged)


        # =======================================================================
        #                   Creation des curves
        # =======================================================================
        plot = self.get2DProjectionCurvePlot()

        # ========================   All points   ===============================

        curve1 = make.curve([], [],
                            color = "green",
                            linestyle = "NoPen",
                            marker = "o",
                            markersize = self.main.marker_size,
                            markerfacecolor = "red",
                            markeredgecolor = "black",
                            title = "all_points")

        plot.add_item(curve1)

        bottom_axis_id = plot.get_axis_id("bottom")

        plot.set_axis_unit(bottom_axis_id, "u.a.")

        plot.replot()

        # =========================   References   ==============================
        self.projectionTab["curve_all_points"] = curve1


        # =======================================================================
        #                               Outils de selection
        # =======================================================================

        selectTool = widget1.manager.add_tool(SelectPointTool,
                                              title = "Selection",
                                              on_active_item = False,
                                              mode = "create",
                                              end_callback = self.pickerSelectionChanged_inCloud)

        selectTool.activate()

        freeFormTool = widget1.manager.add_tool(FreeFormTool,
                                                title = "Selection",
                                                handle_final_shape_cb = self.freeFormSelectionChanged_inCloud)


        # =================freestyle======================================


    def updateGroupsDisplayDatas(self):
        """
        Cette methode met à jour l'affichage des selections sur la representation
        image du jdd et appel la mise a jours de l'affichage des groupes et
        du spectre en cours
        TODO: Changer le type d'affichage en fonction du nombre de points dans
        le groupe et/ou affiché a l'ecran en fonction de xy_range pour ne pas
        surcharger l'affichage
        """
        mc_logging.debug("---inside updateGroupsDisplayDatas_inProjection---")

        ds = self.mcData.datasets.getDataset()

        groups = ds["groups"]

        proj_name       = self.getProjectionNameInGui()
        proj_curvePlot  = self.get2DProjectionCurvePlot()
        proj_curveItems = self.get2DProjectionGroupsCurveItems()

        # =======================================================================
        # On les affiche en surimpression sur le cloud
        # =======================================================================
        display_on_2DProjectionPlot = False

        if proj_name in ds["projections"]:

            datasX, datasY, proj, vectorXName, vectorYName = self.get2DProjectionDatasOfSelectedVectorsInGUI()

            # on s'assure qu'une projection existe avant l'affichage
            if len(datasX) > 0: display_on_2DProjectionPlot = True

        # =====================================================================
        #     On affiche en surrimpression sur projection
        # =====================================================================
        for group_name, group in groups.items():

            selected_idxs = group["indexes"]

            # ==================================================================
            # Limitation de l'affichage en attendant subsampling par zoom
            # ==================================================================

            selected_idxs = group["indexes"]

            max_points_to_display = self.main.limits.max_points_on_curves

            if len(selected_idxs) > max_points_to_display:
                mc_logging.info("too many points to display (%d), limiting to %d (random selection)" % (
                len(selected_idxs), max_points_to_display))

                # selected_idxs = selected_idxs[::int(1.0 * len(selected_idxs) / max_points_to_display)]
                print("before random selection")
                selected_idxs = random.sample(selected_idxs, max_points_to_display)
                print("after random selection")

            selected_idxs = sorted(selected_idxs)

            # ==================================================================
            curve_title = '"%s" group' % (group_name,)

            if curve_title in proj_curveItems and display_on_2DProjectionPlot:
                curve = proj_curveItems[curve_title]
                # print("before setdata")
                curve.set_data(datasX[selected_idxs], datasY[selected_idxs])
                # print("after setdata")


            elif display_on_2DProjectionPlot:
                print("%s not in proj_curveItems!" % (curve_title))


        proj_curvePlot.replot()


    def updateProjectionList(self):

        print("inside updateProjectionList")

        p = self.panel

        ds_name = self.mcData.datasets.currentDatasetName
        ds      = self.mcData.datasets.getDataset(ds_name)

        s = p.combo_projections
        s.clear()

        items = [pr_name for pr_name in list(ds["projections"].keys())]

        s.addItems(items)


    def get2DProjectionDatasOfSelectedVectorsInGUI(self):
        """
        Convenient method to retrieve dataX,DataY of selected baseVector on GUI
        for selected projection in GUI
        return dataX,dataY,ds["projections"][proj_name],vectorXName,vectorYName,vectorX_idx,vectorY_idx
        """

        p = self.panel

        proj = self.getCurrentProjection()

        default_return = [], [], {}, '', ''

        if not proj: return default_return

        vectorXName = p.comboBox_vectorOnX.currentText()
        vectorYName = p.comboBox_vectorOnY.currentText()

        if not vectorXName or not vectorYName: return default_return

        try:
            vectorX_idx = proj["vectors_names"].index(vectorXName)
            vectorY_idx = proj["vectors_names"].index(vectorYName)

        except ValueError as e:
            print("ValueError:", e)
            return default_return

        # print "vectorX_idx,vectorY_idx", vectorX_idx, vectorY_idx
        # vectorZ_idx = proj["vectors_names"].index(vectorZName)

        dataX = proj["values"][:, vectorX_idx]
        dataY = proj["values"][:, vectorY_idx]

        return dataX, dataY, proj, vectorXName, vectorYName


    def getCurrentProjection(self):
        # p = self.gui.panel

        ds_name = self.mcData.datasets.currentDatasetName
        ds      = self.mcData.datasets.getDataset(ds_name)
        proj_name = self.getProjectionNameInGui()

        if proj_name not in ds["projections"]: return None

        return ds["projections"][proj_name]


    def getProjectionNameInGui(self):
        """
        Getter GUI
        """
        p = self.panel
        name = str(p.combo_projections.currentText())
        return name


    def get2DProjectionCurvePlot(self):
        return self.projectionTab["cloudWidget"].get_plot()
            # return self.gui.representations.representationTab["imageItem"]


    def get2DProjectionGroupsCurveItems(self):
        plot = self.get2DProjectionCurvePlot()
        return getItemsInPlotMatchingName(plot, "group")


    def updateDisplayedSpectrums(self, spectrum_indexes = []):

        widget_ref = self.getExplorerWidgetRef()
        ds_name = self.mcData.datasets.currentDatasetName

        #TODO: decoupler
        self.spectrums.updateDisplayedSpectrumsInWidgetByDsName(widget_ref,
                                                                ds_name,
                                                                spectrum_indexes)
                                                                #autoselect_indexes = True)

    #@my_pyqtSlot()
    def update2DProjectionPlot(self):
        """
        Cette methode met a jour le plot container avec la projection des scores
        sur les vecteurs PCN en x et PCM en y

        TODO: utiliser current_projection_name au lieu de PCA
        """

        print("update2DProjectionPlot")

        # ======================================================================
        #                            affichage data widgets
        # =======================================================================
        datasX, datasY, proj, vectorXName, vectorYName = self.get2DProjectionDatasOfSelectedVectorsInGUI()

        #=======================================================================
        #                           Si plot 2D
        #=======================================================================

        # ======== Mise a jour du titre du graph: PCy = f(PCy) ==============

        plot = self.get2DProjectionCurvePlot()

        txt = "%s = f(%s)" % (vectorYName, vectorXName)

        title = Qwt.QwtText(txt)

        title.setFont(QFont('DejaVu', 8, QFont.Light))

        # plot.setTitle(title)

        plot.set_titles(title,
                        xlabel = "%s" % (vectorXName,),
                        ylabel = "%s" % (vectorYName,))

        # =======================================================================


        #========================================================================
        #                  Plot de tous les points
        #=========================================================================
        curve1 = self.projectionTab["curve_all_points"]

        if len(datasX) > self.main.limits.max_points_on_curves:
            mc_logging.info("points number over limits, limiting to %d (random selection)" % (self.main.limits.max_points_on_curves))
            selected_idxs = sorted( random.sample(range(len(datasX)), self.main.limits.max_points_on_curves))
            curve1.set_data(datasX[selected_idxs], datasY[selected_idxs])
        else:
            curve1.set_data(datasX, datasY)
        # =======================================================================

        # ====================Plot des points selectionnes=======================
        self.signals.signal_groupsUpdated.emit()
        # =======================================================================

        plot.do_autoscale()
        plot.replot()


    def update2DProjectionOptionsOnProjectionChange(self):

        p = self.panel

        ds_name = self.mcData.datasets.currentDatasetName

        ds = self.mcData.datasets.getDataset(ds_name)

        proj_name = self.getProjectionNameInGui()

        mc_logging.debug("inside updateCloudsTabOnProjectionChange")

        if not proj_name:

            p.comboBox_vectorOnX.setEnabled(False)
            p.comboBox_vectorOnY.setEnabled(False)
            p.comboBox_vectorOnZ.setEnabled(False)

        else:

            p.comboBox_vectorOnX.setEnabled(True)
            p.comboBox_vectorOnY.setEnabled(True)

        if proj_name not in ds["projections"]: return

        proj = ds["projections"][proj_name]

        for comboBox in (p.comboBox_vectorOnX, p.comboBox_vectorOnY):
            comboBox.blockSignals(True)

            comboBox.clear()
            if len(proj["vectors_names_selected"])>0:
                comboBox.addItems(proj["vectors_names_selected"])

            comboBox.blockSignals(False)

    def setCurrentProjection(self, proj_name):
        p = self.panel
        i = p.combo_projections.findText(proj_name)
        p.combo_projections.setCurrentIndex(i)

    def updateCurrentProjection(self):
        """
        Cette methode met a jour l'onglet projection_base en affichant l'ensemble
        des vecteurs de base "vectors_names_selected"
        Elle demande egalement la mise à jour des options disponibles pour
        l'affichage des projections en plot2D

        """

        p = self.panel

        ds_name   = self.mcData.datasets.currentDatasetName
        ds        = self.mcData.datasets.getDataset(ds_name)
        proj_name = self.getProjectionNameInGui()

        mc_logging.debug("inside updateCurrentProjection for '%s'" % (ds_name,))

        # suppression des widgets existants
        self.clean_all_plots_in_projectionTab()


        if not proj_name or proj_name not in ds["projections"]:
            return

        proj = ds["projections"][proj_name]

        # pour avoir des refs uniques a chaque creation
        self.main.graph_refs_counter = self.main.graph_refs_counter + 1

        # ======================================================================
        #
        # ======================================================================

        vectors_names_selected = proj.get("vectors_names_selected", [])

        vectors = proj["vectors"]

        # ======================================================================
        #                Scroll Area contenant les plots
        # ======================================================================
        nb_plot_by_line = 3

        # Le layout du scrollWidget
        scroll_layout = self.create_scroll_area_in_projectionTab_and_get_scroll_layout()


        # =============creation et affichage data widgets========================
        for i, vector_name in enumerate(vectors_names_selected):

            widget = PlotDialog(edit = False, toolbar = False, options = PlotOptions(type="curve"))

            widgetName = 'plotContainer_%d_%d' % (self.main.graph_refs_counter, i,)

            widget.setObjectName(widgetName)
            widget.setFixedHeight(250)


            scroll_layout.addWidget(widget, i // nb_plot_by_line, i % nb_plot_by_line)

            #=========================================================================
            # pour eviter wrapped c/c++ object of type QwtPlotCanvas has been deleted
            #=========================================================================
            self.main.save_widget_ref(widget)


            # ===on vas afficher en complement d'information les valeurs des parametres facultatifs
            additional_info = ''

            # on recupere la position du vecteur selectionné dans la liste original de tous les vecteurs

            # print "debug, type(proj['vectors_names'])",type(proj["vectors_names"])
            # print "proj['vectors_names']",proj["vectors_names"]


            # hack rapide, au chargement d'un projet hdf5 proj["vectors_names"

            # devient un ndarray, .index ne marche donc plus
            #print("vector_name:",vector_name)
            #print(proj["vectors_names"])
            v_idx = proj["vectors_names"].index(vector_name)

            for j, param_name in enumerate(proj["parameters_names_list"]):

                # valeurs des parametres associées à ce vecteur

                param_value = proj["parameters_values"][v_idx][j]

                param_unit = proj["parameters_units"][j]

                if param_value == np.nan: continue

                if np.issubdtype(type(param_value), float):

                    str_value = "%.2f" % (param_value,)

                else:
                    str_value = param_value


                #TODO: Erreur "can't convert 'bytes' to str à corriger -> OK maintenant?
                try:
                    #additional_info += " - %s : %s" % (param_name, str_value) + param_unit
                    additional_info += " - {} : {} {}".format(param_name, str_value, param_unit)
                except Exception as e:
                    mc_logging.error("Encoding error TODO")
                    mc_logging.error(e)
                    mc_logging.error(param_name)
                    mc_logging.error(str_value)
                    mc_logging.error(param_unit)
                    mc_logging.error(type(param_name))
                    mc_logging.error(type(str_value))
                    mc_logging.error(type(param_unit))
            # ==================================================================

            vector_name = str(vector_name)
            #print("type(vector_name)", type(vector_name))
            #print("type(additional_info)", type(additional_info))
            title = vector_name + additional_info

            vector = vectors[vector_name]

            plots.displayAPlotInCurveWidget(curveWidget_name = widgetName,
                                            title = title,
                                            x = ds["W"],
                                            y = vector,
                                            panel = p)

            plot = plots.getPlotByWidgetName(widgetName, p)

            self.spectrums.addLabelsOnPlot(plot)

            # on attache un calback affichant la representation associé au vecteur

            #print("connecting:",widget.get_plot())
            callback_fnc = partial(self.doubleClick_onProjection,
                                   proj_name = proj_name,
                                   vector_name = vector_name,
                                   gotoTab = True)

            widget.get_plot().mouseDoubleClickEvent = callback_fnc
        # ======================================================================
        #  Fin scroll Area
        # ======================================================================

        self.update2DProjectionOptionsOnProjectionChange()


    #TODO: decoupler projection et representation
    def doubleClick_onProjection(self, event, proj_name, vector_name, gotoTab):
        self.representations.signal_updateRepresentationDisplay.emit(proj_name, vector_name, gotoTab)


    def clean_all_plots_in_projectionTab(self):

        p = self.panel

        scroll_area = p.findChild(QtWidgets.QScrollArea, name = "projectionTabScrollArea")

        if scroll_area:

            layout = scroll_area.widget().layout()

            #print("Removing plots inside gridLayoutProjectionTab")
            for __ in range(layout.count()):
                item = layout.takeAt(0)
                #pour eviter les underliing c++ object has been deleted
                #on supprime tous les elements un par un avant de supprimer le conteneur
                item.widget().get_plot().disconnect()
                item.widget().deleteLater()
            #print("done")

        #print("Removing gridLayoutProjectionTab")
        #print("count", p.gridLayout_projectionTab.count())

        for __ in range(p.gridLayout_projectionTab.count()):
            item = p.gridLayout_projectionTab.takeAt(0)
            item.widget().disconnect()
            item.widget().deleteLater()


    def create_scroll_area_in_projectionTab_and_get_scroll_layout(self):

        p = self.panel

        scroll_layout = QtWidgets.QGridLayout()

        # le widget qui contiendra la scrollArea
        scroll_widget = QtWidgets.QWidget()
        scroll_widget.setLayout(scroll_layout)

        # la scrollArea
        scroll_area = QtWidgets.QScrollArea()

        scroll_area.setObjectName("projectionTabScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setStyleSheet("QScrollArea {background-color:white;}")

        # le layout principal de l'onglet
        p.gridLayout_projectionTab.addWidget(scroll_area)

        return scroll_layout


    def pickerSelectionChanged_inCloud(self, tool):
        """
        Methode appellée en cliquant sur un point du cloud.
        Elle vas chercher le point du jdd le plus proche du jdd et l'ajouter/supprimer
        au groupe de selection en cours
        """

        print("inside pickerSelectionChanged_inCloud")

        # ==================recuperation des variables===========================

        p = self.panel

        ds_name = self.mcData.datasets.currentDatasetName

        ds = self.mcData.datasets.getDataset(ds_name)

        if self.getCurrentProjection() is None: return

        currentGroup = self.bl.groups.getCurrentGroup()

        print("currentGroup:", currentGroup)

        if currentGroup:
            group = ds["groups"][currentGroup]


        plot = self.get2DProjectionCurvePlot()

        # =======================================================================

        # click en coordonnées data

        plotX, plotY = tool.get_coordinates()

        dataIdx = self.get_closest_point_index_from_coordinates_in_current_2D_projection(plotX, plotY)


        # ============ Mise Ã  jour du graph du spectre en cour ==================

        self.mcData.currentSpectrumIndex = int(dataIdx)  # dataIdx[0]

        self.signals.signal_spectrumsToDisplayChanged.emit([])
        # =======================================================================


        # =======================================================================
        #        Mise a jour de la selection si un groupe est selectionne
        # =======================================================================

        if currentGroup:

            # ==on met un flag sur le spectre cliqué en fonction de son groupe===
            idx = dataIdx  # dataIdx[0][0]

            # ======== on ajoute si absent, on supprime si present ==============
            add_or_remove = str(p.combo_selectionType.currentText())

            if add_or_remove == "add":
                self.bl.groups.addPointsToGroup(currentGroup, ds_name, idx, ds["xys"][idx])

            elif add_or_remove == "remove":
                self.bl.groups.removePointsFromGroup(currentGroup, ds_name, idx, ds["xys"][idx])
            # ===================================================================

            # ===========En surrimpression on met les point "selected"===========
            self.signals.signal_groupsUpdated.emit()
            # ===================================================================


    def freeFormSelectionChanged_inCloud(self, shape):

        """
        Methode appellée lors de la confirmation d'un groupe au lasso
        (appuis sur entrer aprés avoir commencé la forme)
        """

        print("inside freeFormSelectionChanged_inCloud")

        # ==================recuperation des variables===========================

        p = self.panel

        ds_name = self.mcData.datasets.currentDatasetName
        ds      = self.mcData.datasets.getDataset(ds_name)
        currentGroup = self.bl.groups.getCurrentGroup()

        print("freeform on cloud")

        plot = self.get2DProjectionCurvePlot()

        datasX, datasY, _, _, _ = self.get2DProjectionDatasOfSelectedVectorsInGUI()

        print("currentGroup:", currentGroup)

        # =======================================================================
        # on prend le bounding rect de la forme pour reduire le nombre de
        # test "inside polygone"

        shape_points = shape.get_points()

        xmin, xmax = min(shape_points[:, 0]), max(shape_points[:, 0])
        ymin, ymax = min(shape_points[:, 1]), max(shape_points[:, 1])

        # ============indices des points dans le bounding rect==================


        condition_x_1 = datasX >= xmin
        condition_x_2 = datasX <= xmax
        condition_y_1 = datasY >= ymin
        condition_y_2 = datasY <= ymax

        dataIdxs = np.where(condition_x_1 & condition_x_2 & condition_y_1 & condition_y_2)

        points_inside_bounding_rect = dataIdxs[0]

        # ================ Test d'appartenance au polygone ======================
        """
        on "convertit" notre polygone en QPolygonF pour pouvoir utiliser
        la methode poly.containsPoint(QPointF)
        """

        poly = QPolygonF()

        for pt in shape_points: poly.append(QPointF(pt[0], pt[1]))

        points_inside_shape = [idx for idx in points_inside_bounding_rect if
                               poly.containsPoint(QPointF(datasX[idx], datasY[idx]), Qt.OddEvenFill)]

        plot.del_item(shape)

        # =======================================================================
        # =       Mise a jour de la selection si un groupe est selectionne     ==
        # =======================================================================

        if currentGroup:

            add_or_remove = str(p.combo_selectionType.currentText())

            if add_or_remove == "add":
                self.bl.groups.addPointsToGroup(currentGroup, ds_name, points_inside_shape, ds["xys"][points_inside_shape])

            elif add_or_remove == "remove":
                self.bl.groups.removePointsFromGroup(currentGroup, ds_name, points_inside_shape, ds["xys"][points_inside_shape])

            else:
                pass

            # ===========En surrimpression on met les point "selected"===========
            self.signals.signal_groupsUpdated.emit()
            # ===================================================================


    def get_closest_point_index_from_coordinates_in_current_2D_projection(self, plotX, plotY):

        # 5print "plotX, plotY=", plotX, plotY
        #        print imagePlot.items
        #
        # item = plot.get_items(item_type=ICurveItemType)[0]
        #
        # coordonnÃ©es du point le plus proche du click dans les datas
        # !  get_closest_coordinates ne semble pas fonctionner correctement
        # On utilise donc une methode faite maison
        # dataX, dataY = item.get_closest_coordinates(plotX,plotY)

        """
        print("dataX, dataY=", datasX, datasY)

        #on cherche l'indice du point de coordonnÃ©es dataX,dataY

        condition_x = datasX==dataX
        condition_y = datasY==dataY

        dataIdx = np.where(condition_x & condition_y)

        """

        # dataIdx = [1, 0]

        datasX, datasY, _, _, _ = self.get2DProjectionDatasOfSelectedVectorsInGUI()

        array = np.concatenate((datasX[:, np.newaxis], datasY[:, np.newaxis]), axis = 1)

        sq_diffs = np.power(array - np.array([plotX, plotY]), 2)

        sq_dist = np.sqrt(np.sum(sq_diffs, axis=1))

        dataIdx = np.argmin(sq_dist)

        # print "Distlist:",sq_dist
        # print "IDX:",dataIdx

        dataX, dataY = datasX[dataIdx], datasY[dataIdx]

        print("dataX, dataY=", dataX, dataY)

        return dataIdx


    def chooseSelectedProjectionVectors(self):

        """
        Cette methode ouvre une GUI permetant de selectionner les vecteurs de base
        à afficher ou à utiliser pour du fit par exemple (vectors_names_selected)
        """

        ds = self.mcData.datasets.getDataset()

        proj_name = self.getProjectionNameInGui()

        if proj_name not in ds["projections"]:
            print(("error, '%s' not in projection list" % (proj_name,)))

            return 0

        proj = ds["projections"][proj_name]

        # ====import GUI====================================

        d = uic.loadUi("assets//ui_files//multiple_choice_from_list.ui")

        d.setWindowTitle("Please select vector(s) to display")

        # ======= On remplit la listBox avec les vecteurs disponibles ==========
        d.list_availableItems.addItems(proj["vectors_names"])

        for i in range(d.list_availableItems.count()):

            vector_name_selected = d.list_availableItems.item(i).text()

            # on preselectionne les vecteurs dejas selectionnées
            if vector_name_selected in proj["vectors_names_selected"]:
                d.list_availableItems.item(i).setSelected(True)

        ok = d.exec_()

        # ============= On recupere les donnÃ©es de la gui =======================

        if ok:
            requested_selected_vectors_names = [str(d.list_availableItems.item(i.row()).text()) for i in

                                                d.list_availableItems.selectedIndexes()]

            proj["vectors_names_selected"] = requested_selected_vectors_names

        self.representations.createRepresentationsForVectorsInSelectedVectorsList()

        print("===========================EMIT2=================================")
        self.signal_updateCurrentProjection.emit()
        print("==========================ENDEMIT2===============================")


    def selectedProjectionVectorsChanged(self):

        print("selectedProjectionVectorsChanged")

        p = self.panel

        ds_name = self.mcData.datasets.currentDatasetName

        ds = self.mcData.datasets.getDataset(ds_name)

        proj_name = self.getProjectionNameInGui()

        if not proj_name: return

        max_proj_vectors_nb = int(p.selectedBaseVectorsNb.text())

        proj = ds["projections"][proj_name]

        proj["vectors_names_selected"] = proj["vectors_names"][0:max_proj_vectors_nb]

        self.representations.createRepresentationsForVectorsInSelectedVectorsList()

        print("=========================EMIT3=========================")
        self.signal_updateCurrentProjection.emit()
        print("=======================ENDEMIT3========================")


    def insertProjectionInDatasetDict(self, name, vectors_names, vectors, values, parameters_names = [],
                                      parameters_values = [], parameters_units = [], order_by = '', override = True):

        """
        insert a projection in ds["projections"] dict()

        p = ds["projections"][name]

        p["vectors_names"] = list(): liste des noms des vecteurs propres
        p["vectors_names_selected"] = list(): liste des noms des vecteurs propres à utiliser

        pour la projection, on peux restreindre par exemple aux N premieres PCs

        ex: p["vectors_names"] = ["mean spectrum","PC0","PC1","PC2","PC3"]

        p["vectors"] = dict(): dictionnaire des vecteurs propres de tailles X[0,:]

        ex:
            p["vectors"]["mean spectrum"] = mean_spectrum
            p["vectors"]["PC0"] = PC0
            ...

        p["values"] = list(): liste de liste de taille len(dataset) comprenant les projections

        sur les vecteurs propres sous forme de liste

        p["values_by_vector"]    = dict() : dictionnaire de liste de coefficient de taille len(dataset)
        p["values_by_vector"][vector_name] = list()
        p["parameters_names_list"] = list(): Liste de parametres servant à qualifier/ trier les vecteurs de base ["variance","poids", "% total"] etc...
        p["order_by"] = un element de "parameters_names_list", si pas specifié, en prend l'ordre de remplissage de "selected_vectors"
        p["parameters_values"] = list de meme taille de "vectors_names" contenant des liste de valeurs (taille de parameters_names_list)
        p["parameters_units"] = list de str de la taille de "parameters_names_list" contenant les unitées ex: ["%","%m", "ua",""]
        p["parameters_by_vector"][vector_name] = list()


        ex:
            p["values_by_vector"]["PC0"]              = [0.56,256,12,.......,145]
            p["values_by_vector"]["PC1"]              = [0.60,125,87,.......,85]

            p["values"][0]  = [1,0.56,0.25,0,0]
            p["values"][1]  = [1,0.60,0.18,0,5663]

            ...

        len(p["values_by_vector"][x]) = len(dataset)
        len(p["values_by_vector"]) = len(p["vectors"]) = len(p["vectors_names"])

        """

        ds_name = self.mcData.datasets.currentDatasetName

        ds = self.mcData.datasets.getDataset(ds_name)

        p = self.panel

        # ========================== test inputs ==============================#
        # !TODO, tester les inputs


        default_vector_number_selected = int(p.selectedBaseVectorsNb.text())

        proj = dict()

        proj["vectors_names_selected"] = vectors_names[0:min(default_vector_number_selected,
                                                             len(vectors_names))]  # par default les 20 premiers...

        proj["vectors_names"] = vectors_names
        proj["vectors"] = vectors
        proj["values_by_vector"] = values

        projValuesHolder = self.bl.io.workFile.getTempHolder((ds["size"], len(vectors_names)))

        print("filling projValuesHolder")

        chunk_size = getChunkSize((ds["size"], len(vectors_names)))

        print("chunk_size:", chunk_size)

        for i in range(0, ds["size"], chunk_size):
            i_min = i
            i_max = min(i_min + chunk_size, ds["size"])

            chunk = np.array([[values[v_name][j] for v_name in vectors_names] for j in range(i_min, i_max)])

            projValuesHolder[i_min:i_max] = chunk

            self.main.displayProgressBar(100.0 * i / ds["size"])

        print("filling done")

        self.main.resetProgressBar()

        proj["values"] = projValuesHolder

        # ======================================================================
        # partie parametres comme variance etc...
        # ======================================================================

        # TODO, c'est tres moche...

        if len(parameters_names) and len(parameters_values) and len(parameters_units):

            print("adding parameters values...")

            proj["parameters_names_list"] = parameters_names
            proj["order_by"] = order_by  # pas utilisé pour l'instant
            proj["parameters_values"] = parameters_values
            proj["parameters_units"] = parameters_units

        else:

            print("parameters values empty")
            proj["parameters_names_list"] = []
            proj["order_by"] = ''
            proj["parameters_values"] = [[] for __ in range(len(vectors_names))]
            proj["parameters_units"] = ['' for __ in range(len(parameters_names))]

        # ======================================================================

        # ==================== On insert dans le dataset ======================#
        if name in ds["projections"] and not override:
            print('Error: Projection "%s" already exists')
            return

        else:
            print('"%s" inserted into projection dict()' % (name))
            ds["projections"][name] = proj

        # =====================================================================#
        # =====================================================================#

        # ======= On met a jour la liste des projection dans la GUI  ==========#
        self.signal_updateProjectionList.emit()

        # ============= On creer les representations associées  ===============#
        self.representations.createRepresentationsForVectorsInSelectedVectorsList(projection_name = name)


    def importProjection(self):
        """
        import projection from an external container
        Container can be a  matlab .mat or hdf5 .h5 with following keys:
        - vectors: base vectors where values are projected, each vector must have size(W)
        - vectors_names: str array/list of size len(vectors)
        - values: array of size(current dataset) * len(vectors)
        - parameters_names/values/units: optional
        """
        p = self.panel
        mc_logging.debug("Importing a projection in current dataset")

        ds = self.mcData.datasets.getDataset()

        # TODO: ici on pourrais mettre '*_proj.h5'
        filename = QFileDialog.getOpenFileName(p, "Open Projection File..." , '(MAT file) *.mat;;(HDF5 file) *.h5')[0]
        filename = str(filename)

        print(filename)

        if not filename:
            print("No file selected")
            return

        with h5py.File(filename, 'r') as f:

            keys = list(f.keys())

            #=================================================================
            # Check Keys
            #=================================================================
            if not all([k in keys for k in ["values","vectors"]]):
                key_error_mess = "Mat file must have at least 'vectors' and 'values' keys"

                QtWidgets.QMessageBox.information(self.mainWindow,
                                                  'Import error',
                                                  key_error_mess)
                return

            values  = f["values"][:]
            vectors = f["vectors"][:]

            # TODO: Probleme avec vector name impossible à lire/ecrire une liste de string avec Matlab!
            # on n'inclus donc pas le champ vector_names et on genere ici une liste arbitraire...
            if 'vector_names' in f:
                try:
                     vectors_names = f["vector_names"][:,0]
                except Exception:
                     vectors_names = f["vector_names"][:]

                vectors_names = helpers.data.convertBytesToStr(vectors_names)
                vectors_names = list(vectors_names)
            else:
                vectors_names = ["vector #{}".format(i) for i in range(vectors.shape[0])]

            vectors_count         = vectors.shape[0]
            vectors_spectral_size = vectors.shape[1]
            vectors_names_count   = len(vectors_names)
            values_count          = values.shape[0]
            values_spectral_size  = values.shape[1]


            #=================================================================
            # Check Sizes
            #=================================================================
            try:
                assert(vectors_spectral_size == len(ds["W"]))
                assert(values_spectral_size == vectors_names_count)
                assert(vectors_count == vectors_names_count)

            except AssertionError as e:
                print(e)
                size_error_mess  = "vectors size must be N*%d (current %d*%d)\n" % (len(ds["W"]), vectors_count, vectors_spectral_size)
                size_error_mess += "vectors_names size must be N (current %d)\n" % (vectors_names_count)
                size_error_mess += "values size must be %d*N (current %d*%d)" % (ds["size"],values_count,values_spectral_size)

                QtWidgets.QMessageBox.information(self.mainWindow,
                                                  'Import error',
                                                  size_error_mess)
                return


        #===================================================================
        # conversion array vers dictionnaire
        #===================================================================

        values_dict = {k:values[:, i] for (i, k) in enumerate(vectors_names)}
        vectors     = {k:vectors[i, :] for (i, k) in enumerate(vectors_names)}


        dialog = InputDialogText(p)
        projection_name, ok = dialog.getText("Projection import...",
                                             "Enter a name:")



        if ok and projection_name:

            self.insertProjectionInDatasetDict(projection_name,
                                               vectors_names,
                                               vectors,
                                               values_dict,
                                               order_by = '',
                                               override = True)
                                                # parameters_names,
                                                # parameters_values,
                                                # parameters_units,