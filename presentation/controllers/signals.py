from PyQt5.QtCore import pyqtSignal, QObject


from helpers.data import singleton


@singleton
class MCPresentationController_signals(QObject):

    #==============================================
    # Signaux relatifs aux changements generaux
    #==============================================
    signal_groupsUpdated = pyqtSignal()
    signal_spectrumsToDisplayChanged = pyqtSignal(list)

    #==============================================
    # Signaux relatifs au menu
    #==============================================


    def __init__(self):
        super().__init__()
        print(type(self).__name__ + " initialized")
