import os

from PyQt5 import QtWidgets
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import *

from helpers import mc_logging
from helpers.data import singleton
from helpers.dialogs import InputDialogWithColorChoice
from threading import Thread
from helpers.io.datasetsImporter import DatasetsImporter
from presentation.controllers import main, representations, spectrums, projections, signals, datasets
from helpers.bigDataTools import fillByChunk

@singleton
class MCPresentationController_io(QObject):

    def __init__(self, qt_panel, mcBusinessLogic, mcData, mainWindow):
        super().__init__()
        print(type(self).__name__ + " initialized")

        self.bl     = mcBusinessLogic
        self.mcData = mcData
        self.panel  = qt_panel
        self.mainWindow = mainWindow
        # self.view  = mcPresentationView
        # self.model = mcPresentationModel

        self.main     = main.MCPresentationController_main(qt_panel, mcBusinessLogic, mcData, mainWindow)
        self.datasets = datasets.MCPresentationController_datasets(qt_panel, mcBusinessLogic, mcData, mainWindow)
        self.signals  = signals.MCPresentationController_signals()

    def makeConnections(self):
        print("inside makeConnections in MCPresentationController_io")
        p = self.panel
        p.saveProjectButton.clicked.connect(self.saveProject)
        p.loadButton.clicked.connect(self.loadFile)

        self.main.signal_projectLoadingDone.connect(self.projectLoadingDone)

    def saveProject(self):
        """
        Save Datasets in HDF5 mode
        """
        print("Saving current project...")

        if len(self.mcData.datasets.names()) < 1: return False

        preferredName = self.mcData.datasets.names()[0] + "_project"

        filename = QtWidgets.QFileDialog.getSaveFileName(parent = self.mainWindow,
                                                         caption = "Save file",
                                                         directory = preferredName,
                                                         filter = "*.h5")[0]

        if not filename:
            return False
        else:
            try:
                self.bl.io.saveProject(filename)
                return True

            except OSError as e:
                mc_logging.error("Can't save project")
                mc_logging.error(e)
                return False


    def displayFilenamesInPathLine(self, filenames):

        p = self.panel

        # on converti les slash en backslash
        if type(filenames) is str:

            filenames = os.path.normpath(filenames)
            p.fileNameLine.setText(filenames)

        elif type(filenames) is list:

            filenames = [os.path.normpath(f) for f in filenames]
            p.fileNameLine.setText(",".join(filenames))

    def askForDatasetNameAndColor(self, default_ds_name = ""):

        # on creer un nom unique par default
        i = 0


        if not default_ds_name:
            base_name = "original_"
            default_ds_name = base_name + str(i)
        else:
            base_name = default_ds_name


        while default_ds_name in self.mcData.datasets.names():
            i = i + 1
            default_ds_name = base_name + str(i)
            # TODO: pas de verification si on entre un nom existant


        default_color = self.bl.getNextColor()

        dialog = InputDialogWithColorChoice(self.panel)

        new_ds_name, color, ok = dialog.getTextAndColor("Dataset creation",
                                                        "Please enter a name for new dataset:",
                                                        default_ds_name,
                                                        default_color)

        if ok:
            default_ds_name = new_ds_name
            default_color = color

        else:
            mc_logging.debug("using default name for dataset: %s" % (default_ds_name,))

        return default_ds_name, default_color


    def askForDatafilesChoice(self):
        """
        Open dialog asking for files selection
        :return: filenames list
        """
        filenames = QFileDialog.getOpenFileNames(self.mainWindow, "Open Dataset File...")[0]

        return filenames


    def projectLoadingDone(self):

        print("DEBUG: inside projectLoadingDone")

        datasets = self.mcData.datasets
        # relationships = self.mcData.relationships

        self.datasets.signal_updateDatasetsList.emit()

        first_ds_name = datasets.names()[0]
        self.datasets.changeCurrentDataset(first_ds_name)

        print(("currentDatasetName:", datasets.currentDatasetName))

        # probleme avec groupes sinon
        self.signals.signal_groupsUpdated.emit()
        self.datasets.signal_enableGuiActionsOnDataset.emit()
        self.main.signal_updateLinkedDatasetsList_inMultiDatasetExplorer.emit()  # def keyPressEvent(self, e):

    def loadProjectAsynchronously(self, filename):
        """
        Load Project asynchronously to avoid gui lag
        """
        self.datasets.signal_disableGuiActionsOnDataset.emit(True)
        self.bl.io.loadProject(filename, self.main.displayProgressBar)
        self.main.signal_projectLoadingDone.emit()
        self.datasets.signal_enableGuiActionsOnDataset.emit()

    def loadProject(self, filename=None, ask_for_confirm=True):

        datasets = self.mcData.datasets
        relationships = self.mcData.relationships
        mainWindow = self.mainWindow

        if not filename:

            filename = str(QFileDialog.getOpenFileName(mainWindow, "Open Project File...", '*.h5'))[0]
            if not filename: return False

        if ask_for_confirm:

            # =======avertissement perte du projet en cour==========================

            if datasets.count() > 0:

                reply = QtWidgets.QMessageBox.question(mainWindow,
                                                       'Confirmation',
                                                       'This file is a project file. Current datasets will be replaced, are you sure?',
                                                       QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                                       QtWidgets.QMessageBox.No)

                if reply == QtWidgets.QMessageBox.Yes:
                    pass
                else:
                    return False
                # ======================================================================

        print(("Opening project:", filename))

        myThread = Thread(target = self.loadProjectAsynchronously, args=(filename,))
        myThread.daemon = True
        myThread.start()
        # print "self.mcData.datasets.py.keys() after project loaded",self.mcData.datasets.py.keys()


    def loadFile(self, filenames_list = []):

        p = self.panel

        self.main.signal_updateProgress.emit(0)

        importer = DatasetsImporter(workFile = self.bl.io.workFile)

        # ======================Pour le dossier de csv==========================
        #        cdir = os.path.dirname(os.path.abspath(__file__)) + "\\"
        #        f_names = ["Fe % masse.csv","Ca % masse.csv","K % masse.csv",
        #                   "Cl % masse.csv","S % masse.csv","P % masse.csv",
        #                   "Si % masse.csv","Al % masse.csv","Mg % masse.csv",
        #                   "Na % masse.csv","O % masse.csv"]
        #        filename = [cdir + 'bin\\unit_test_datasets\\fichiers_csv\\' + f_name for f_name in f_names]
        # ======================================================================



        # ============ Fenetre de dialogue choix de fichier ===================
        if not filenames_list:
            filenames_list = self.askForDatafilesChoice()

        # ====================== fichiers Raman================================
        # filename = "C://Users//mbouhier//Documents//datasets.py//Corpus//AmXIVE//zoneDx450//Raman//160212_AmXIVE//Stream_p5_90s_slalom_zoneDx450.wxd"
        # filename = "C://Users//mbouhier//Documents//datasets.py//Stream_p5_30s_slalom_zoneDx450_20090011.wxd"
        # ======================================================================

        # ====================== Tests Emilande================================
        # filename = "C://Users//mbouhier//Documents//datasets.py//emilande//hc10_carto_19_02_16crtr.wxd"
        # ======================================================================

        # ====================== Gros fichiers ================================
        # filename = "C://Users//mbouhier//Documents//datasets.py//Corpus//AmXIVE//zoneDx450//Raman//160212_AmXIVE//Stream_p5_90s_slalom_zoneDx450.wxd"
        # filename = "C://Users//mbouhier//Documents//datasets.py//Stream_p5_30s_slalom_zoneDx450_20090011.wxd"
        # ======================================================================

        if not filenames_list:
            print("no filename(s) specified")
            return False

        if len(filenames_list) == 1 and self.bl.io.isProjectFile(filenames_list[0]):
            self.loadProject(filenames_list[0])
            return True

        self.displayFilenamesInPathLine(filenames_list)

        print("Loading dataset, please wait...")

        # ======================================================================
        #                  Ouverture des differents types
        #           de fichiers grace au module DatasetsImporter
        # ======================================================================
        try:
            spectrums, W, xys, args = importer.loadFile(filenames_list, qt_mode = True)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self.mainWindow, "Loading Error", "Can't load file(s), see console for details")
            print("Loading error:")
            print(e)
            return

        mc_logging.debug("dataset_size: %d" % (len(spectrums),))

        # ==============Hack rapide=============================================
        # il faudrait que laodFile renvoi un ID vers un fichier hdf5, en attendant
        # il renvoi une liste dans le cas de memory error numpy au chargement
        # on convertie donc cette liste en dataset hdf5

        if type(spectrums) == list:
            print("converting list to hdf5 dataset (spectrums)")

            datasetShape = (len(spectrums), len(W))

            spectrums_hdf5 = self.bl.io.workFile.getTempHolder(datasetShape)

            fillByChunk(spectrums, spectrums_hdf5, progress_callback = self.main.displayProgressBar)

            spectrums = spectrums_hdf5

            print("conversion done")

        if type(xys) == list:
            print("converting list to hdf5 dataset (xys)")

            datasetShape = (len(xys), 2)

            xys_hdf5 = self.bl.io.workFile.getTempHolder(datasetShape)

            fillByChunk(xys, xys_hdf5, progress_callback = self.main.displayProgressBar)

            xys = xys_hdf5

            print("conversion done")

        # ======================================================================
        self.mcData.currentSpectrumIndex = 0
        # ======================================================================
        #                Ajout au dictionnaire de datasets.py
        # ======================================================================
        #le nom par default est le nom du fichier, auquelle on aura enlever l'extension
        if len(filenames_list)==1:
            default_ds_name = filenames_list[0].split("/")[-1]
            splitted_name = default_ds_name.split('.')
            if len(splitted_name)==2:
                default_ds_name = splitted_name[0]

        ds_name, ds_color = self.askForDatasetNameAndColor(default_ds_name)

        self.datasets.addDatasetToDict(name = ds_name, W = W, datas = spectrums, xys = xys, color = ds_color, args = args)

        # === Et on demande le chargement et affichage de ce dataset ===========
        self.datasets.changeCurrentDataset(name = ds_name)

        # ============ Creation d'un groupe de selection par default ============
        # self.addGroupToDict("Default_%s" % (default_ds_name), default_ds_name)
        # =======================================================================
        self.datasets.signal_enableGuiActionsOnDataset.emit()
