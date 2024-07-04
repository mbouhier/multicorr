from functools import partial

import numpy as np
from PyQt5 import uic, QtWidgets
from PyQt5.QtCore import pyqtSignal, QObject

from filters.dataFilter import FilterException
from filters.filter_ASLSBaseline import Filter_ASLSBaseline
from filters.filter_fluo import Filter_fluo
from filters.filter_noisePCA import Filter_noisePCA
from filters.filter_saturate import Filter_saturate
from filters.filter_spikes import Filter_spikes
from helpers.bigDataTools import normalizeHDF5
from helpers.data import singleton
from presentation.controllers import main, spectrums, signals, groups, datasets


@singleton
class MCPresentationController_filters(QObject):

    signal_filteringDone = pyqtSignal(str, str)

    FILTER_APPLIED_TO_CURRENT_DS = 0
    FILTER_CREATE_A_NEW_GROUP    = 1
    FILTER_CREATE_A_NEW_DS       = 2

    def __init__(self, qt_panel, mcBusinessLogic, mcData, mainWindow):
        super().__init__()
        print(type(self).__name__ + " initialized")

        self.bl     = mcBusinessLogic
        self.mcData = mcData
        self.panel  = qt_panel
        self.mainWindow = mainWindow

        self.main    = main.MCPresentationController_main(qt_panel, mcBusinessLogic, mcData, mainWindow)
        self.groups  = groups.MCPresentationController_groups(qt_panel, mcBusinessLogic, mcData, mainWindow)
        self.spectrums = spectrums.MCPresentationController_spectrums(qt_panel, mcBusinessLogic, mcData, mainWindow)
        self.datasets = datasets.MCPresentationController_datasets(qt_panel, mcBusinessLogic, mcData, mainWindow)
        self.signals = signals.MCPresentationController_signals()


        self.filter_application_choices = {self.FILTER_APPLIED_TO_CURRENT_DS : "Apply filter to current dataset",
                                           self.FILTER_CREATE_A_NEW_GROUP :    "Create a new group",
                                           self.FILTER_CREATE_A_NEW_DS :       "Create a new dataset"}

        self.filter_target = self.FILTER_APPLIED_TO_CURRENT_DS #default

        # self.view  = mcPresentationView
        # self.model = mcPresentationModel

    def makeConnections(self):

        self.signal_filteringDone.connect(self.notificateFilterDone)
        self.makeConnections_menuItems()


    def makeConnections_menuItems(self):
        # TODO: faire un ajout de boutons et connects automatique avec la liste des methodes disponibles
        p = self.panel

        p.buttonFilterSat.clicked.connect(partial(self.openFilteringDialog, filter_name = "filterSaturate"))
        #p.buttonFilterSpikes.clicked.connect(partial(self.openFilteringDialog, filter_name = "filterSpikes"))
        p.buttonFilterAsls.clicked.connect(partial(self.openFilteringDialog, filter_name = "filterAsls"))
        p.buttonFilterNoisePCA.clicked.connect(partial(self.openFilteringDialog, filter_name = "filterNoisePCA"))


    def cb_filter_target_changed(self, panel):
        d = panel
        combo_id = d.comboBox_filter_apply_type.currentIndex()
        self.filter_target = int(combo_id)

        if combo_id == self.FILTER_CREATE_A_NEW_DS:
            d.lineEdit_name.setVisible(True)
            d.label_name.setVisible(True)
            new_ds_name = self.mcData.datasets.currentDatasetName + "_filtered"
            d.lineEdit_name.setText(new_ds_name)
            self.new_ds_name = new_ds_name

        elif combo_id == self.FILTER_APPLIED_TO_CURRENT_DS:
            d.lineEdit_name.setVisible(False)
            d.label_name.setVisible(False)

        elif combo_id == self.FILTER_CREATE_A_NEW_GROUP:
            d.lineEdit_name.setVisible(False)
            d.label_name.setVisible(False)


    def openFilteringDialog(self, filter_name):

        ds = self.mcData.datasets.getDataset()
        d = uic.loadUi("assets//ui_files//filter_applyType.ui")
        d.setWindowTitle("Filtering")

        d.comboBox_filter_apply_type.addItems(self.filter_application_choices.values())

        self.cb_filter_target_changed(d) #initialisation
        d.comboBox_filter_apply_type.currentIndexChanged.connect(partial(self.cb_filter_target_changed,d))

        # ======================================================================
        # On ajoute les parametres à la boite de dialogue en fonction
        # des parametres demandés par le filtre
        # ======================================================================
        ok = d.exec_()

        # ============= On recupere les données de la gui =======================
        if ok:
            self.applyFilter(filter_name, self.filter_target)

        else:
            return

    # @my_pyqtSlot(str,str)
    def notificateFilterDone(self, filter_name, message):
        p = self.panel

        ds = self.mcData.datasets.getDataset()

        groups = ds["groups"]

        QtWidgets.QMessageBox.information(self.mainWindow, 'Filtering - %s' % (filter_name,), message)

        if filter_name in groups:
            p.tabWidget.setCurrentIndex(self.gui.main.getTabIndexByName("Representation"))



    def applyFilter(self, filter_name, filter_target):
        """
        Methode lancant les differents filtres

        Les filtres doivent renvoyer une copy du dataset modifié et la liste
        des indices modifiés/à modifier et prendre en entrée au minimum W et X

        dataset, indices = filter(W,X,other_params)
        """

        print("Applying Filter...")

        # ======================================================================
        # Chargement du jeux de données
        # ======================================================================
        useNormalizedData = self.spectrums.useNormalizedData

        ds = self.mcData.datasets.getDataset()
        W = ds["W"]

        if useNormalizedData:
            print("INSIDE useNormalizedData")
            X = self.datasets.getDataset_X_normalized()
        else:
            print("OUTSIDE useNormalizedData")
            X = ds["X"]

        # ======================================================================
        # Lancement du filtre
        # ======================================================================
        filters = DataFilters(workFile = self.mcData.workFile)

        # =========    remove fluo   ===========================================
        # TODO: generer les icones dynamiquement et prendre les filter_name depuis le nom des boutons

        try:
            if filter_name == "filterFluo":
                f = filters.getFilter(filter_name)
                X_filtered, idxs = f(W, X)


            if filter_name == "filterNoisePCA":
                f = filters.getFilter(filter_name)
                ds = self.mcData.datasets.getDataset()
                X_filtered, idxs = f(W, X, {"ds": ds,})

            elif filter_name == "filterSaturate":

                f = filters.getFilter(filter_name)
                X_filtered, idxs = f(W, X, {"threshold": 2,
                                            "Intensity threshold": 400,
                                            "Zeros number threshold": 10})



            elif filter_name == "filterSpikes":

                f = filters.getFilter(filter_name)
                X_filtered, idxs = f(W, X, {"maximum ratio mean data": 10,
                                            "maximum ratio": 5,
                                            "window size": 20})



            elif filter_name == "filterAsls":

                f = filters.getFilter(filter_name)
                X_filtered, idxs = f(W, X, {"p": 0,
                                            "lam": 0,
                                            "iterations": 0})

            else:
                print(('\nFilter "%s" is not defined' % (filter_name)))
                return


        except FilterException as e:
            QtWidgets.QMessageBox.warning(self.mainWindow, "Filtering Error", e.message)
            return

        # ======================================================================
        # Application du filtre
        # ======================================================================
        if filter_target == self.FILTER_APPLIED_TO_CURRENT_DS:
            # =====on enregistre le jdd=====
            if useNormalizedData:
                ds["X_normalized"] = X_filtered

            else:
                ds["X"] = X_filtered
                # le jdd original est modifié, on met donc a jour le X_normalized
                ds["X_normalized"] = normalizeHDF5(X_filtered, self.mcData.workFile, self.spectrums.normalizeMethod)

            # =====on recalcule des données de base du jdd=====
            print("reprocess mean data")
            mean_datas = np.mean(X_filtered, axis=0)
            print("mean data done")

            if useNormalizedData:
                ds["mean_datas_normalized"] = mean_datas
            else:
                ds["mean_datas"] = mean_datas

        if filter_target == self.FILTER_CREATE_A_NEW_GROUP:
            # TODO: attention, pour l'instant on enleve tous les groupes de type "filters"
            self.groups.removeGroupFromDict(family = 'filters', updateDisplay = True)
            self.groups.addGroupToDict(filter_name, family = 'filters', indexes = idxs)

        if filter_target == self.FILTER_CREATE_A_NEW_DS:
            #TODO: tester si le nom n'existe pas deja!
            ds = self.mcData.datasets.getDataset()
            ds_name = self.mcData.datasets.currentDatasetName
            new_ds_name = self.new_ds_name

            self.datasets.addDatasetToDict(name=new_ds_name,
                                           W=ds["W"],
                                           datas=X_filtered,
                                           xys=ds["xys"],
                                           )


            self.bl.coordinates.setTransformationMatrixToIdentity(ds_name, new_ds_name)
            self.datasets.changeCurrentDataset(new_ds_name)

        # =====on met à jours l'affichage, on utilise un signal==================
        # car on est dans un thread non QT
        self.datasets.signal_updateDisplayOnDatasetChange.emit(True)

        # pour les groupes (redondant avec updateDisplay)
        self.signals.signal_groupsUpdated.emit()

        # ======================================================================
        # Message d'information
        # ======================================================================
        mess = "%d spectrum(s) processed" % (len(idxs),)

        self.signal_filteringDone.emit(filter_name, mess)
        print(mess)

        print("Filtering done!")

    # ===========================================================================
    #                   Curves Fit
    # ===========================================================================


class DataFilters(QtWidgets.QMainWindow):

    #=========================================================================#
    #                    Methodes de base                                     #
    #=========================================================================#
    updateProgress = pyqtSignal(float)
    updateDisplayedSpectrum = pyqtSignal()
    accepted = pyqtSignal()


    def useWorkFile(self):
        return hasattr(self, "workFile")

    def __init__(self, workFile = None):

        super().__init__()

        if workFile: self.workFile = workFile

        #instantiation des filtres
        self._filters_refs = {  "filterFluo"    : Filter_fluo(workFile),
                                "filterSaturate": Filter_saturate(workFile),
                                "filterSpikes"  : Filter_spikes(workFile),
                                "filterAsls"    : Filter_ASLSBaseline(workFile),
                                "filterNoisePCA": Filter_noisePCA(workFile),
                              }
        self.filtersDictionnary = { name: filter.run for name,filter in self._filters_refs.items()}



    def getFiltersNames(self):
        return list(self.filtersDictionnary.keys())


    #TODO, ne plus passer par un dictionary preexistant mais le generer en fonction des nom de fichier dans un dossier "Filters"
    def getFilter(self, filter_name):

        if filter_name in self.filtersDictionnary:
            return self.filtersDictionnary[filter_name]

        else:
            print("Error: filter '%s' doesn't exists" % (filter_name))
            return None


    def _updateProgressBar(self, i, pb_guiref):

        if i >= 0: pb_guiref.setValue(int(i))
        else:      pb_guiref.reset()