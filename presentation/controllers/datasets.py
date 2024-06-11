from functools import partial
from threading import Thread

import numpy as np
from PyQt5 import QtGui, QtWidgets
from PyQt5 import uic
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5 import QtCore
from PyQt5.QtGui import QFont, QColor, QBrush, QPainter


from helpers import mc_logging
from helpers.bigDataTools import normalizeHDF5, getMean
from helpers.data import singleton
from helpers.plots import plots
from presentation.controllers import main, representations, spectrums, groups, signals, projections


@singleton
class MCPresentationController_datasets(QObject):

    signal_updateUnitsEverywhere = pyqtSignal()
    signal_setNeutralViewWhenNoDataset = pyqtSignal()
    signal_disableGuiActionsOnDataset = pyqtSignal(bool)
    signal_enableGuiActionsOnDataset = pyqtSignal()

    signal_updateDatasetsList = pyqtSignal()
    signal_updateDatasetsListWithoutRefresh = pyqtSignal()
    signal_updateDisplayOnDatasetChange = pyqtSignal(bool)


    def __init__(self, qt_panel, mcBusinessLogic, mcData, mainWindow):
        super().__init__()
        print(type(self).__name__ + " initialized")

        self.bl     = mcBusinessLogic
        self.mcData = mcData
        self.panel  = qt_panel
        self.mainWindow = mainWindow

        self.main = main.MCPresentationController_main(qt_panel, mcBusinessLogic, mcData, mainWindow)
        self.representations = representations.MCPresentationController_representations(qt_panel, mcBusinessLogic, mcData, mainWindow)
        self.spectrums = spectrums.MCPresentationController_spectrums(qt_panel, mcBusinessLogic, mcData, mainWindow)
        self.groups = groups.MCPresentationController_groups(qt_panel, mcBusinessLogic, mcData, mainWindow)
        self.projections = projections.MCPresentationController_projections(qt_panel, mcBusinessLogic, mcData, mainWindow)

        self.signals = signals.MCPresentationController_signals()
        # self.view  = mcPresentationView
        # self.model = mcPresentationModel

    def makeConnections(self):
        print("inside makeConnections in MCPresentationController_datasets")
        p = self.panel

        self.signal_setNeutralViewWhenNoDataset.connect(self.setNeutralViewWhenNoDataset)
        self.signal_disableGuiActionsOnDataset.connect(self.disableGuiActionsOnDataset)
        self.signal_enableGuiActionsOnDataset.connect(self.enableGuiActionsOnDataset)
        self.signal_updateDatasetsList.connect(self.updateDatasetsList)
        self.signal_updateDatasetsListWithoutRefresh.connect(partial(self.updateDatasetsList, autoselect_last=False))

        #TODO: ne doit pas etre la
        self.signal_updateDisplayOnDatasetChange.connect(self.updateDisplayOnDatasetChange)

        p.infoXunit.returnPressed.connect(self.changeDatasetUnits)
        p.infoYunit.returnPressed.connect(self.changeDatasetUnits)
        p.infoSpatialUnit.returnPressed.connect(self.changeDatasetUnits)

        self.signal_updateUnitsEverywhere.connect(self.updateUnitsEverywhere)

        p.button_addDataset.clicked.connect(self.createNewDatasetDialog)
        p.button_delDataset.clicked.connect(self.delDatasetDialog)
        p.button_exportDataset.clicked.connect(self.exportDatasetDialog)
        p.comboBox_datasets.currentIndexChanged.connect(partial(self.changeCurrentDataset, name = ''))


        p.PCATypeCombo.currentIndexChanged.connect(self.PCATypeComboChanged)



    def changeDatasetUnits(self):
        """
        methode modifiant les x_unit et y_unit du jdd en cour
        """
        p = self.panel

        ds = self.mcData.datasets.getDataset()

        ds["x_unit"] = str(p.infoXunit.text())
        ds["y_unit"] = str(p.infoYunit.text())
        ds["spatial_unit"] = str(p.infoSpatialUnit.text())

        self.signal_updateUnitsEverywhere.emit()

    def updateUnitsEverywhere(self):
        """
        Method called on axis title change
        """

        print("inside updateUnitsEverywhere")

        ds = self.mcData.datasets.getDataset()

        # ======================================================================
        #           Representation
        # ======================================================================
        imagePlot = self.representations.getRepresentationImagePlot()

        bottom_axis_id = imagePlot.get_axis_id("bottom")

        left_axis_id = imagePlot.get_axis_id("left")

        imagePlot.set_axis_unit(bottom_axis_id, ds["spatial_unit"])
        imagePlot.set_axis_unit(left_axis_id, ds["spatial_unit"])

        imagePlot.replot()

        # ======================================================================
        #           MultiDatasetViewer
        # ======================================================================
        # TODO

        # ======================================================================
        #           Plots
        # ======================================================================
        self.signals.signal_spectrumsToDisplayChanged.emit([])

        # ======================================================================
        #           Dataset Infos tab
        # ======================================================================
        self.main.signal_updateInfosTab.emit()

    def exportDatasetDialog(self):
        ds_name = self.mcData.datasets.currentDatasetName
        print("inside exportDatasetDialog")

        if "mc_export_" not in ds_name: #pour eviter un filename du type "mc_export_mc_export_xxxxxx"
            proposed_filename = "mc_export_" + ds_name
        else:
            proposed_filename = ds_name

        filename = QtWidgets.QFileDialog.getSaveFileName(parent = self.mainWindow,
                                                         caption = "Save dataset",
                                                         directory = proposed_filename,
                                                         filter = "*.h5")[0]

        if not filename:
            return False

        else:
            try:
                self.bl.io.saveDataset(ds_name, filename)
                return True

            except OSError as e:
                mc_logging.error("Can't save dataset")
                mc_logging.error(e)
                return False

    # =========================================================================
    #  Methodes propres a createNewDatasetDialog
    # =========================================================================
    def createNewDatasetDialog(self):

        print("inside openNewDatasetDialog")

        # datasets.py = self.mcData.datasets.py.getDatasets()

        p = self.panel  # panel principal

        d = uic.loadUi("assets//ui_files//newDatasetDialog.ui")

        d.setWindowTitle("New dataset creation")

        # ======= On remplit le comboBox avec les datasets.py disponibles ==========
        items = [p.comboBox_datasets.itemText(i) for i in range(p.comboBox_datasets.count())]



        #==================================================================================
        #Methode appelé lors du changement du dataset de base dans la combobox
        #on le met avant le addItems pour que le callback soit appelé a l'initialisation
        #==================================================================================
        callback = partial(self.createNewDatasetDialog_baseDatasetChanged, panel = d, parent_panel = p)
        d.combo_baseDataset.currentIndexChanged.connect(callback)

        #==================================================================================
        #Mise à jour des informations sur le binning demandé
        #==================================================================================
        for widget in (d.comboBox_spectralxbin, d.comboBox_spatialxbin, d.comboBox_spatialybin):

            callback = partial(self.createNewDatasetDialog_updateInfos, panel = d, parent_panel = p)
            widget.currentIndexChanged.connect(callback)


        d.combo_baseDataset.addItems(items)
        #on preselectionne par default le dataset en cour
        index_of_current_dataset = d.combo_baseDataset.findText(self.mcData.datasets.currentDatasetName)
        d.combo_baseDataset.setCurrentIndex(index_of_current_dataset)

        # =============Nom par defaut du dataset=================================
        #d.lineEdit_datasetName.setText("dataset%d" % (p.comboBox_datasets.count() + 1))
        d.lineEdit_datasetName.setText("%s_%d" % (d.combo_baseDataset.currentText(), self.mcData.datasets.count() + 1))


        # ============ Couleur par default =====================================
        default_color = self.bl.getNextColor()

        self.main.setWidgetBackgroundColor(d.pushButton_color, default_color)

        d.pushButton_color.clicked.connect(partial(self.main.getColorFromColorPickerDialog, d.pushButton_color))

        ok = d.exec_()


        if ok:
            #=================================================================
            # Collecte des infos de la GUI
            #=================================================================
            ds_name      = str(d.lineEdit_datasetName.text())
            ds_base_name = str(d.combo_baseDataset.currentText())
            color        = getattr(self, "_color_picker_value", default_color)

            #=================================================================
            # Truncate datas
            #=================================================================
            x_min = d.spinbox_xmin.value()
            x_max = d.spinbox_xmax.value()

            i_min = d.spinbox_imin.value()
            i_max = d.spinbox_imax.value()

            #=================================================================
            # Spatial and spectral binning
            #=================================================================
            spatial_xbin  = int(d.comboBox_spatialxbin.currentText())
            spatial_ybin  = int(d.comboBox_spatialybin.currentText())
            spectral_xbin = int(d.comboBox_spectralxbin.currentText())

            excluded_groups = [str(d.list_excludedGroups.item(i.row()).text()) for i in
                               d.list_excludedGroups.selectedIndexes()]

            included_groups = [str(d.list_includedGroups.item(i.row()).text()) for i in
                               d.list_includedGroups.selectedIndexes()]

            #=================================================================
            # Channels filtering
            #=================================================================
            included_channels = [i.row() for i in d.list_includedChannels.selectedIndexes()]
            excluded_channels = [i.row() for i in d.list_excludedChannels.selectedIndexes()]


            #=================================================================
            # Print some infos
            #=================================================================
            print("====== Creating dataset ======")
            print("name:\t\t", ds_name)
            print("based on:\t\t", ds_base_name)
            print("xrange:\t\t", x_min, "to", x_max)
            print("irange:\t\t", i_min, "to", i_max)
            print("xbin,ybin:\t\t", spatial_xbin, spatial_ybin)
            print("spectral bin:\t", spectral_xbin)

            if included_groups:
                print("including only:\t", included_groups)

            if excluded_groups:
                print("excluding:\t\t", excluded_groups)

            if included_channels:
                print("including only channels:\t", included_channels)

            if excluded_channels:
                print("excluding channels:\t\t", excluded_channels)

            # =================================================================
            # Mise en garde sur le binning si les points sont non jointifs
            # =================================================================
            mess = "You choose spatial binning with non-contiguous data points.\n"
            mess += "Be aware that new dataset will be created with contiguous data points. "
            mess += "Continue anyway?\n"

            if (spatial_xbin > 1 or spatial_ybin > 1) and not self.bl.coordinates.hasContiguousPoints(ds_base_name):

                reply = QtWidgets.QMessageBox.question(self.mainWindow,
                                                       'Confirmation',
                                                       mess,
                                                       QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                                       QtWidgets.QMessageBox.No)

                if reply == QtWidgets.QMessageBox.No:
                    return

            # =================================================================
            # On lance la creation du dataset dans un thread a part
            # =================================================================
            args = {"ds_name": ds_name,
                    "ds_base_name": ds_base_name,
                    "color": color,
                    "x_min": x_min,
                    "x_max": x_max,
                    "i_min": i_min,
                    "i_max": i_max,
                    "spatial_xbin": spatial_xbin,
                    "spatial_ybin": spatial_ybin,
                    "spectral_xbin": spectral_xbin,
                    "included_groups": included_groups,
                    "excluded_groups": excluded_groups,
                    "included_channels": included_channels,
                    "excluded_channels": excluded_channels,
                    "callback_progress" : self.main.displayProgressBar,
                    "callback_done":self.createNewDatasetThread_doneCallback,
                    "normalize_method": self.spectrums.normalizeMethod
                    }

            self.disableGuiActionsOnDataset(False)

            myThread = Thread(target = self.bl.io.createNewDatasetFromUserParameters, args = (args,))
            myThread.daemon = True
            myThread.start()

        else:
            print("new dataset creation canceled")
            return


    def createNewDatasetThread_doneCallback(self, ds_name):
        """
        Quand un nouveau jeux de données ds_name est cree, mise à jour de la liste,
        des relations entre jdds et autoselection de ce jdd
        """

        self.signal_updateDatasetsList.emit()

        # ======================================================================
        #   Mise a jour des relationships disponibles
        # ======================================================================
        self.main.signal_updateLinkedDatasetsList_inMultiDatasetExplorer.emit()
        self.signal_updateDatasetsListWithoutRefresh.emit()

        # =================================================================
        # On demande le chargement et affichage du nouveau dataset
        # =================================================================
        self.changeCurrentDataset(name = ds_name)

        self.enableGuiActionsOnDataset()


    def createNewDatasetDialog_updateInfos(self, panel, parent_panel):

        mc_logging.debug("inside createNewDatasetDialog_updateInfos")

        d = panel

        # p = parent_panel

        ds_base_name = str(d.combo_baseDataset.currentText())

        ds_base = self.mcData.datasets.getDataset(ds_base_name)

        #W  = ds_base["W"]
        dx = ds_base["dx"]
        dy = ds_base["dy"]

        # w = ds_base["image_width"]
        # h = ds_base["image_height"]

        spectral_unit = ds_base["x_unit"]
        spatial_unit  = ds_base["spatial_unit"]


        W = self.mcData.datasets.getNumericVersionOfW(ds_base_name)

        if len(W) > 1:
            dW = abs(W[1] - W[0])
        else:
            dW = 0

        try:
            spatial_xbin  = int(d.comboBox_spatialxbin.currentText())
            spatial_ybin  = int(d.comboBox_spatialybin.currentText())
            spectral_xbin = int(d.comboBox_spectralxbin.currentText())

        except ValueError as e:
            print(e)
            return

        spatialBinningInfo = "( original dx, dy =  %.2f, %.2f %s    new dx, dy =  %.2f, %.2f %s)" % (

            dx, dy, spatial_unit, dx * spatial_xbin, dy * spatial_ybin, spatial_unit)

        spectralBinningInfo = "( original bin: %.2f %s    new bin: %.2f %s )" % (
        dW, spectral_unit, spectral_xbin * dW, spectral_unit)

        d.label_spatialBinningInfo.setText(spatialBinningInfo)
        d.label_spectralBinningInfo.setText(spectralBinningInfo)


    def createNewDatasetDialog_baseDatasetChanged(self, panel, parent_panel):

        mc_logging.debug("inside createNewDatasetDialog_baseDatasetChanged")

        d = panel

        p = parent_panel

        ds_name_base = str(d.combo_baseDataset.currentText())

        ds_base = self.mcData.datasets.getDataset(ds_name_base)


        w = ds_base["image_width"]
        h = ds_base["image_height"]

        dsSize = ds_base["size"]

        W = ds_base["W"]
        Wnum = self.mcData.datasets.getNumericVersionOfW(ds_name_base)

        # =====================================================================
        #                  On definit la gamme possible pour x
        # =====================================================================
        print("Wnum:",Wnum[-1])
        d.spinbox_xmin.setRange(min(Wnum), max(Wnum))
        d.spinbox_xmax.setRange(min(Wnum), max(Wnum))
        d.spinbox_xmin.setValue(min(Wnum))
        d.spinbox_xmax.setValue(max(Wnum))

        #======================================================================
        #            Mise à jour du nom par default
        #======================================================================
        d.lineEdit_datasetName.setText("%s_%d" % (d.combo_baseDataset.currentText(), p.comboBox_datasets.count() + 1))

        # =====================================================================
        #                  On definit la gamme possible pour i
        # =====================================================================
        d.spinbox_imin.setRange(0, dsSize)
        d.spinbox_imax.setRange(0, dsSize)
        d.spinbox_imax.setValue(dsSize)

        # =====================================================================
        # On definit la gamme possible pour x_bin/y_bin
        # =====================================================================
        allowed_x_dividers = [str(x) for x in range(w) if x != 0 and w % x == 0]
        allowed_y_dividers = [str(y) for y in range(h) if y != 0 and h % y == 0]

        d.comboBox_spatialxbin.clear()
        d.comboBox_spatialybin.clear()

        d.comboBox_spatialxbin.addItems(allowed_x_dividers)
        d.comboBox_spatialybin.addItems(allowed_y_dividers)

        # =====================================================================
        # On definit les cannaux possibles pour une selection par canaux
        # =====================================================================
        channel_list = list(map(str, W))

        d.list_includedChannels.clear()
        d.list_excludedChannels.clear()

        d.list_includedChannels.addItems(channel_list)
        d.list_excludedChannels.addItems(channel_list)

        # =====================================================================
        # On definit la gamme possible pour spectralxbin
        # =====================================================================
        allowed_x_dividers = [str(x) for x in range(1,len(W)) if x==1 or len(W) % x == 0]
        d.comboBox_spectralxbin.clear()
        d.comboBox_spectralxbin.addItems(allowed_x_dividers)


        # =======================================================================
        # On affiche la liste des groupes associes au baseDataset
        # dans les list "exclude" et "include"
        # =======================================================================
        # on itere sur la combobox au lieu de self.selections.iteritems() pour avoir
        # les groupes dans l'ordre de creation
        # combo = p.combo_currentSelectionGroup

        icon = QtGui.QPixmap(40, 40)

        d.list_includedGroups.clear()
        d.list_excludedGroups.clear()

        for group_name, group in ds_base["groups"].items():

            color = self.bl.groups.getGroupColor(ds_name_base, group_name)

            print("color for", group_name, end=' ')
            print(color)

            icon.fill(color)

            item1 = QtWidgets.QListWidgetItem(QtGui.QIcon(icon), group_name)
            item2 = QtWidgets.QListWidgetItem(QtGui.QIcon(icon), group_name)

            d.list_includedGroups.addItem(item1)
            d.list_excludedGroups.addItem(item2)

        self.createNewDatasetDialog_updateInfos(panel, parent_panel)




    #==========================================================================
    #
    #===========================================================================
    # @my_pyqtSlot()
    def setNeutralViewWhenNoDataset(self):
        """
        TODO: Quand aucun dataset dans le projet, mise à zero des differents graphs
        et onglets
        """
        mc_logging.debug("setting neutral view")


    # @my_pyqtSlot()
    def disableGuiActionsOnDataset(self, fileTabEnabled = True):
        """
        desactivation des actions sur le jdd tant qu'aucun n'est chargé
        """

        p = self.panel

        #================================================================
        # Disable Tabs
        #================================================================
        tabs = p.tabWidget_toolbar

        currentIndex = tabs.currentIndex()

        for tab_id in range(tabs.count()):

            tab_name = tabs.tabText(tab_id)

            if tab_name == "File" and fileTabEnabled:
                tabs.setTabEnabled(tab_id, True)
            else:
                tabs.setTabEnabled(tab_id, False)

        if not fileTabEnabled:
            tabs.setCurrentIndex(currentIndex)
        #================================================================
        # Disable Dataset selector
        #================================================================
        p.comboBox_datasets.setEnabled(False)

    ##@my_pyqtSlot()
    def enableGuiActionsOnDataset(self):
        """
        complementaire à disableActionsBeforeFileLoaded
        """
        p = self.panel

        #================================================================
        # Enable Tabs
        #================================================================
        tabs = p.tabWidget_toolbar

        for tab_id in range(tabs.count()):
            tab_name = tabs.tabText(tab_id)
            tabs.setTabEnabled(tab_id, True)
        #================================================================
        # Enable Dataset selector
        #================================================================
        p.comboBox_datasets.setEnabled(True)


    def removeDataset(self, ds_name):

        self.bl.io.removeDataset(ds_name)
        self.updateDisplayAfterDatasetDeleted()


    def updateDisplayAfterDatasetDeleted(self):

        """
        All actions to do after deleting a dataset
        """

        mc_logging.debug("updateDisplayAfterDatasetDeleted")

        # mise a  jour de la combobox de choix du dataset

        self.signal_updateDatasetsList.emit()

        self.main.signal_updateLinkedDatasetsList_inMultiDatasetExplorer.emit()
        self.main.signal_updateRepresentationsDisplay_inMultiDatasetExplorer.emit(True)

        if len(self.mcData.datasets.names()) == 0:
            self.signal_disableGuiActionsOnDataset.emit(True)
            self.signal_setNeutralViewWhenNoDataset.emit()


    def delDatasetDialog(self):

        p = self.panel  # panel principal

        dataset_name = p.comboBox_datasets.currentText()

        # datasets.py = self.getDatasets()

        # ============== Confirmation de suppression ============================
        reply = QtWidgets.QMessageBox.question(self.mainWindow,
                                               'Confirmation',
                                               'Are you sure you want to delete "%s" dataset?' % (dataset_name,),
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                               QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.Yes:

            self.removeDataset(dataset_name)
        else:
            return


    def changeCurrentDataset(self, name = ''):

        p = self.panel

        self.main.saveGuiState()

        # ======================================================================

        cd = p.comboBox_datasets

        if not name:

            ds_name = str(cd.currentText())

            if not ds_name: return

            self.mcData.datasets.currentDatasetName = ds_name


        else:
            ds_name = name

            try:
                self.mcData.datasets.currentDatasetName = ds_name
                cd.setCurrentIndex(cd.findText(ds_name))

            except NameError as e:
                print("Name error:",e)




        # ======================================================================

        print('Current dataset is now "%s"' % (ds_name))

        ds_infos = self.mcData.datasets.datasetInfos(ds_name)
        print(ds_infos)

        # sinon, bug quand on change de dataset et qu'un spectre est affiché
        self.mcData.currentSpectrumIndex = 0
        self.bl.groups.setCurrentGroup(None)

        # ========= Mise a jour de l'affichage des PCs, Mean_data etc... =======
        self.signal_updateDisplayOnDatasetChange.emit(True)

    def getDatasetColor(self, ds_name, as_tuple = False):

        ds = self.mcData.datasets.getDataset(ds_name)

        color = ds.get("display", {}).get("color", None)

        if color is None or type(color) is str:
            color = self.bl.getNextColor()  # .getDatasetColor()
            ds.setdefault("display", {})["color"] = color#.getRgb()

        #print("type",type(color))
        #print("color:",color)

        if as_tuple:
            return color.getRgb()
        else:
            if isinstance(color, tuple) or isinstance(color, np.ndarray):
                return QtGui.QColor(color[0],color[1],color[2])
            else:
                return color



    def getDataset_X_normalized(self, norm_type = ''):

        ds = self.mcData.datasets.getDataset()

        # Si on demande un type de normalisation particulier, en enregistre pas dans le ds
        if norm_type:
            datas_normalized = normalizeHDF5(ds["X"], self.bl.io.workFile, norm_type)
            return datas_normalized

        else:
            norm_type = self.spectrums.normalizeMethod

            #on ne recalcul pas si X_normalized existe deja
            if ds.get("X_normalized", None) is not None:
                return ds["X_normalized"]

            else:
                datas_normalized = normalizeHDF5(ds["X"], self.bl.io.workFile, norm_type)
                ds["X_normalized"] = datas_normalized
                return ds["X_normalized"]


    def getDataset_MeanDatas_normalized(self):

        ds = self.mcData.datasets.getDataset()

        if ds.get("mean_datas_normalized", None) is not None:
        #if "mean_datas_normalized" in ds:
            #print "MeanDatas_normalized already calculated"
            return ds["mean_datas_normalized"]

        else:
            datas_normalized = self.getDataset_X_normalized()
            print("datas_normalized",datas_normalized)
            ds["mean_datas_normalized"] = getMean(datas_normalized, axis = 0)
            return ds["mean_datas_normalized"]


    def updateDatasetsList(self, autoselect_last = True):

        print("DEBUG: inside updateDatasetsList")
        p = self.panel
        s = p.comboBox_datasets

        ds_names = self.mcData.datasets.names()
        #previously_selected_value = s.currentText()

        s.clear()
        s.blockSignals(True)

        last_index = len(ds_names) - 1

        for i, ds_name in enumerate(ds_names):

            if i == last_index and autoselect_last: s.blockSignals(False)

            # ======================================================================
            # On ajoute une couleur par dataset + un indicateur pour identifier
            # les ds reliés
            # ======================================================================
            icon = QtGui.QPixmap(60, 40)

            color = self.getDatasetColor(ds_name)
            #print("color:",color)
            icon.fill(color)

            # ligne transverse
            # painter = QtGui.QPainter(icon)
            # brush = QtGui.QBrush(QtGui.QColor(255,0,150))
            # painter.setBrush(brush)
            # painter.drawLine(0,0,40,40)
            # painter.end()

            # print("self.bl.relationships.getAvailableRelationships():")
            # print(self.bl.relationships.getAvailableRelationships())

            if ds_name in self.bl.relationships.getAvailableRelationships():

                painter = QPainter(icon)
                marker_color = QColor(0, 0, 0)
                brush = QBrush(marker_color)
                painter.setBrush(brush)
                painter.setPen(marker_color)
                font = QFont("Times", 20, QFont.Bold)
                painter.setFont(font)
                painter.drawText(0, 0, 60, 40, QtCore.Qt.AlignCenter, "L")
                painter.end()

            # ======================================================================

            s.addItem(QtGui.QIcon(icon), ds_name)

        # ======================================================================
        # on remet le ds qui etait selectionné à la base
        # =====================================================================
        if not autoselect_last:

            index = s.findText(self.mcData.datasets.currentDatasetName)

            if index != -1:  s.setCurrentIndex(index)
            else:            print("cant find previously selected dataset")

        s.blockSignals(False)


    def addDatasetToDict(self, name, W, datas, xys, base_dataset = None, args = dict(), indices_in_base_dataset = None,
                         xys_base_dataset = None, color = None):

        self.bl.io.addDatasetToDict(name = name,
                                    W = W,
                                    datas = datas,
                                    xys = xys,
                                    base_dataset = base_dataset,
                                    args = args,
                                    indices_in_base_dataset = indices_in_base_dataset,
                                    xys_base_dataset = xys_base_dataset,
                                    color = color,
                                    normalize_method = self.spectrums.normalizeMethod,
                                    callback_progress = self.main.displayProgressBar)

        self.signal_updateDatasetsList.emit()


    def updateDisplayOnDatasetChange(self, restore_gui_state = True):

        mc_logging.debug("inside updateDisplayOnDatasetChange")

        print("updating display (mean_data, pcaComponents, group_display, displayed_spectrum)")

        ds = self.mcData.datasets.getDataset()

        if ds:

            # ==================== Affichage du spectre moyen ======================
            if self.spectrums.useNormalizedData:
                mean_data = self.getDataset_MeanDatas_normalized()
            else:
                mean_data = ds["mean_datas"]

            plots.displayAPlotInCurveWidget(curveWidget_name ='meanData',
                                            title = 'Mean data',
                                            x = ds["W"],
                                            y = mean_data,
                                            panel = self.panel)

            # ======= on essai d'afficher la PCA si elle a deja été lancé ==========
            self.main.signal_displayCoeffsHistogram.emit("pca")
            # ======================================================================


            # ======================================================================
            #          Affiche uniquement les groupes
            #          et representations relatifs a ce dataset
            #          dans les comboBoxs
            # ======================================================================
            #print("before _displayAPlotInCurveWidget")
            self.groups.signal_updateGroupsList.emit()

            self.groups.signal_updateGroupsDisplayHolders.emit()

            self.signals.signal_groupsUpdated.emit()

            self.representations.signal_updateRepresentationsFamilyList.emit()

            self.projections.signal_updateProjectionList.emit()

            self.projections.signal_updateCurrentProjection.emit()

            #TODO: il faudrait abonner updateSpectrumsRefList à DatasetChanged pour decoupler
            #self.main.signal_updateSpectrumsRefsList.emit()

            self.signals.signal_spectrumsToDisplayChanged.emit([])

            self.main.signal_updateInfosTab.emit()

            self.PCASetRandomSampleBounds()
            #print("after _displayAPlotInCurveWidget")

            #==============================================================================
            #mise à jour des correlations
            #==============================================================================
            self.representations.switchExplorerTypeInRepresentationTab("data")

            self.representations.signal_updateLabelsOnCorrelationPlot.emit()


            if restore_gui_state:
                self.main.restoreGuiState()


    #===========================================================================================
    # TODO: a mettre ailleur!
    #===========================================================================================
    def PCASetRandomSampleBounds(self):
        """
        Met a jour l'affichage du choix de taille d'echantillon possible pour la PCA
        min = len(W)
        max = len(dataset)
        """
        p  = self.panel
        ds = self.mcData.datasets.getDataset()

        if ds:
            p.PCASampleSize.setMinimum(1)
            p.PCASampleSize.setMaximum(ds["size"])


    def PCATypeComboChanged(self):
        """
        mise a jour de l'affichage au changement de type de pca
        """
        print("PCATypeComboChanged")

        p = self.panel

        pcaType = p.PCATypeCombo.currentText()

        print("pcaType", pcaType)

        if pcaType == "x size random set":
            p.PCASampleSize_label.setEnabled(True)
            p.PCASampleSize.setEnabled(True)

        else:
            p.PCASampleSize_label.setEnabled(False)
            p.PCASampleSize.setEnabled(False)

    #=============================================================================================