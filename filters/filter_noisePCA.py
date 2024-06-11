import time
from functools import partial
from threading import Thread

import numpy as np

import time
from functools import partial
from threading import Thread

from PyQt5 import uic
from PyQt5.QtCore import pyqtSignal
from plotpy.builder import make
from plotpy.plot import PlotDialog,PlotOptions
from businessLogic.mainLogic import MCBusinessLogic

from filters.dataFilter import DataFilter, FilterException


class Filter_noisePCA(DataFilter):

    updateProgress = pyqtSignal(float)
    updateDisplayedSpectrum = pyqtSignal()
    accepted = pyqtSignal()


    def __init__(self, workFile):

        super().__init__()

        if workFile: self.setWorkFile(workFile)

        self.button_title = "Noise PCA"

    def run(self, W, X, args_dict):

        # =====================================================================#
        #                           GUI
        # =====================================================================#
        d = uic.loadUi("assets//ui_files//filter_noise_pca.ui")
        d.setWindowTitle("PCA Noise filtering")

        ds = args_dict["ds"]
        self.ds = ds

        # ====================reference=========================================
        self.guiRefsContainer = guiRefs = dict()
        guiRefs["panel"] = d

        # ======================================================================
        # On ajoute les fonctions callback et elements pour l'affichage interactif
        # ======================================================================
        curveDialogNoiseFiltering = PlotDialog(edit = False, toolbar = False,options = PlotOptions(type="curve"))
 
        curve_plot = curveDialogNoiseFiltering.get_plot()
   
        d.graphsContainerLayout.addWidget(curveDialogNoiseFiltering)
      
        max_pcs_nb = min(len(X),len(W)-1)

        d.spinbox_pcs_nb.setRange(0, max_pcs_nb)
        d.spinbox_pcs_nb.setValue(min(5, max_pcs_nb))
        d.spinbox_sampleIndex.setRange(0, len(X)-1)
        d.horizontalSlider_sampleIndex.setMinimum(0)
        d.horizontalSlider_sampleIndex.setMaximum(len(X)-1)
        d.horizontalSlider_sampleIndex.setValue(0)

        f1 = lambda v:d.spinbox_sampleIndex.setValue(v)
        d.horizontalSlider_sampleIndex.valueChanged.connect(f1)

        # ======================================================================
        #               Initialisation des curves
        # ======================================================================
        #pcs_nb, sampleIndex = self._get_parameters_from_gui()

        projections = ds["projections"]

        if "PCA" not in projections:
            raise FilterException("Please perform PCA before applying this filter")

        # ================================================================================
        #   Initialisation curves
        # ================================================================================
        proj = projections["PCA"]

        spectrum          = [0 for i in range(len(W))]
        spectrum_filtered = [0 for i in range(len(W))]
        residual          = [0 for i in range(len(W))]

        #================================================================================

        curve_before   = make.curve(W, spectrum, color = "b")
        curve_filtered = make.curve(W, spectrum_filtered, color = "g")
        curve_residual = make.curve(W, residual, color = "r")

        curve_plot.add_item(curve_before)
        curve_plot.add_item(curve_filtered)
        curve_plot.add_item(curve_residual)


        # ================================================================================
        #   Initialisation image
        # ================================================================================
        # img_w = ds["image_width"]
        # img_h = ds["image_height"]
        #
        # residual_image = np.zeros((img_h, img_w), dtype=np.float32)
        # imageItem = make.image(residual_image)
        #
        # image_plot.add_item(imageItem)

        # ================================================================================
        #   On garde les references
        # ================================================================================
        guiRefs["curve_before"]   = curve_before
        guiRefs["curve_filtered"] = curve_filtered
        guiRefs["curve_residual"] = curve_residual
        guiRefs["curve_plot"]     = curve_plot
        # guiRefs["image_plot"]     = image_plot
        # guiRefs["image_item"]     = imageItem
        guiRefs["progress_bar"]   = d.progressBar



        # =============Connexion callbacks======================================
        gui_cb_1 = partial(self._gui_callback, panel=d, W=W, X=X, proj=proj, reprocess_residuals=True)
        gui_cb_2 = partial(self._gui_callback, panel=d, W=W, X=X, proj=proj, reprocess_residuals=False)
        processing_method = partial(self._process_all, W = W, X = X, proj = proj)

        d.spinbox_pcs_nb.valueChanged.connect(gui_cb_1)
        d.spinbox_sampleIndex.valueChanged.connect(gui_cb_2)

        d.button_process.clicked.connect(processing_method)

        self.updateProgress.connect(self._updateProgressBar)

        gui_cb_1() #mise a jour des plots à l'initialisation
        # ======================================================================
        #
        # ======================================================================
        d.exec_()

        if hasattr(self, "spectrums_noise_filtered"):
            return self.spectrums_noise_filtered, list(range(len(X)))

        else:
            raise FilterException("PCA Noise Filtering not launched")

    def _get_parameters_from_gui(self):

            guiRefs = self.guiRefsContainer
            d = guiRefs["panel"]

            sampleIndex = int(d.spinbox_sampleIndex.value())
            pcs_nb      = int(d.spinbox_pcs_nb.value())

            return pcs_nb, sampleIndex


    def _gui_callback(self, panel, W, X, proj,reprocess_residuals):
        """
        Methode de mise a jour de l'affichage du plot avant/apres filtering en fonction
        des parametres de la GUI
        """

        pcs_nb, sampleIndex = self._get_parameters_from_gui()

        print("pcs_nb, sampleIndex:", pcs_nb, sampleIndex)

        # ================================================================================
        #       On reprend les references aux plots
        # ================================================================================
        guiRefs = self.guiRefsContainer

        d              = guiRefs["panel"]
        curve_before   = guiRefs["curve_before"]
        curve_filtered = guiRefs["curve_filtered"]
        curve_residual = guiRefs["curve_residual"]
        curve_plot     = guiRefs["curve_plot"]
        # image_plot     = guiRefs["image_plot"]
        # image_item     = guiRefs["image_item"]

        # ================================================================================
        #       Calcul du spectre
        # ================================================================================
        spectrum = X[sampleIndex]

        if reprocess_residuals or not (hasattr(self, "spectrums_filtered") and hasattr(self, "residuals")):

            spectrum_filtered  = [0 for i in range(len(W))] #initialisation
            spectrums_filtered = np.zeros((len(X),len(W)))  # initialisation

            for i in range(0, pcs_nb):
                 vector_name = proj["vectors_names"][i]
                 spectrum_filtered += proj["values_by_vector"][vector_name][sampleIndex] * proj["vectors"][vector_name]

                 vector = np.array(proj["vectors"][vector_name])
                 values  = np.array(proj["values_by_vector"][vector_name])

                 spectrums_filtered += values[:,np.newaxis] * vector[np.newaxis,:]

            residuals = X - spectrums_filtered

            self.spectrums_filtered = spectrums_filtered
            self.residuals = residuals



        spectrums_filtered = self.spectrums_filtered
        residuals = self.residuals

        residuals_sqsum = np.sum(residuals ** 2, axis=1)
        residual = residuals[sampleIndex]
        spectrum_filtered = spectrums_filtered[sampleIndex]

        # ================================================================================
        #       Mise à jour des plots
        # ================================================================================
        curve_before.set_data(W, spectrum)
        curve_filtered.set_data(W, spectrum_filtered)
        curve_residual.set_data(W, residual)

        curve_plot.do_autoscale()
        curve_plot.replot()

        # ================================================================================
        #       Mise à jour de l'image du residu
        # ================================================================================
        # ds  = self.ds
        # img_w, img_h = ds["image_width"], ds["image_height"]
        # residual_image = np.zeros((img_h,img_w), dtype=np.float32)
        # lut = ds["idx_to_img_coo"]
        # for sp_idx in range(len(X)):
        #     x,y = lut[sp_idx]
        #     residual_image[x,y] = residuals_sqsum[sp_idx]
        #
        # image_item.set_data(residual_image)
        # image_plot.replot()


    def _process_all(self, W, X, proj):
        """
        process noise filtering on all dataset
        """

        self.noisePCAFilterRunning = True

        myThread = Thread(target = self._process_all_thread, args = (W, X, proj))
        myThread.daemon = True
        myThread.start()


    def _process_all_thread(self, W, X, proj):

        # ============= On recupere les donnees de la gui =======================
        pcs_nb, _ = self._get_parameters_from_gui()

        #if self.useWorkFile():
        start_time = time.time()

        spectrums_filtered = self.workFile.getTempHolder(X.shape)

        print("spectrums_filtered.shape", spectrums_filtered.shape)

        for i in range(0, pcs_nb):
             vector_name = proj["vectors_names"][i]
             spectrums_filtered += np.outer(proj["values_by_vector"][vector_name][:],proj["vectors"][vector_name])
             self.updateProgress.emit(100.0 * i / pcs_nb)

        self.updateProgress.emit(100)

        print("done in %.2f" % (time.time() - start_time))

        self.noisePCAFilterRunning = False
        self.spectrums_noise_filtered = spectrums_filtered
        self.accepted.emit()

    def _updateProgressBar(self, i):

        pb = self.guiRefsContainer["progress_bar"]

        if i >= 0: pb.setValue(i)
        else:      pb.reset()


if __name__ == "__main__":
    pass