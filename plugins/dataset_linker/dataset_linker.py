import copy
from functools import partial
from threading import Thread

from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QPushButton

from datasetsMatcherMulti import DatasetsMatcher
from helpers import mc_logging


class DatasetLinker(QObject):

    signal_prepareDsMatcherDatasDone = pyqtSignal(dict, dict)

    def __init__(self, bl, mcData, gui):
        super().__init__()

        #TODO: a inserer dans le bloc "Overlap" de l'onglet Multiviewer

        self.tab = "MultiViewer"
        self.family = ""
        self.name   = "dataset linker"
        self.tooltip_text = "tooltip text..."

        self.menu_item = QPushButton("Link...",
                                     clicked = self.linkDatasetsClicked)

        self.bl = bl
        self.mcData = mcData
        self.gui = gui


        self.mainWindow = self.gui.main.mainWindow


        self.signal_prepareDsMatcherDatasDone.connect(self._prepareDsMatcherDatas_done)


    def linkDatasetsClicked(self):

        self.gui.datasets.signal_disableGuiActionsOnDataset.emit(False)

        myThread = Thread(target = self._prepareDsMatcherDatas_thread)
        myThread.daemon = True
        myThread.start()


    def _prepareDsMatcherDatas_thread(self):
        ds_infos, relationships = self.bl.relationships.prepareDsMatcherDatas(self.gui.main.displayProgressBar)
        self.signal_prepareDsMatcherDatasDone.emit(ds_infos, relationships)


    def _prepareDsMatcherDatas_done(self, ds_infos, relationships):
        self.linkDatasetsDialog(ds_infos, relationships)


    def linkDatasetsDialog(self, ds_infos, relationships):
        """
        Methode appelant le programme d'appariement des datasets.py
        """
        print("inside linkDataset:")

        #        p       = self.gui.panel
        #        ds_name = self.currentDatasetName
        #        ds      = self.mcData.datasets.py[ds_name]

        dsMatcher = DatasetsMatcher()

        print("after preparing:")
        print(("relationships.keys()", list(relationships.keys())))

        dsMatcher.set_datasets(ds_infos, relationships)

        dsMatcher.panel.button_ok.clicked.connect(partial(self.linkDatasetsDialog_accepted, dsMatcher))
        dsMatcher.panel.button_cancel.clicked.connect(partial(self.linkDatasetsDialog_canceled, dsMatcher))
        dsMatcher.closeEvent = self.linkDatasetsDialog_canceled(dsMatcher)

        dsMatcher.show()
        dsMatcher.activateWindow()
        dsMatcher.raise_()
        dsMatcher.setFocus()

    def linkDatasetsDialog_canceled(self, dsMatcher):

        mc_logging.debug("linking canceled")
        dsMatcher.close()
        self.gui.datasets.signal_enableGuiActionsOnDataset.emit()

    def linkDatasetsDialog_accepted(self, dsMatcher):

        # TODO: ils faudrait enregistrer ca dans un element à part et non dans le ds en cour!!

        mc_logging.debug("inside linkDatasetsDialog_accepted")

        # ds = self.mcData.datasets.py.getDataset()
        print("self.mcData.relationships.relationships_dict")
        print((self.mcData.relationships.relationships_dict))

        #if getattr(self, "relationships", None):
        #    print((self.mcData.relationships.relationship_dict))
        #
        #else:
        #    print("relationship  doesn't exists")

        self.mcData.relationships.relationships_dict = copy.deepcopy(dsMatcher.relationships)

        dsMatcher.close()

        self.gui.datasets.signal_enableGuiActionsOnDataset.emit()
        # mise a jour des positions des representations
        self.gui.main.signal_updateRepresentationsDisplay_inMultiDatasetExplorer.emit(True)
        # mise a jour de la liste des datasets.py disponibles(tous ceux ayant été linked)
        self.gui.main.signal_updateLinkedDatasetsList_inMultiDatasetExplorer.emit()
        # mise a jour des icones dans la liste des datasets.py
        self.gui.datasets.signal_updateDatasetsListWithoutRefresh.emit()


