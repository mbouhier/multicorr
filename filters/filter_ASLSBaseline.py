import time
from functools import partial
from threading import Thread

from PyQt5 import uic
from PyQt5.QtCore import pyqtSignal
from plotpy.builder import make
from plotpy.plot import PlotDialog, PlotOptions

from filters.asls import baseline_als, paralelized_baseline_als
from filters.dataFilter import DataFilter, FilterException


class Filter_ASLSBaseline(DataFilter):

    updateProgress = pyqtSignal(float)
    updateDisplayedSpectrum = pyqtSignal()
    accepted = pyqtSignal()


    def __init__(self, workFile = None):
        super().__init__()

        if workFile: self.setWorkFile(workFile)

        self.button_title = "ASLS"

        self.lambda_min = 100
        self.lambda_max = 10000000
        self.lambda_step = 100
        self.lambda_default = 100000

        self.p_min = 0.0001
        self.p_max = 0.1
        self.p_step = 0.001
        self.p_default = 0.001


    def run(self, W, X, args_dict = None):

        #=====================================================================#
        #                           GUI
        #=====================================================================#
        d = uic.loadUi("assets//ui_files//filter_asls.ui")
        d.setWindowTitle("Asymetric Least Squares - Baseline correction")

        #====================reference=========================================
        self.guiRefsContainer = guiRefs = dict()
        guiRefs["panel"]      = d

        #======================================================================
        #On ajoute les fonctions callback et elements pour l'affichage interactif
        #======================================================================
        curveDialogBeforeAsls = PlotDialog(edit = False, toolbar = False, options = PlotOptions(type="curve"))
        curveDialogAfterAsls  = PlotDialog(edit = False, toolbar = False, options = PlotOptions(type="curve"))

        plot_before = curveDialogBeforeAsls.get_plot()
        plot_after  = curveDialogAfterAsls.get_plot()

        d.graphsContainerLayout.addWidget(curveDialogBeforeAsls)
        d.graphsContainerLayout.addWidget(curveDialogAfterAsls)

        #======================================================================
        #Definition bornes sliders et spinbox
        #======================================================================
        #lamba en int
        d.spinbox_lam.setRange(self.lambda_min, self.lambda_max)
        d.spinbox_lam.setValue(self.lambda_default)
        d.horizontalSlider_lam.setMinimum(self.lambda_min)
        d.horizontalSlider_lam.setMaximum(self.lambda_max)
        d.horizontalSlider_lam.setValue(self.lambda_default)
        #p en float
        d.spinbox_p.setRange(self.p_min, self.p_max)
        d.spinbox_p.setValue(self.p_default)
        d.horizontalSlider_p.setMinimum(self.p_min*1/self.p_min) #transforme en int
        d.horizontalSlider_p.setMaximum(self.p_max*1/self.p_min)
        d.horizontalSlider_p.setValue(self.p_default*1/self.p_min)

        d.spinbox_sampleIndex.setRange(0, len(X)-1)
        d.horizontalSlider_sampleIndex.setRange(0, len(X) - 1)

        f1 = lambda v:d.spinbox_sampleIndex.setValue(v)
        d.horizontalSlider_sampleIndex.valueChanged.connect(f1)

        f2 = lambda v:d.spinbox_lam.setValue(v)
        d.horizontalSlider_lam.valueChanged.connect(f2)

        f3 = lambda v:d.spinbox_p.setValue(v*self.p_min) #on remet en float
        d.horizontalSlider_p.valueChanged.connect(f3)

        #======================================================================
        #               Initialisation des curves
        #======================================================================
        lam, p, niter, sampleIndex = self._get_parameters_from_gui()

        spectrum = X[sampleIndex]

        baseline = baseline_als(spectrum, lam, p, niter)

        curve_before   = make.curve(W, spectrum, color="b")
        curve_baseline = make.curve(W, baseline, color="r")
        curve_after    = make.curve(W, spectrum - baseline, color="g")

        plot_before.add_item(curve_before)
        plot_before.add_item(curve_baseline)
        plot_after.add_item(curve_after)

        guiRefs["curve_before"]   = curve_before
        guiRefs["curve_baseline"] = curve_baseline
        guiRefs["curve_after"]    = curve_after
        guiRefs["plot_before"]    = plot_before
        guiRefs["plot_after"]     = plot_after
        guiRefs["progress_bar"]   = d.progressBar


        #=============Connexion callbacks======================================
        func1 = partial(self._gui_callback, panel = d, W = W, X = X)
        func2 = partial(self._process_all, W = W, X = X)


        for item in (d.spinbox_niter,
                     d.spinbox_lam,
                     d.spinbox_p,
                     d.spinbox_sampleIndex,
                     d.horizontalSlider_lam,
                     d.horizontalSlider_p,
                     d.horizontalSlider_sampleIndex):

            item.valueChanged.connect(func1)

        d.button_process.clicked.connect(func2)

        self.updateProgress.connect(self._updateProgressBar)
        self.updateDisplayedSpectrum.connect(self._updateDisplayedSpectrum)

        #======================================================================
        #
        #======================================================================
        d.exec_()

        if hasattr(self,"spectrums_asls"):
            return self.spectrums_asls, list(range(len(X)))

        else:
           raise FilterException("Asls aborted")

    def _get_parameters_from_gui(self):

        """
        Convenient methode to retrieve paramteres from GUI
        """
        guiRefs = self.guiRefsContainer
        d = guiRefs["panel"]

        niter       = int(d.spinbox_niter.value())
        lam         = float(d.spinbox_lam.value())
        p           = float(d.spinbox_p.value())
        sampleIndex = int(d.spinbox_sampleIndex.value())

        return lam, p, niter, sampleIndex

    def _updateDisplayedSpectrum(self):

        guiRefs = self.guiRefsContainer
        l = self.lastAsls

        curve_before   = guiRefs["curve_before"]
        curve_baseline = guiRefs["curve_baseline"]
        curve_after    = guiRefs["curve_after"]
        plot_before    = guiRefs["plot_before"]
        plot_after     = guiRefs["plot_after"]

        #d.spinbox_sampleIndex.setValue(l["index"])

        curve_before.set_data(l["W"], l["spectrum"])
        curve_baseline.set_data(l["W"], l["baseline"])
        curve_after.set_data(l["W"], l["spectrum"] - l["baseline"])


        plot_before.do_autoscale()
        plot_after.do_autoscale()

        plot_before.replot()
        plot_after.replot()

    def _gui_callback(self, panel, W, X):
        """
        Methode de mise a jour de l'affichage du plot avant/apres asls en fonction
        des parametres de la GUI
        """

        lam, p, niter, sampleIndex = self._get_parameters_from_gui()


        spectrum  = X[sampleIndex]
        baseline = baseline_als(spectrum, lam, p, niter)


        self.lastAsls = {"spectrum" : spectrum,
                         "index" : sampleIndex,
                         "W" : W,
                         "baseline" : baseline}


        self._updateDisplayedSpectrum()

    def _process_all(self, panel, W, X):
        """
        process asls on all dataset
        """
        self.aslsFilterRunning = True

        myThread = Thread(target = self._process_all_thread, args=(W, X))
        myThread.daemon = True
        myThread.start()


    def _updateProgressBar(self, i):

        d = self.guiRefsContainer["panel"]

        if i >= 0:
            d.progressBar.setValue(i)
        else:
            d.progressBar.reset()


    def _process_all_thread(self, W, X):

        paralelize = False

        #============= On recupere les donnees de la gui =======================
        lam, p, niter, sampleIndex = self._get_parameters_from_gui()


        if self.useWorkFile():
            baselines_asls = self.workFile.getTempHolder(X.shape)

        else:
            baselines_asls = [None for i in X]

        start_time = time.time()


        if not paralelize:

            print("Processing asls (standard version)")

            for i,spectrum in enumerate(X):

                baselines_asls[i] = baseline_als(spectrum, lam, p, niter)

                self.lastAsls = {"spectrum" : spectrum,
                                 "index" : i,
                                 "W" : W,
                                 "baseline" : baselines_asls[i]}

                #Show preview only every N spectrums
                show_every_N = 1
                if i % show_every_N == 0:

                    self.updateProgress.emit(100.0 * i / len(X))
                    self.updateDisplayedSpectrum.emit()


            self.updateProgress.emit(100)

        else:
            print("Processing asls (paralel version)")
            baselines_asls = paralelized_baseline_als(X, lam, p, niter)


        print("done in %.2f" % (time.time() - start_time))


        self.aslsFilterRunning = False


        if self.useWorkFile():
            spectrums_asls = self.workFile.getTempHolder(X.shape)

            print("copying results...")

            for i in range(len(spectrums_asls)):
                spectrums_asls[i] = X[i] - baselines_asls[i]

            print("copying done!")

            self.spectrums_asls = spectrums_asls


        else:

            self.spectrums_asls = X[:] - baselines_asls

        self.accepted.emit()



if __name__ == "__main__":
    pass