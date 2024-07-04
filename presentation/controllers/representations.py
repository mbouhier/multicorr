# from presentation.controllers.main      import MCPresentationController_main
# from presentation.controllers.spectrums import MCPresentationController_spectrums
import random
import threading
from functools import partial

import numpy as np
import qwt as Qwt
from PyQt5 import uic
from PyQt5.QtCore import QPointF
from PyQt5.QtCore import pyqtSignal, QObject
import plotpy
from plotpy.builder import make
from plotpy.items import RGBImageItem, ImageItem
from plotpy.interfaces import IImageItemType
from plotpy.items import LabelItem
from plotpy.plot import PlotDialog, PlotOptions#ImageDialog, CurveDialog
from plotpy.tools import SelectPointTool, FreeFormTool, RectangleTool
from PyQt5.QtGui import QFont, QColor, QBrush

from helpers import mc_logging
from helpers.data import singleton
from helpers.plots.customGuiQwtTools import CorrelationBoxTool, CorrelationInfoTool
from helpers.plots.plots import getItemsInPlotMatchingName
from presentation.controllers  import main, spectrums, signals


@singleton
class MCPresentationController_representations(QObject):

    signal_updateRepresentationDisplay     = pyqtSignal(str, str, bool)
    signal_updateRepresentationsFamilyList = pyqtSignal()
    signal_updateRepresentationsList       = pyqtSignal(bool)

    signal_updateLabelsOnCorrelationPlot = pyqtSignal()

    def __init__(self, qt_panel, mcBusinessLogic, mcData, mainWindow):
        #self.instance = "==================================================== Instance at %d" % self.__hash__()
        super().__init__()
        print(type(self).__name__ + " initialized (id:{})".format(id(self)))

        self.bl     = mcBusinessLogic
        self.mcData = mcData
        self.panel  = qt_panel
        self.mainWindow = mainWindow

        self.signals = signals.MCPresentationController_signals()

        self.main       = main.MCPresentationController_main(qt_panel, mcBusinessLogic, mcData, mainWindow)
        self.spectrums  = spectrums.MCPresentationController_spectrums(qt_panel, mcBusinessLogic, mcData, mainWindow)


        self.initRepresentationTab()


    def makeConnections(self):
        p = self.panel

        print("inside makeConnections in MCPresentationController_representations")
        self.signal_updateRepresentationDisplay.connect(self.updateRepresentationDisplay)
        self.signal_updateRepresentationsFamilyList.connect(self.updateRepresentationsFamilyList)
        self.signal_updateRepresentationsList.connect(self.updateRepresentationsList)
        self.signal_updateLabelsOnCorrelationPlot.connect(self.updateLabelsOnCorrelationPlot)

        # le activated est appeller lors d'une action utilisateur seulement
        p.combo_representations.activated.connect(self.updateRepresentationDisplay)

        p.combo_representations_family.currentIndexChanged.connect(
            partial(self.updateRepresentationsList, update_repr_display = True))

        #TODO: a mettre dans un plugin
        p.buttonChannelsImages.clicked.connect(self.createRepresentationsForSelectedChannels)




    def initRepresentationTab(self):

        print("Creating RepresentationTab")

        p = self.panel

        self.representationTab = tab = dict()

        # =======================================================================
        #                           Partie Gauche
        # =======================================================================

        # ================== Creation d'un imageDialog ==========================
        # TODO: virer les icones qui ne servent à rien (profil, impression etc...)

        imgDialog = PlotDialog(edit     = False,
                                toolbar  = True,
                                title = "Contrast test",
                                options  = PlotOptions(type = "image", show_contrast = False))

        imgDialog.setObjectName("representationImage")  # pour le retrouver plus tard

        # =======================================================================



        #========================================================================
        #                   Ajout d'un item image
        #========================================================================

        imagePlot = imgDialog.get_plot()

        # par defaut, pas d'interpolation
        imageItem = make.image(np.zeros((10, 10), 'float32'),
                               interpolation = 'nearest',
                               title = "Representation"
                               )

        imagePlot.add_item(imageItem)

        # =======================================================================



        # =========== ajout d'un item curve pour localisation de points =========

        imagePlot = imgDialog.get_plot()

        curve = make.curve([], [],
                           linestyle = "NoPen",
                           marker = "o",
                           markersize = self.main.marker_size,
                           markerfacecolor = "red",
                           markeredgecolor = "black",
                           title = "selected point(s)")

        imagePlot.add_item(curve)

        # =======================================================================



        #==============================================================================================================
        #                                        Ajout de tools
        #==============================================================================================================

        correlationBoxTool = imgDialog.manager.add_tool(CorrelationBoxTool,
                                                        title = "Correlation",
                                                        handle_final_shape_cb = self.correlationSelectionChanged_inRepresentation)


        selectTool = imgDialog.manager.add_tool(SelectPointTool,
                                                title = "Selection (point)",
                                                on_active_item = False,
                                                mode = "create",
                                                end_callback = self.pickerSelectionChanged_inRepresentation)

        selectTool.activate()

        # TODO creer une fonction finalshape ici!!!!! et gerer l'activation/desactivation des tools


        for tool in [FreeFormTool, RectangleTool]:

            imgDialog.manager.add_tool(tool,
                                       title = "Selection",
                                       handle_final_shape_cb = partial(self.formSelectionChanged_inRepresentation, plotInstance = "image")
                                      )

        # =======================================================================

        tab["curve_selected_points"] = curve
        tab["imageItem"]   = imageItem
        tab["imageWidget"] = imgDialog

        # =======================================================================
        #       Connexion des changements induits par zoom/deplacement avec
        #       avec une methode de mise a jour de l'affichage
        # =======================================================================

        # self.connect(imagePlot, SIG_PLOT_AXIS_CHANGED, self.representation_axes_changed)
        imagePlot.SIG_PLOT_AXIS_CHANGED.connect(self.representation_axes_changed)

        # Callback  color_map + lut_range
        self.attachLUTCallbackToRepresentationImage(imageItem)

        # =======================================================================
        #                           Partie Droite
        # =======================================================================

        # =======================================================================
        #               Creation d'un curveDialog pour les datas
        # =======================================================================
        curveDialog = PlotDialog(edit = False, toolbar = False, options=PlotOptions(type="curve"))

        curveDialog.setObjectName("spectrumExplorer")  # pour le retrouver plus tard

        tab["explorerWidget"] = curveDialog

        # =======================================================================
        #           Creation d'un imageDialog pour les correlations
        # =======================================================================
        imgDialog_corr = PlotDialog(edit     = False,
                                     toolbar  = True,
                                     options  = PlotOptions(type="image",show_contrast = False))
        imgDialog_corr.setObjectName("correlationImage")
        # =======================================================================

        # =======================================================================
        #                        Ajout d'un item image
        #========================================================================
        imagePlot = imgDialog_corr.get_plot()
        imageItem = make.image(np.zeros((10, 10), 'float32'), interpolation = 'nearest', title = "Correlation matrix")
        imagePlot.add_item(imageItem)

        #=========================================================================
        #                       Correlation info tool
        #=========================================================================
        self.corrMatrix = []

        correlationInfoTool = imgDialog_corr.manager.add_tool(CorrelationInfoTool,
                                                              mcData = self.bl.mcData,
                                                              correlation_matrix_cb = self.getLastCorrelationMatrix)

        correlationInfoTool.activate()

        tab["explorerWidget_correlation"] = imgDialog_corr
        tab["explorerWidget_correlationImageItem"] = imageItem
        #p.correlationLayout.addWidget(imagePlot, 0, 0)


        # =======================================================================
        #
        # =======================================================================


        # ==============suppression des widgets existants=======================
        for i in range(p.explorerLayout.count()):

            item = p.gridLayout.takeAt(i)

            try:
                item.widget().deleteLater()

            except AttributeError:
                pass

        # =======================================================================

        # ================== Ajout au Layout ====================================
        p.explorerLayout.addWidget(imgDialog, 0, 0)
        p.explorerLayout.addWidget(curveDialog, 0, 1)

        p.explorerLayout.addWidget(imgDialog_corr, 0, 2)
        imgDialog_corr.setVisible(False)

        self.main.save_widget_ref(imgDialog)
        self.main.save_widget_ref(curveDialog)
        self.main.save_widget_ref(imgDialog_corr)
        # =======================================================================



    def pickerSelectionChanged_inRepresentation(self, tool):
        """
        Methode appelee lorsque l'on clique sur l'image de representation avec l'outil
        selection de point
        """
        #print("inside pickerSelectionChanged_inRepresentation")

        p = self.panel

        ds_name = self.mcData.datasets.currentDatasetName

        if not ds_name: return

        ds = self.mcData.datasets.getDataset(ds_name)

        self.switchExplorerTypeInRepresentationTab("data")

        currentGroup = self.bl.groups.getCurrentGroup()

        #        print event.x()
        #        print event.y()
        #        #position ecran
        #        print event.globalX()
        #        print event.globalY()

        # ================= reference du widget PCA Image =======================

        imageDialog = p.findChild(PlotDialog, name = 'representationImage')

        imagePlot = self.getRepresentationImagePlot()

        curveDialog = p.findChild(PlotDialog, name = 'spectrumExplorer')


        imageDialog.manager.set_default_plot(imagePlot)

        # ==================On prend la ref du tool active=======================
        #        #tool = imageDialog.get_active_tool()
        #        #si c'est pas le selectPoinTool, on sort
        #        from guiqwt.tools import SelectPointTool
        #        if not isinstance(tool,SelectPointTool):
        #            print "not selectPoinTool"
        #            #return
        #        else:
        #            print "select pointTool!!!!!"
        # =======================================================================

        plotX, plotY = tool.get_coordinates()

        imageItem = self.getRepresentationImageItem()

        pixelX, pixelY = imageItem.get_closest_indexes(plotX, plotY)

        # ==================================================================
        # Convert (x,y) from axes coordinates to canvas coordinates system
        # for hit_test
        # ==================================================================

        imagePlot, ax, ay = imageItem.plot(), imageItem.xAxis(), imageItem.yAxis()

        point = QPointF(imagePlot.transform(ax, plotX), imagePlot.transform(ay, plotY))

        _, _, click_is_inside, _ = imageItem.hit_test(point)

        if click_is_inside:
            spectrumIndex = self.bl.coordinates.getSpectrumIndexFromImageCoordinate(pixelX, pixelY, ds_name)

        else:
            spectrumIndex = []

        # ==================================================================


        # on ajoute/retire ou affiche simplement le spectre selectionné au groupe en cour

        if currentGroup:

            # ======== on ajoute si absent, on supprime si present ==============
            add_or_remove = str(p.combo_selectionType.currentText())

            if add_or_remove == "add":
                self.bl.groups.addPointsToGroup(currentGroup, ds_name, spectrumIndex, ds["xys"][spectrumIndex])

            elif add_or_remove == "remove":
                self.bl.groups.removePointsFromGroup(currentGroup, ds_name, spectrumIndex, ds["xys"][spectrumIndex])

            else:
                pass

            self.signals.signal_groupsUpdated.emit()

        self.mcData.currentSpectrumIndex = spectrumIndex

        # on met a jour l'affichage de spectre en cours
        self.signals.signal_spectrumsToDisplayChanged.emit([])

        return spectrumIndex


    def getCorrelationImagePlot(self):
        tab = self.representationTab
        return tab["explorerWidget_correlation"].get_plot()
        #     p = self.panel
        #     return p.findChild(ImageDialog, name = 'correlationImage').get_plot()

    def getCorrelationImageItem(self):
        tab = self.representationTab
        return tab["explorerWidget_correlationImageItem"]

    def correlationSelectionChanged_inRepresentation(self, shape):
            t = threading.Thread(target = self.correlationSelectionChanged_inRepresentation_Thread,
                                 args   = (shape,))
            t.deamon = True
            t.start()

    def correlationSelectionChanged_inRepresentation_Thread(self, shape):
        #voir freeFormSelectionChanged_inCloud

        print("inside correlationSelectionChanged_inRepresentation_Thread")
        plot        = self.getCorrelationImagePlot()
        imageItem   = self.getCorrelationImageItem()
        imageDialog = self.getCorrelationImageItem()

        ds      = self.mcData.datasets.getDataset()
        ds_name = self.mcData.datasets.currentDatasetName

        if ds:

            self.switchExplorerTypeInRepresentationTab("correlation")

            shape.setTitle("correlationBox")

            indexes_inside_shape, overlaps, _ = self.bl.shapes.getIndexesInsideShape(ds_name,
                                                                                     shape.get_points(),
                                                                                     ds_name,
                                                                                     self.main.displayProgressBar)

            corrMatrix = np.corrcoef(ds["X"][np.sort(indexes_inside_shape), :], rowvar = False)

            self.correlation_last_matrix = corrMatrix

            imageItem.set_data(corrMatrix[:, :])

            nb_pt = len(indexes_inside_shape)
            ratio = 1.0 * nb_pt / len(ds["X"])

            plot.setTitle("Correlation on %d points (%.2f%% of dataset)" % (nb_pt, 100*ratio))

            plot.do_autoscale()
            plot.replot()

    def getLastCorrelationMatrix(self):
        return self.correlation_last_matrix


    def getRepresentationImagePlot(self):
        p = self.panel
        return p.findChild(PlotDialog, name = 'representationImage').get_plot()

    def getRepresentationImageItemList(self):
        p = self.panel
        p.findChild(PlotDialog, name = 'representationImage').itemlist

    def getRepresentationImageItem(self):

        plot = self.getRepresentationImagePlot()

        # retourne un dictionnaire avec comme clef le title
        imageItems = getItemsInPlotMatchingName(plot, "Representation")

        if imageItems: return list(imageItems.values())[0]
        else:          return None

    def getRepresentationGroupsCurveItems(self):

        plot = self.getRepresentationImagePlot()

        return getItemsInPlotMatchingName(plot, "group")


    def getCurrentRepresentation(self):
        """
        Convenient method to retrieve current displayed representation
        """
        p = self.panel

        ds_name = self.mcData.datasets.currentDatasetName

        repr_family = p.combo_representations_family.currentText()
        repr_name   = p.combo_representations.currentText()

        return self.bl.representations.getRepresentation(ds_name, repr_family, repr_name)


    def insertRepresentationInDatasetDict(self, family, repr_name, image, dataset = None, override = True, ds_name = None,
                                          display = False, gotoTab = False):
        """
        insert a dataset representation in ds["representations"] dict()

        ds["representations"][family_name] = dict()
        ds["representations"][family_name][repr_name]["image"] = array(imwidth,imheight)


        if display = True, change current selected representation
        if gotoTab = True, display representation Tab
        """
        self.bl.representations.insertRepresentationInDatasetDict(family,
                                                                  repr_name,
                                                                  image,
                                                                  dataset,
                                                                  override,
                                                                  ds_name)

        if (ds_name == self.mcData.datasets.currentDatasetName or ds_name == None) and display:
            self.signal_updateRepresentationsFamilyList.emit()
            self.signal_updateRepresentationDisplay.emit(family, repr_name, gotoTab)


    def removeRepresentationFamilyFromDatasetDict(self, family, update_display = True):
        """
        remove a dataset representation from ds["representations"] dict()
        """

        self.bl.representations.removeRepresentationFamilyFromDatasetDict(family)

        if update_display:
            self.main.signal_updateRepresentationsFamilyList.emit()



    def switchExplorerTypeInRepresentationTab(self, type):
        """type = data or correlation"""
        tab = self.representationTab

        c_widget = tab["explorerWidget_correlation"]
        d_widget = tab["explorerWidget"]

        #==suppression des eventuelles correlationBox precedentement affichées==
        plot = self.getRepresentationImagePlot()
        items = [item for item in plot.get_items() if "correlationBox" in item.title().text()]
        plot.del_items(items)
        #======================================================================

        if type == "data":
            c_widget.setVisible(False)
            d_widget.setVisible(True)

        elif type == "correlation":
            c_widget.setVisible(True)
            d_widget.setVisible(False)


    def attachLUTCallbackToRepresentationImage(self, imageItem):
        """
        Attach un callback LUT changed si image 1 canal
        """
        imageItem.plot().SIG_LUT_CHANGED.connect(self.imageLUTChanged_inRepresentation)


    def representation_axes_changed(self, plot):
        """
        Methode appelée des qu'un changement est fait aux axes du conteneur de l'image
        de representation, cad lors d'un deplacement ou zoom sur l'image
        """
        bottom_id = plot.get_axis_id("bottom")
        left_id   = plot.get_axis_id("left")

        # print "xlimits:",plot.get_axis_limits(bottom_id)
        # print "ylimits:", plot.get_axis_limits(left_id)
        # print "representation axes_changed!",
        # print plot.get_items()


    # @my_pyqtSlot()
    def updateRepresentationsFamilyList(self):

        print("inside updateRepresentationsFamilyList")

        p = self.panel

        ds_name = self.mcData.datasets.currentDatasetName
        ds = self.mcData.datasets.getDataset(ds_name)

        c = p.combo_representations_family
        c.clear()

        items = [name for name in list(ds["representations"].keys())]
        c.addItems(items)

        self.signal_updateRepresentationsList.emit(True)

    # @my_pyqtSlot(bool)
    def updateRepresentationsList(self, update_repr_display = True):

        print("inside updateRepresentationsList")

        p = self.panel

        ds_name = self.mcData.datasets.currentDatasetName
        ds      = self.mcData.datasets.getDataset(ds_name)

        family = str(p.combo_representations_family.currentText())

        # raz
        c = p.combo_representations
        c.clear()

        # remplissage si famille selectionné

        if family:
            items = [name for name in sorted(ds["representations"][family].keys())]

            c.addItems(items)

        # On affiche la representation selectionnée

        if update_repr_display:
            repr_name = str(p.combo_representations.currentText())

            self.signal_updateRepresentationDisplay.emit(family, repr_name, False)





    # @my_pyqtSlot(str,str,bool)
    def updateRepresentationDisplay(self, family = None, name = None, gotoTab = False):

        # TODO: reussir à afficher tels quel les images RGBA!
        mc_logging.debug("inside updateRepresentationDisplay")

        if not family or not name:
            p = self.panel
            family = str(p.combo_representations_family.currentText())
            name = str(p.combo_representations.currentText())


        mc_logging.debug("Representation update requested for {} of family {}".format(name, family))

        p = self.panel

        ds_name = self.mcData.datasets.currentDatasetName
        ds      = self.mcData.datasets.getDataset(ds_name)

        a_ratio = ds.get("aspect_ratio", None)  # image aspect_ratio

        c_f = p.combo_representations_family
        c_r = p.combo_representations

        # sinon on verifie qu'ils existe bien dans le dictionnaire
        try:
            assert (family in ds["representations"]), '"%s" not in representations dict()' % (family)
            assert (name in ds["representations"][family]), '"%s" not in "%s" representation family' % (name, family)

        except AssertionError:
            mc_logging.debug("family or name not in representations dict")
            return

        r_family = family
        r_name = name

        # on place les combo dans la configuration (family,name) demandée
        c_f.setCurrentIndex(c_f.findText(r_family))

        # on utilise pas updateRepresentationsList() car il y a un temps
        # de latence de mise a jour de la combo name faisant que findText
        # ne retourne pas la bonne valeur
        c_r.clear()

        items = [key for key in sorted(ds["representations"][r_family].keys())]

        c_r.addItems(items)

        c_r.setCurrentIndex(c_r.findText(r_name))

        # ====== on fait un autoscale si on change de family ou dataset =========

        # autoscale = False

        if hasattr(self, "_previousFamily") and hasattr(self, "_previousDataset"):

            if r_family == self._previousFamily and ds_name == self._previousDataset:
                autoscale = False

            else:
                autoscale = True

        else:
            autoscale = True

        self._previousFamily  = r_family
        self._previousDataset = ds_name
        # =====================================================================

        # ============ On recupere la ref du conteneur de l'image =============
        imagePlot = self.getRepresentationImagePlot()
        imageItem = self.getRepresentationImageItem()
        # =====================================================================

        rep  = self.bl.representations.getRepresentation(ds_name, r_family, r_name)
        data = self.bl.representations.getRepresentationImage(ds_name, r_family, r_name)

        print("data.shape:", data.shape)

        if len(data.shape) == 2:
            nb_channels = 1

        else:
            nb_channels = data.shape[2]

        # ======================================================================
        # Action differente dans le cas d'une image 1 ou 3 canaux
        # ======================================================================

        # TODO: Bug a cet endroit si on envoi une image RGB, à corriger

        # on supprime le imageItem precedent si le type (1 cannal ou RGB)
        # n'est plus bon

        print("before set_data")

        if nb_channels == 1:
            # ==================================================================
            # Si on a pas un conteneur 1 channel
            # ==================================================================
            if type(imageItem) != ImageItem:

                print("changing imageItem type")

                try:
                    imagePlot.del_item(imageItem)

                except Exception as e:
                    print("Can't delete imageItem")
                    print(e)

                imageItem = ImageItem()

                imagePlot.add_item(imageItem)

            # ==================================================================
            #
            # ==================================================================

            print("1 channel image")

            imageItem.set_interpolation('nearest')
            imageItem.setTitle("Representation")
            imageItem.set_data(data)

            self.attachLUTCallbackToRepresentationImage(imageItem)

        # ======================================================================
        # Si on a des datas 3 channel
        # ======================================================================

        if nb_channels == 3:
            # ==================================================================
            # Si on a pas un conteneur 3 channels
            # ==================================================================

            if type(imageItem) != RGBImageItem:

                print("changing imageItem type")

                try:
                    imagePlot.del_item(imageItem)

                except Exception as e:
                    print("Can't delete imageItem")
                    print(e)

                imageItem = RGBImageItem()

                imagePlot.add_item(imageItem)

            # ==================================================================
            #
            # ==================================================================

            print("3 channel image")

            downscale_factor = 1

            while True:

                try:
                    imageItem.set_data(data[::downscale_factor, ::downscale_factor, :])
                    break

                except MemoryError:
                    print("MemoryError while creating image item")
                    downscale_factor += 1
                    print("trying with downscale_factor:", downscale_factor)

            imageItem.setTitle("RepresentationRGB")

        print("after set_data")

        # ======================================================================
        # Mise a jour des x,y_datas
        # ======================================================================

        # concatenation des deux listes pour conparer tout les elements d'un coup
        old_xydatas = list(imageItem.get_xdata() + imageItem.get_ydata())

        if not np.all(old_xydatas == ds["x_range"].tolist() + ds["y_range"].tolist()):
            autoscale = True

        # contient la representation + d'eventuels images superposées
        items_with_xydatas_to_update = [item for item in imagePlot.get_items() if
                                        "group" in item.title().text() and isinstance(item, IImageItemType)]

        #print("items_with_xydatas_to_update:", items_with_xydatas_to_update)

        items_with_xydatas_to_update.append(imageItem)

        for item in items_with_xydatas_to_update:

            item.set_xdata(ds["x_range"][0], ds["x_range"][1])
            item.set_ydata(ds["y_range"][0], ds["y_range"][1])

            # sans set_data, est-ce-que les deux instructions suivantes mettent a jour l'affichage?
            item.update_bounds()
            item.update_border()

        # ==================Ajout des unitées===================================

        for axis_name in ["bottom", "left"]:
            axis_id = imagePlot.get_axis_id(axis_name)

            imagePlot.set_axis_unit(axis_id, ds["spatial_unit"])

        if autoscale: imagePlot.do_autoscale()

        if a_ratio:   imagePlot.set_aspect_ratio(a_ratio)

        # ======================================================================
        # on remet les paramètres de color_map et lut_range si enregistrés
        # ======================================================================

        if nb_channels == 1:

            if "color_map" in rep and rep["color_map"]:
                mc_logging.debug("rep[color_map]:")
                mc_logging.debug(rep["color_map"])
                try:
                    imageItem.set_color_map(rep["color_map"])
                except:
                    #s'il y a eu un probleme a la lecture, on reactualise l'enregistrement du lut
                    mc_logging.error("Can't set color_map, set to 'jet' by default")
                    imageItem.set_color_map("jet")
                    self.imageLUTChanged_inRepresentation()

            if "lut_range" in rep and len(rep["lut_range"]) == 2:
                mc_logging.debug("rep[lut_range]:")
                mc_logging.debug(rep["lut_range"])
                lut_range = rep["lut_range"]
            else:
                lut_range = imageItem.get_lut_range_full()

            try:
                imageItem.set_lut_range(lut_range)
            except:
                # s'il y a eu un probleme a la lecture, on reactualise l'enregistrement du lut
                mc_logging.error("Can't set lut_range")
                self.imageLUTChanged_inRepresentation()

        # ============on definit un titre=======================================

        title = Qwt.QwtText('%s - %s' % (r_family, r_name))

        title.setFont(QFont('DejaVu', 8, QFont.Light))

        imagePlot.setTitle(title)

        # ======================================================================
        imagePlot.replot()

        # ============ On se place sur l'onglet representation ==============
        if gotoTab: p.tabWidget.setCurrentIndex(self.main.getTabIndexByName("Representation"))


    def imageLUTChanged_inRepresentation(self):
        """
        Callback method called when lut range or color map changed in
        current representation. Values are recorded for further display
        """
        print(".", end = ' ')

        rep = self.getCurrentRepresentation()

        # imagePlot = self.gui.representations.getRepresentationImagePlot()
        imageItem = self.getRepresentationImageItem()

        # get current representation
        rep["lut_range"] = imageItem.get_lut_range()
        rep["color_map"] = imageItem.get_color_map_name()

        # print "type(rep['color_map'])",type(rep["color_map"])


    def formSelectionChanged_inRepresentation(self, shape, plotInstance = 'image'):
        t = threading.Thread(target = self.formSelectionChanged_inRepresentation_Thread,
                             args = (shape, plotInstance))
        t.deamon = True
        t.start()


    def formSelectionChanged_inRepresentation_Thread(self, shape, plotInstance = 'image'):
        """
        Methode appellée lors de la confirmation d'un groupe au lasso
        (appuis sur entrer aprés avoir commencé la forme)
        """
        print("inside formSelectionChanged_inRepresentation")

        # ==================recuperation des variables===========================
        p = self.panel

        ds_name = self.mcData.datasets.currentDatasetName
        ds      = self.mcData.datasets.getDataset(ds_name)

        currentGroup = self.bl.groups.getCurrentGroup()
        print("currentGroup:", currentGroup)

        plot = self.getRepresentationImagePlot()

        plot.del_item(shape)
        plot.replot()  # peux poser probleme?

        self.switchExplorerTypeInRepresentationTab("data")

        # =======================================================================
        #        Mise a jour de la selection si un groupe est selectionne
        # =======================================================================

        if currentGroup:

            # ======== on ajoute si absent, on supprime si present ==============
            add_or_remove = str(p.combo_selectionType.currentText())

            indexes_inside_shape, overlaps, _ = self.bl.shapes.getIndexesInsideShape(ds_name,
                                                                                     shape.get_points(),
                                                                                     ds_name,
                                                                                     self.main.displayProgressBar)

            # print "indexes_inside_shape:",indexes_inside_shape
            # print "shape.get_points():",shape.get_points()

            xys_of_points_inside_shape = [ds["xys"][point_idx] for point_idx in indexes_inside_shape]

            if add_or_remove == "add":
                self.bl.groups.addPointsToGroup(currentGroup, ds_name, indexes_inside_shape, xys_of_points_inside_shape)

            elif add_or_remove == "remove":
                self.bl.groups.removePointsFromGroup(currentGroup, ds_name, indexes_inside_shape, xys_of_points_inside_shape)

            else:
                return

            # ===========En surrimpression on met les point "selected"===========
            self.signals.signal_groupsUpdated.emit()
            # ===================================================================


    def updateGroupsDisplayDatas(self):
        """
        Cette methode met à jour l'affichage des selections sur la representation
        image du jdd et appel la mise a jours de l'affichage des groupes et
        du spectre en cours
        TODO: Changer le type d'affichage en fonction du nombre de points dans
        le groupe et/ou affiché a l'ecran en fonction de xy_range pour ne pas
        surcharger l'affichage
        """
        mc_logging.debug("---updateGroupsDisplayDatas_inRepresentation---")
        ds = self.mcData.datasets.getDataset()

        groups = ds["groups"]

        repr_imagePlot  = self.getRepresentationImagePlot()
        repr_curveItems = self.getRepresentationGroupsCurveItems()

      # =====================================================================
        #     On affiche en surrimpression sur Representation
        # =====================================================================
        for group_name, group in groups.items():

            # ==================================================================
            # Limitation de l'affichage en attendant subsampling par zoom
            # ==================================================================
            selected_idxs = group["indexes"]

            max_points_to_display = self.main.limits.max_points_on_curves

            if len(selected_idxs) > max_points_to_display:

                mc_logging.info("too many points to display (%d), limiting to %d (random selection)" % (len(selected_idxs), max_points_to_display))
                #selected_idxs = selected_idxs[::int(1.0 * len(selected_idxs) / max_points_to_display)]
                print("before random selection")
                selected_idxs = random.sample(selected_idxs, max_points_to_display)
                print("after random selection")

            selected_idxs = sorted(selected_idxs)

            curve_title = '"%s" group' % (group_name,)

            if curve_title in repr_curveItems:
                # ==========================================================
                #     Version points
                # ==========================================================
                curve = repr_curveItems[curve_title]

                if selected_idxs:
                    xs = ds["xys"][selected_idxs][:, 1]
                    ys = ds["xys"][selected_idxs][:, 0]

                else:
                    xs, ys = [], []

                curve.set_data(xs, ys)

            else:
                print("%s not in repr_curveItems!" % (curve_title))

        repr_imagePlot.replot()


    def updateLabelsOnCorrelationPlot(self):
        # ================== Ajout des labels si type(W) = str===============
        # Si type W est str, on ajoute des labels
        ds = self.mcData.datasets.getDataset()
        curvePlot  = self.getCorrelationImagePlot()
        labelBrush = QBrush(QColor(255, 255, 255, 160))
        if not ds:
            print("Can't update correlation labels, no dataset yet")
            return

        W = self.mcData.datasets.getDataset()["W"]

        #Suppression des eventuel labels precedent
        for item in curvePlot.get_items():
            if(isinstance(item, LabelItem)):
                #print(type(item),"is instance")
                curvePlot.del_item(item)
            else:
                pass
                #print(type(item),"isnotinstance")

        for i in range(len(W)):
            if (isinstance(W[i], str)):
                name_label_top  = make.label(W[i], (i, 0), (0, -20), "BL")
                name_label_left = make.label(W[i], (0, i), (-20, 20), "TR")

                name_label_top.bg_brush  = labelBrush
                name_label_left.bg_brush = labelBrush

                curvePlot.add_item(name_label_top)
                curvePlot.add_item(name_label_left)




    #TODO: a mettre dans un plugin
    def createRepresentationsForSelectedChannels(self, family_name = ""):

        print("inside createRepresentationsForSelectedChannels")

        ds = self.mcData.datasets.getDataset()

        W = ds["W"]

        display_limit_nb = 40  # arbitraire, a definir en fonction de la taille des images?

        # =====================================================================
        #              import GUI
        # =====================================================================
        d = uic.loadUi("assets//ui_files//multiple_choice_from_list.ui")
        d.setWindowTitle("Please select Channels to use")

        # =====================================================================
        #              On remplit la listBox avec les canaux disponibles
        # =====================================================================
        d.list_availableItems.addItems(list(map(str, W)))  # cas des W float, int ou str
        ok = d.exec_()

        # =====================================================================
        #               On recupere les donnees de la gui
        # =====================================================================
        if ok:
            requested_channels = [i.row() for i in d.list_availableItems.selectedIndexes()]
            channels_nb = len(requested_channels)

        else:
            print("no channel selected, abort")
            return

        if not family_name: family_name = "Sp. Slices"

        if channels_nb > display_limit_nb:
            print("Representation number requested too high (%d), limited to %d" % (
                len(requested_channels), display_limit_nb))

            return

        if channels_nb > 1:
            display, gotoTab = False, False

        else:
            display, gotoTab = True, True

        for i, ch_idx in enumerate(requested_channels):

            channel = W[ch_idx]
            print("type(channel):", type(channel))

            if np.issubdtype(type(channel), str):
                repr_name = channel

            else:
                repr_name = "Channel %d" % (ch_idx,)

            if i == len(requested_channels) - 1:
                display, gotoTab = True, True

            image = self.bl.representations.getImageFromValues(ds["X"][:, ch_idx])

            print("tttt", display, gotoTab)

            self.insertRepresentationInDatasetDict(family_name,
                                                   repr_name,
                                                   image,
                                                   display = display,
                                                   gotoTab = gotoTab)


    def getExplorerWidgetRef(self):
        return self.representationTab["explorerWidget"]

    def updateDisplayedSpectrums(self, spectrum_indexes = []):
        #print("inside updateDisplayedSpectrums  in representations")

        widget_ref = self.getExplorerWidgetRef()
        ds_name    = self.mcData.datasets.currentDatasetName

        self.spectrums.updateDisplayedSpectrumsInWidgetByDsName(widget_ref,
                                                                ds_name,
                                                                spectrum_indexes)#,
                                                                #autoselect_indexes = True)



    def createRepresentationsForVectorsInSelectedVectorsList(self, projection_name = None):
        """
        This method create and insert into representation list, all representation
        of proj["vectors_names_selected"] wich contain all base_vector to diplay
        We should create representation for all base Vector but it should result in
        poor performance.
        This method is called each time proj["vectors_names_selected"] change
        """

        ds = self.mcData.datasets.getDataset()

        p = self.panel

        if projection_name: current_projection_name = projection_name
        else:               current_projection_name = str(p.combo_representations_family.currentText())

        mc_logging.debug("inside createRepresentationsForVectorsInSelectedVectorsList")

        if current_projection_name not in ds["projections"]: return

        proj = ds["projections"][current_projection_name]

        mc_logging.debug("creating representations for:")

        last_vector_in_list = len(proj["vectors_names_selected"]) - 1

        for i, selected_vector in enumerate(proj["vectors_names_selected"]):

            repr_name = selected_vector

            vector_idx = proj["vectors_names"].index(selected_vector)

            mc_logging.debug("-%s" % (selected_vector,))

            image = self.bl.representations.getImageFromValues(proj["values"][:, vector_idx])

            if i == last_vector_in_list:
                update_display = True

            else:
                update_display = False

            self.insertRepresentationInDatasetDict(current_projection_name, repr_name, image, display = update_display)
