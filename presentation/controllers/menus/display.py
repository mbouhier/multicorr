from PyQt5.QtCore import pyqtSignal, QObject

# from presentation.controllers.main            import MCPresentationController_main
# from presentation.controllers.representations import MCPresentationController_representations
# from presentation.controllers.spectrums       import MCPresentationController_spectrums

from PyQt5.QtCore import pyqtSignal, QObject



class MCPresentationController_menu_display(QObject):

    signal_updateProbesShapesAndPlots_inMultiDatasetExplorer = pyqtSignal()

    metadatasDisplayModes = ["none", "projection values", "fit result", "fit result normalized", "channel values"]

    def __init__(self, qt_panel, mcBusinessLogic, mcData, mainWindow):
        super().__init__()
        print(type(self).__name__ + " initialized")

        self.bl     = mcBusinessLogic
        self.mcData = mcData
        self.panel  = qt_panel
        self.mainWindow = mainWindow


    def setMetadataDisplayedMode(self, ds_name, display_mode):
        p = self.panel
        ds = self.mcData.datasets.getDataset(ds_name)

        ds["display"]["metadata_type"] = display_mode

        self.signal_updateProbesShapesAndPlots_inMultiDatasetExplorer.emit()

    def getMetadataDisplayedMode(self, ds_name = None):
        p = self.panel

        ds = self.mcData.datasets.getDataset(ds_name)

        default_type = p.combo_metadatas.currentText()

        metadata_type = ds.get("display", {}).get("metadata_type", default_type)

        return metadata_type

