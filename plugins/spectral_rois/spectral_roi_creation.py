import threading

import numpy as np
from PyQt5 import QtGui, QtCore
from PyQt5 import uic
from PyQt5.QtWidgets import QPushButton,QFileDialog
from plotpy.builder import make
from plotpy.plot import PlotDialog, PlotOptions

from helpers import mc_logging
from helpers.plots import plots


class SpectralRoiCreation(object):

    def __init__(self, bl, mcData, gui):
        super().__init__()

        self.tab = "Filtering"
        self.family = "representation_creation"
        self.name   = "Spectral Roi Creation"
        self.tooltip_text = "tooltip text..."

        self.menu_item = QPushButton("ROI",
                                      clicked = self.launchMainGui)

        self.bl = bl
        self.mcData = mcData
        self.gui = gui

        self.mainWindow = self.gui.main.mainWindow



    def launchMainGui(self):
        """
        Cette methode creer une image correspondant à une ROI
        """

        print("inside spectralROICreation_launchMainGUI")

        # p = self.gui.panel

        ds = self.mcData.datasets.getDataset()

        spectrumIndex = self.mcData.currentSpectrumIndex

        #=========================================================================
        # import GUI
        # =========================================================================
        d = uic.loadUi("assets//ui_files//spectral_ROI_selection.ui")

        d.setWindowTitle("Spectral ROI selection")

        self.spectralROICreation_panel = d

        # ==================On place un curve dialog============================

        curveDialog = PlotDialog(edit = False, toolbar = False,options = PlotOptions(type="curve"))

        curveDialog.setObjectName("curvewidget")  # pour le retrouver plus tard

        d.plotDialogContainerLayout.addWidget(curveDialog)

        self.gui.main.save_widget_ref(curveDialog)

        # TODO: afficher un appercu live du ROI


        # =======================================================================
        # On affiche une courbe, par default le spectre selected_spectrum
        # =======================================================================

        if self.gui.spectrums.useNormalizedData:
            X = self.gui.datasets.getDataset_X_normalized()

        else:
            X = ds["X"]

        plots.displayAPlotInCurveWidget(panel = d,
                                        curveWidget_name = "curvewidget",
                                        title = "Spectrum",
                                        x = ds["W"],
                                        y = X[spectrumIndex],
                                       )

        d.button_loadRoiCsv.clicked.connect(self.importROIList)

        d.button_addRoi.clicked.connect(self.addROI)

        d.button_removeRoi.clicked.connect(self.removeSelectedROIs)

        d.listWidget_roiList.itemClicked.connect(self.updateDisplayedRois)

        # conteneur pour les ROIs

        self.spectralROICreation_ROIDict = dict()

        # ==========un nom de roi par default====================

        # TODO, compter les roi deja existantes et incrementer

        d.text_roiName.setText("auto")

        # on lance l'interface

        d.setModal(True)

        ok = d.exec_()

        # ============= On recupere les donnees de la gui =======================

        if ok:
            roi_mode = str(d.comboRoiMode.currentText())

            roi_dict = self.spectralROICreation_ROIDict

            selected_roi_names = [str(item.text()) for item in d.listWidget_roiList.selectedItems()]

            rois_ranges = [roi_dict[roi_name]["range_item"].get_range() for roi_name in selected_roi_names]

            print("rois_ranges", rois_ranges)

            # ==================================================================
            # On lance le thread de caclul
            # ==================================================================

            t = threading.Thread(target = self.createROIImages_Thread,
                                 args = (ds, roi_mode, rois_ranges, selected_roi_names))

            t.deamon = True

            t.start()



    def getCurvePlot(self):

        panel = self.spectralROICreation_panel

        curveDialogWidget = panel.findChild(PlotDialog, name = "curvewidget")

        curvePlot = curveDialogWidget.get_plot()

        return curvePlot


    def getRangeItem(self, x_min, x_max):
        """
        :param panel: gui ref
        :param x_min: range min
        :param x_max: range max
        :return: range object reference

        """

        range = make.range(x_min, x_max)

        # range_label = make.range_info_label(range,
        #                                    anchor = "TL",
        #                                    label = "%.1f - %.1f" + ds["x_unit"],
        #                                    function = lambda x, dx: (x - dx, x + dx),
        #                                    title = "Range infos:")

        random_color = self.bl.getNextColor()

        random_color.setAlpha(38)

        range.brush = QtGui.QBrush(random_color)

        return range




    def createROIImages_Thread(self, ds, roi_mode, rois_ranges, roi_names):
        """
        Creation de representations ROI
        ds: dataset slicy
        roi_mode: type de baseline
        rois_ranges: liste de tuple (x_min, x_max) definissant la ROI
        roi_name: liste de str

        TODO, faire toutes les rois en meme temps pour accelerer?
        """

        W = ds["W"][:]

        for i, roi_name in enumerate(roi_names):

            x_min, x_max = min(rois_ranges[i]),max(rois_ranges[i])

            if "auto" in roi_name:  # texte par default

                roi_name = "%.1f to %.1f %s" % (x_min, x_max, ds["x_unit"])

            print("auto roi name:", roi_name)

            idxs_xmin = W >= x_min
            idxs_xmax = W <= x_max

            spectral_interval_idxs = np.where(idxs_xmin & idxs_xmax)[0].tolist()

            # print "spectral_interval_idxs:",spectral_interval_idxs

            if len(spectral_interval_idxs) < 2:

                print("error: Invalid interval")
                return

            else:

                print("Channels for ROI:", len(spectral_interval_idxs))

            idx_xmin = spectral_interval_idxs[0]
            idx_xmax = spectral_interval_idxs[-1]

            xmin = ds["W"][idx_xmin]
            xmax = ds["W"][idx_xmax]

            # print "type(spectral_interval_idxs)",type(spectral_interval_idxs)
            # print "spectral_interval_idxs:",spectral_interval_idxs

            if type(ds["W"] is list):
                W_roi = ds["W"][idx_xmin: idx_xmax + 1]
            else:
                W_roi = ds["W"][spectral_interval_idxs]

            # on creer un conteneur vide pour les valeurs de roi calculées

            values = np.zeros((ds["size"],))

            if roi_mode == "Signal to baseline":
                # calcul du coefficient directeur et coo a l'origine d'une droite y = ax+b
                # reliant le point min et le point max pour faire une baseline

                # TODO: choisir le type de baseline, pour l'instant ->lineaire
                # TODO: a accelerer !!

                for spectrum_index in range(ds["size"]):

                    ymin = ds["X"][spectrum_index][idx_xmin]
                    ymax = ds["X"][spectrum_index][idx_xmax]

                    a = (ymax - ymin) / (xmax - xmin)

                    b = 0.5 * (ymin + ymax - a * (xmin + xmax))

                    baseline = lambda x: a * x + b

                    raw_values = ds["X"][spectrum_index][spectral_interval_idxs]

                    baseline_values = baseline(W_roi)

                    roi_values = raw_values - baseline_values

                    values[spectrum_index] = np.sum(roi_values)

                    self.gui.main.displayProgressBar(100.0 * spectrum_index / ds["size"])

            elif roi_mode == "Sum":
                print("Processing ROI sum...", end='')

                values_in_ROI = ds["X"][:,spectral_interval_idxs]
                values = np.sum(values_in_ROI, axis=1)
                print("done!")


            self.gui.main.resetProgressBar()

            image = self.bl.representations.getImageFromValues(values)

            self.gui.representations.insertRepresentationInDatasetDict("Spectral ROIs",
                                                                       roi_name,
                                                                       image,
                                                                       display = True,
                                                                       gotoTab = True
                                                                       )


    def addROI(self, x_min=None, x_max=None, roi_name=None):
        panel = self.spectralROICreation_panel

        roi_dict = self.spectralROICreation_ROIDict

        rl = panel.listWidget_roiList

        # =======================================================================
        # ajout d'une ROI par defaut
        # =======================================================================

        if roi_name is None:

            ds = self.mcData.datasets.getDataset()

            mid_point = int(len(ds["W"]) / 2)

            x_min = ds["W"][int(mid_point - mid_point / 2)]
            x_max = ds["W"][int(mid_point + mid_point / 2)]

            # ====================================================================
            # on creer un nom par defaut si non definit dans l'interface
            # ====================================================================

            gui_roi_name = str(panel.text_roiName.text())

            if gui_roi_name == "auto":

                counter = getattr(self, "spectralROICreation_counter", 0)

                roi_name = "auto_named_%d" % (counter)

                self.spectralROICreation_counter = counter + 1

            else:

                roi_name = gui_roi_name

        # =======================================================================
        # Creation d'une entree dans le dict des ROIs
        # =======================================================================

        roi = dict()

        roi["min"] = x_min
        roi["max"] = x_max

        roi["range_item"] = self.getRangeItem(x_min, x_max)
        roi_dict[roi_name] = roi

        # =========================================================
        # Ajout de la ROI a la liste
        # =========================================================

        # le + roi_name pour mettre selected par default

        old_selected = [item.text() for item in rl.selectedItems()] + [roi_name]

        new_list = [item.text() for item in rl.findItems("", QtCore.Qt.MatchContains)] + [roi_name]

        rl.clear()

        rl.addItems(new_list)

        for i in range(rl.count()):
            if rl.item(i).text() in old_selected:
                rl.item(i).setSelected(True)

        # =========================================================
        # Ajout de la ROI au plot
        # =========================================================

        curvePlot = self.getCurvePlot()

        curvePlot.add_item(roi["range_item"])

        # curvePlot.add_item(range_label)

        curvePlot.replot()


    def updateDisplayedRois(self):
        print("inside spectralROICreation_updateDisplayedRois")

        panel = self.spectralROICreation_panel

        roi_dict = self.spectralROICreation_ROIDict

        rl = panel.listWidget_roiList

        curvePlot = self.getCurvePlot()

        # =========================================================
        # is_selected set to True if selected in list
        # =========================================================

        selected_roi_names = [str(item.text()) for item in rl.selectedItems()]

        print("selected_roi_names:", selected_roi_names)

        for roi_name, roi in roi_dict.items():

            if roi_name in selected_roi_names:
                roi["range_item"].show()
            else:
                roi["range_item"].hide()

        curvePlot.replot()


    def removeSelectedROIs(self):
        panel = self.spectralROICreation_panel

        roi_dict = self.spectralROICreation_ROIDict
        curvePlot = self.getCurvePlot()

        rl = panel.listWidget_roiList

        selected_roi_names = [str(item.text()) for item in rl.selectedItems()]

        for roi_name in selected_roi_names:
            # del roi_dict[roi_name]

            item_inList = rl.findItems(roi_name, QtCore.Qt.MatchContains)[0]

            rl.takeItem(rl.row(item_inList))

        self.updateDisplayedRois()


    def importROIList(self):
        panel = self.spectralROICreation_panel

        filename = QFileDialog.getOpenFileName(panel, "Open ROI List File...")[0]

        print("opening ROI List file:\n", filename)

        # ============================================================================
        #           Lecture du txt
        # ============================================================================

        roi_dict = dict()

        if not filename:
            mc_logging.debug("no ROI file specified")
            return

        try:
            f = open(filename, 'r')
        except FileNotFoundError:
            mc_logging.warning("ROI file '%s' not found" % (filename))
            return

        for line in f:
            splitted = line.split()
            roi_name = splitted[0]

            roi_min = float(splitted[1])
            roi_max = float(splitted[2])

            self.addROI(roi_min, roi_max, roi_name)

            # self.spectralROICreation_updateROIList(panel, roi_dict)

