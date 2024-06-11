import numpy as np
import qwt as Qwt
from PyQt5.QtCore import QObject
from plotpy.builder import make

from PyQt5 import QtGui
from PyQt5.QtGui import QFont, QColor, QBrush

from helpers.data import singleton
from helpers.plots import plots
from presentation.controllers import main, signals, menu


@singleton
class MCPresentationController_multidatasets(QObject):

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

        print("inside makeConnections in MCPresentationController_multidatasets")