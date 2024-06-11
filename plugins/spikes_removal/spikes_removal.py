import numpy as np
from PyQt5 import QtGui
from PyQt5 import uic
from PyQt5.QtWidgets import QPushButton
from plotpy.builder import make
from plotpy.plot import PlotDialog,PlotOptions


class SpikesRemoval(object):

    def __init__(self, bl, mcData, gui):
        super().__init__()

        self.tab = "Filtering"
        self.family = ""
        self.name   = "Spikes Removal"
        self.tooltip_text = "tooltip text..."

        self.menu_item = QPushButton("Spikes",
                                     clicked = self.launchMainGui)

        self.bl = bl
        self.mcData = mcData
        self.gui = gui


        self.mainWindow = self.gui.main.mainWindow



    def launchMainGui(self):
        """
        """

        print("inside spikes_removal launchMainGui")

        self.guiDatas = dict()
        # indice du spectre en key, spectre en value
        self.new_spectrums = {}


        # p = self.gui.panel
        spectrumIndex = self.mcData.currentSpectrumIndex

        #=========================================================================
        # import GUI
        # =========================================================================
        d = uic.loadUi("assets//ui_files//spikes_removal.ui")

        d.setWindowTitle("Spikes Removal")

        self.spectralROICreation_panel = d

        #=========================================================================
        # On place les curves dialogs
        # =========================================================================

        curveDialog_before = PlotDialog(edit = False, toolbar = False, options=PlotOptions(type="curve"))
        curveDialog_before.setObjectName("curvewidget_before")
        d.plotDialogContainerLayout.addWidget(curveDialog_before)

        curveDialog_before.get_plot().SIG_RANGE_CHANGED.connect(self.applySpikeRemovalToSpectrum)


        self.gui.main.save_widget_ref(curveDialog_before)


        curveDialog_after = PlotDialog(edit = False, toolbar = False, options=PlotOptions(type="curve"))
        curveDialog_after.setObjectName("curvewidget_after")
        d.plotDialogContainerLayout.addWidget(curveDialog_after)

        self.gui.main.save_widget_ref(curveDialog_after)

        #TODO: exit if ds["W"] non numeric

        # =======================================================================
        # On affiche une courbe, par default le spectre selected_spectrum
        # =======================================================================
        ds = self.mcData.datasets.getDataset()

        if self.gui.spectrums.useNormalizedData:
            X = self.gui.datasets.getDataset_X_normalized()

        else:
            X = ds["X"]

        self.X = X
        self.W = W = ds["W"]

        curveBefore = make.curve(W, X[spectrumIndex], color = "b")
        curveAfter  = make.curve(W, X[spectrumIndex], color = "g")

        curveDialog_before.get_plot().add_item(curveBefore)
        curveDialog_after.get_plot().add_item(curveAfter)

        self.guiDatas["curveDialogBefore"] = curveDialog_before
        self.guiDatas["curveBefore"] = curveBefore
        self.guiDatas["plotBefore"]  = curveDialog_before.get_plot()

        self.guiDatas["curveDialogAfter"] = curveDialog_after
        self.guiDatas["curveAfter"] = curveAfter
        self.guiDatas["plotAfter"]  = curveDialog_after.get_plot()

        #callback au deplacement de la ROI
        d.button_addRoi.clicked.connect(self.addROI)


        # conteneur pour les ROIs
        self.roi_dict = dict()

        # ==========un nom de roi par default====================

        # on lance l'interface
        d.setModal(True)

        ok = d.exec_()

        # ======================================================================
        # Si on clique sur OK
        # ======================================================================
        if ok:

            roi_dict = self.roi_dict

            rois_ranges = [roi_dict[roi_name]["range_item"].get_range() for roi_name in roi_dict.keys()]

            print("rois_ranges", rois_ranges)

            print("{} spectrums modified".format(len(self.new_spectrums)))

            #======================================================================
            #On applique au jeux de données
            #======================================================================
            for index, spectrum in self.new_spectrums.items():
                ds["X"][index] = spectrum

            self.gui.signals.signal_spectrumsToDisplayChanged.emit([])


    def getRangeItem(self, x_min, x_max):

        range = make.range(x_min, x_max)

        random_color = self.bl.getNextColor()

        random_color.setAlpha(38)

        range.brush = QtGui.QBrush(random_color)

        return range




    def applySpikeRemovalToSpectrum(self):

        W = self.W
        X = self.X

        spectrum_index = self.mcData.currentSpectrumIndex

        old_spectrum = X[spectrum_index]

        new_spectrum = old_spectrum


        for roi in self.roi_dict.values():

            x_min, x_max = roi["range_item"].get_range()

            idxs_xmin = W >= x_min
            idxs_xmax = W <= x_max

            spectral_interval_idxs = np.where(idxs_xmin & idxs_xmax)[0].tolist()
            #print("spectral_interval_idxs:",spectral_interval_idxs)

            if len(spectral_interval_idxs) < 2:
                print("error: Invalid interval")
                return

            else:
                print("Channels for ROI:", len(spectral_interval_idxs))

            idx_xmin = spectral_interval_idxs[0]
            idx_xmax = spectral_interval_idxs[-1]

            xmin = W[idx_xmin]
            xmax = W[idx_xmax]

            if type(W is list):
                W_roi = W[idx_xmin: idx_xmax]
            else:
                W_roi = W[spectral_interval_idxs]


            ymin = X[spectrum_index][idx_xmin]
            ymax = X[spectrum_index][idx_xmax]

            a = (ymax - ymin) / (xmax - xmin)

            b = 0.5 * (ymin + ymax - a * (xmin + xmax))

            baseline = lambda x: a * x + b

            baseline_values = baseline(W_roi)

            new_spectrum[idx_xmin:idx_xmax] = baseline_values


        self.new_spectrums[spectrum_index] = new_spectrum

        curve = self.guiDatas["curveAfter"]
        plot  = self.guiDatas["plotAfter"]

        curve.set_data(W, new_spectrum)
        plot.replot()



    def addROI(self, x_min = None, x_max = None, roi_name = None):

        # =======================================================================
        # ajout d'une ROI par defaut
        # =======================================================================

        if roi_name is None:

            ds = self.mcData.datasets.getDataset()

            mid_point = int(len(ds["W"]) / 2)

            x_min = ds["W"][int(mid_point - mid_point / 2)]
            x_max = ds["W"][int(mid_point + mid_point / 2)]

            # ====================================================================
            # on creer un nom par defaut
            # ====================================================================
            counter = getattr(self, "spectralROICreation_counter", 0)

            roi_name = "auto_named_%d" % (counter)

            self.spectralROICreation_counter = counter + 1


        # =======================================================================
        # Creation d'une entree dans le dict des ROIs
        # =======================================================================
        roi = dict()

        roi["min"] = x_min
        roi["max"] = x_max

        roi["range_item"] = self.getRangeItem(x_min, x_max)

        self.roi_dict[roi_name] = roi

        # =========================================================
        # Ajout de la ROI au plot
        # =========================================================
        plot = self.guiDatas["plotBefore"]

        plot.add_item(roi["range_item"])

        plot.replot()



