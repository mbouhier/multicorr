import time
from collections import OrderedDict
from collections import namedtuple

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt

from helpers import mc_logging
from helpers.data import singleton
from presentation.controllers import signals


@singleton
class MCPresentationController_main(QObject):


    signal_updateLinkedDatasetsList_inMultiDatasetExplorer = pyqtSignal()


    signal_updateInfosTab = pyqtSignal()

    signal_updateRepresentationsDisplay_inMultiDatasetExplorer = pyqtSignal(bool)


    signal_updateProgress = pyqtSignal(float)
    signal_displayCoeffsHistogram = pyqtSignal(str)

    signal_updatePlots_inMultiDatasetExplorer = pyqtSignal()
    signal_projectLoadingDone = pyqtSignal()


    marker_size = 6

    # Minimal delay to refresh action on screen in ms
    last_update_time = time.time()

    Limits = namedtuple("Limits", ["max_points_on_curves", "min_refresh_delay", "max_curves_on_plot"])

    limits = Limits(max_points_on_curves = 5000,
                    min_refresh_delay    = 100,
                    max_curves_on_plot   = 50)

    # ==============================================================================
    # Keep references of widgets to avoid random error:
    # c / c + + object of type QwtPlotCanvas has been deleted
    # ==============================================================================
    widgets_refs = []

    graph_refs_counter = 0

    def __init__(self, qt_panel, mcBusinessLogic, mcData, mainWindow):
        self.instance = " Instance at %d" % self.__hash__()
        super().__init__()
        print(type(self).__name__ + " initialized" + self.instance)
        self.bl     = mcBusinessLogic
        self.mcData = mcData
        self.panel  = qt_panel
        self.mainWindow = mainWindow

        self.signals = signals.MCPresentationController_signals()

        # self.view  = mcPresentationView
        # self.model = mcPresentationModel

    def makeConnections(self):
        p = self.panel

        self.signal_updateProgress.connect(self._updateProgressBar)

        p.tabWidget.currentChanged.connect(self.currentTabChanged)




    def displayProgressBar(self, progress):

        if(progress != -1):
            if (time.time() - self.last_update_time) > self.limits.min_refresh_delay / 1000.:
                self.signal_updateProgress.emit(progress)
                self.last_update_time = time.time()
        else:
            self.resetProgressBar()

    def getCurrentTabIndex(self):
        p = self.panel
        return p.tabWidget.currentIndex()

    def getTabIndexByName(self, name):
        p = self.panel
        for i in range(p.tabWidget.count()):
            if p.tabWidget.tabText(i) == name:
                return i
        return -1

    def resetProgressBar(self):
        self.signal_updateProgress.emit(-1)

    # @my_pyqtSlot(float)
    def _updateProgressBar(self, i):
        """
        RAZ bar si i<0
        set pogressbar value to i if 100>i>0
        """
        pb = self.panel.findChild(QProgressBar, "mainProgressBar")

        if i >= 0:
            pb.setValue(int(i))
        else:
            pb.reset()

    def getColorFromColorPickerDialog(self, buttonHandler = None):

        color = QtWidgets.QColorDialog.getColor()

        if color.isValid():

            if buttonHandler:
                buttonHandler.setStyleSheet("QWidget { background-color: %s}" % color.name())

            self._color_picker_value = color

        else:

            delattr(self, "_color_picker_value")

            return None

        return color

    def setWidgetBackgroundColor(self, widget, color):
        widget.setStyleSheet("QWidget { background-color: %s}" % color.name())

    def setWidgetsValuesFromDict(self, panel, params):

        """
        outil permettant de remplir les champ dans l'ui Qt pour des Qline edit
        setText() ou spinbox setValue, TODO implementer d'autre type de widget, slider etc..
        """

        p = panel

        print("inside setWidgetsValuesFromDict")

        for ui_id, value in params.items():

            ui_object = getattr(p, ui_id, None)

            if ui_object is not None:

                # ui_object.setUpdatesEnabled(False)

                if isinstance(ui_object, QtWidgets.QLineEdit):
                    ui_object.setText(str(value))

                elif isinstance(ui_object, QtWidgets.QLabel):
                    ui_object.setText(str(value))

                elif isinstance(ui_object, QtWidgets.QSpinBox):
                    ui_object.setValue(int(value))

                elif isinstance(ui_object, QtWidgets.QComboBox):

                    index = ui_object.findText(str(value), QtCore.Qt.MatchFixedString)

                    if index >= 0: ui_object.setCurrentIndex(index)

                elif isinstance(ui_object, QtWidgets.QCheckBox):
                    ui_object.setChecked(value)

                elif isinstance(ui_object, QtWidgets.QSlider):
                    ui_object.setValue(int(value))

                else:
                    print(("Error NotImplemented widget filling method for", ui_id))
                    print(ui_object)
                    continue


            else:
                print(("Error, widget '%s' not found" % (ui_id)))
                continue

        print("setWidgetsValuesFromDict done")

    def restoreGuiState(self):
        """
        restore previous GUI state when currentDataset change
        TODO: il y a une latence entre le changement de dataset et l'affichage de l'etat precedent
        """

        p = self.panel

        ds = self.mcData.datasets.getDataset()

        if not ds: return 0

        previous_state = ds.get("gui_state", dict())

        self.setWidgetsValuesFromDict(p, previous_state)

        # if previous_state:
        #     mc_logging.debug("previous gui state restored")
        # else:
        #     mc_logging.debug("previous gui state unavailable")

    def saveGuiState(self):
        """
        record GUI state for further restore when currentDataset change
        """

        p = self.panel

        ds = self.mcData.datasets.getDataset()

        # Si il n'y a pas encore de currentDataset
        if not ds: return 0

        # ======================================================================
        # Principal
        # ======================================================================
        pgs = OrderedDict()  # previous_gui_state

        # Todo: iterer sur tout les elements de la Gui de maniere automatique? sinon, les etats des plugins ne seront pas pris en compte
        pgs["combo_representations_family"] = p.combo_representations_family.currentText()
        pgs["combo_representations"]        = p.combo_representations.currentText()
        pgs["combo_currentSelectionGroup"]  = p.combo_currentSelectionGroup.currentText()
        pgs["comboBox_vectorOnX"]           = p.comboBox_vectorOnX.currentText()
        pgs["comboBox_vectorOnY"]           = p.comboBox_vectorOnY.currentText()
        pgs["checkBox_normalizeDatas"]      = p.checkBox_normalizeDatas.isChecked()
        pgs["combo_normalisation_type"]     = p.combo_normalisation_type.currentText()
        pgs["combo_metadatas"]              = p.combo_metadatas.currentText()

        # ======================================================================
        # MultidatasetExplorer
        # ======================================================================
        # pgs["show_overlap"] = p.over
        # pgs["slider_refsAlpha"] = p.slider_refsAlpha.value()
        # pgs["slider_overlapThreshold"] = p.slider_overlapThreshold.value()
        # pgs["checkBox_autoSumDatas"] = p.checkBox_autoSumDatas.isChecked()
        # pgs["combo_referenceDataset"] = p.combo_referenceDataset.currentText()
        # pgs["comboBox_datasets"] = p.comboBox_datasets.currentText() #sinon, boucle infini
        # pgs["list_available_datasets"] = p.list_available_datasets.selected_items

        ds["gui_state"] = pgs

        mc_logging.debug("gui state recorded for '%s'" % (self.mcData.datasets.currentDatasetName))

    def save_widget_ref(self, widget):
        # =========================================================================
        # pour eviter l'erreur:
        # wrapped c/c++ object of type QwtPlotCanvas has been deleted
        # =========================================================================
        self.widgets_refs.append(widget)
        #self.graph_refs_counter += 1

    def currentTabChanged(self, tabIndex):
        """
        Methode appellée quand on change de vue dans l'interface graphique
        """
        mc_logging.debug("currentTab changed: %s" % (tabIndex))

        if tabIndex == self.getTabIndexByName("MultiViewer"):
            self.signal_updatePlots_inMultiDatasetExplorer.emit()