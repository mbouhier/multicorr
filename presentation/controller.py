from PyQt5 import uic
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QProgressBar

from presentation.controllers.datasets        import MCPresentationController_datasets
from presentation.controllers.filters         import MCPresentationController_filters
from presentation.controllers.groups          import MCPresentationController_groups
from presentation.controllers.io              import MCPresentationController_io
from presentation.controllers.main            import MCPresentationController_main
from presentation.controllers.menu            import MCPresentationController_menu
from presentation.controllers.projections     import MCPresentationController_projections
from presentation.controllers.representations import MCPresentationController_representations
from presentation.controllers.signals         import MCPresentationController_signals
from presentation.controllers.spectrums       import MCPresentationController_spectrums
from presentation.controllers.multidatasets   import MCPresentationController_multidatasets
from presentation.controllers.datasetinfos    import MCPresentationController_datasetinfos



class MCPresentationController(QObject):


    def __init__(self, mcBusinessLogic, mcData, mainWindow):
        super().__init__()
        print(type(self).__name__ + " initialized")

        self.panel = self._init_panel(mainWindow)
        self.mcData = mcData

        self.signals = MCPresentationController_signals()


        self.representations = MCPresentationController_representations(self.panel, mcBusinessLogic, mcData, mainWindow)
        self.io              = MCPresentationController_io(self.panel, mcBusinessLogic, mcData, mainWindow)
        self.main            = MCPresentationController_main(self.panel, mcBusinessLogic, mcData, mainWindow)
        self.datasets        = MCPresentationController_datasets(self.panel, mcBusinessLogic, mcData, mainWindow)
        self.projections     = MCPresentationController_projections(self.panel, mcBusinessLogic, mcData, mainWindow)
        self.groups          = MCPresentationController_groups(self.panel, mcBusinessLogic, mcData, mainWindow)
        self.filters         = MCPresentationController_filters(self.panel, mcBusinessLogic, mcData, mainWindow)
        self.spectrums       = MCPresentationController_spectrums(self.panel, mcBusinessLogic, mcData, mainWindow)
        self.multidatasets   = MCPresentationController_multidatasets(self.panel, mcBusinessLogic, mcData, mainWindow)
        self.datasetinfos    = MCPresentationController_datasetinfos(self.panel, mcBusinessLogic, mcData, mainWindow)
        # self.shapes          = MCPresentationController_shapes(mcBusinessLogic, mcPresentationView)
        # self.coordinates     = MCPresentationController_coordinates(mcBusinessLogic, mcPresentationView)
        self.menu            = MCPresentationController_menu(self.panel, mcBusinessLogic, mcData, mainWindow)

        self._controlers =  [self.representations,
                             self.io,
                             self.main,
                             self.menu,
                             self.datasets,
                             self.projections,
                             self.groups,
                             self.spectrums,
                             self.filters,
                             self.multidatasets,
                             self.datasetinfos]

        self._makeConnections()


    def _init_panel(self, mainWindow):

        p = uic.loadUi("assets//ui_files//multicorr_main.ui")

        #======================================
        #Ajout de status et progressbar
        #======================================
        sb = p.statusBar()

        pb = QProgressBar()
        pb.setMaximumHeight(20)
        pb.setRange(0, 100)
        pb.setObjectName("mainProgressBar")


        sb.insertPermanentWidget(0, pb)
        sb.insertPermanentWidget(1, pb)

        #self.pb = pb
        #======================================

        mainWindow.setCentralWidget(p)

        return p

    def _makeConnections(self):

        for controller in self._controlers:
            controller.makeConnections()

        #===============================================================================================================
        #                                               Interconnections
        #                              TODO, faire un systeme d'abonnement à des evenements type
        #===============================================================================================================

        for callback in (self.projections.updateGroupsDisplayDatas,
                         self.representations.updateGroupsDisplayDatas):

            self.signals.signal_groupsUpdated.connect(callback)


        for callback in (self.projections.updateDisplayedSpectrums,
                         self.representations.updateDisplayedSpectrums):

            self.signals.signal_spectrumsToDisplayChanged.connect(callback)


