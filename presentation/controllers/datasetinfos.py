from PyQt5.QtCore import QObject


from helpers.data import singleton

from presentation.controllers import main, signals, menu, datasets


@singleton
class MCPresentationController_datasetinfos(QObject):

    def __init__(self, qt_panel, mcBusinessLogic, mcData, mainWindow):

        super().__init__()
        print(type(self).__name__ + " initialized")

        self.bl     = mcBusinessLogic
        self.mcData = mcData
        self.panel  = qt_panel

        self.main = main.MCPresentationController_main(qt_panel, mcBusinessLogic, mcData, mainWindow)
        self.signals = signals.MCPresentationController_signals()
        self.menu = menu.MCPresentationController_menu(qt_panel, mcBusinessLogic, mcData, mainWindow)

        # self.view  = mcPresentationView
        # self.model = mcPresentationModel

    def makeConnections(self):
        p = self.panel

        print("inside makeConnections in " + type(self).__name__ )

