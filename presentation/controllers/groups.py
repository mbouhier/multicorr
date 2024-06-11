import copy
from functools import partial

import numpy as np
from PyQt5 import QtGui, QtWidgets
from PyQt5 import uic
from PyQt5.QtCore import pyqtSignal, QObject
from plotpy.builder import make
from plotpy.plot import PlotDialog,PlotOptions

from helpers import mc_logging
from helpers.data import singleton
from helpers.dialogs import InputDialogWithColorChoice
from presentation.controllers import main, representations, spectrums, projections, signals


@singleton
class MCPresentationController_groups(QObject):


    signal_removeGroupFromDict = pyqtSignal(str, str, str, bool)
    signal_addGroupToDict = pyqtSignal(str, str, list)
    signal_updateGroupsDisplayHolders = pyqtSignal()
    signal_updateCurrentSelectionGroup = pyqtSignal(str)
    signal_updateGroupsList = pyqtSignal()

    def __init__(self, qt_panel, mcBusinessLogic, mcData, mainWindow):
        super().__init__()
        print(type(self).__name__ + " initialized")

        self.bl     = mcBusinessLogic
        self.mcData = mcData
        self.panel  = qt_panel
        self.mainWindow = mainWindow


        self.main            = main.MCPresentationController_main(qt_panel, mcBusinessLogic, mcData, mainWindow)
        self.representations = representations.MCPresentationController_representations(qt_panel, mcBusinessLogic, mcData, mainWindow)
        self.spectrums       = spectrums.MCPresentationController_spectrums(qt_panel, mcBusinessLogic, mcData, mainWindow)
        self.projections     = projections.MCPresentationController_projections(qt_panel, mcBusinessLogic, mcData, mainWindow)

        self.signals = signals.MCPresentationController_signals()


    def makeConnections(self):
        print("inside makeConnections in MCPresentationController_groups")
        p = self.panel


        #TODO connecter GroupsUpdated a la mise a jour de la liste des groups?
        #self.signal_groupsUpdated.connect(self.updateGroupsDisplayDatas)

        self.signal_removeGroupFromDict.connect(self.removeGroupFromDict)
        self.signal_addGroupToDict.connect(self.addGroupToDict)
        self.signal_updateGroupsDisplayHolders.connect(self.updateGroupsDisplayHolders_in_Representation_and_Projection)
        self.signal_updateCurrentSelectionGroup.connect(self.updateCurrentSelectionGroup)
        self.signal_updateGroupsList.connect(self.updateGroupsList)

        self.makeConnections_menuItems()


    def makeConnections_menuItems(self):

        p = self.panel

        p.button_addSelectionGroup.clicked.connect(self.addSelectionGroup)
        p.button_editSelectionGroup.clicked.connect(self.editSelectionGroup)
        p.button_delSelectionGroup.clicked.connect(self.delSelectionGroup)
        p.combo_currentSelectionGroup.currentIndexChanged.connect(self.changeCurrentSelectionGroup)
        p.button_hideGroups.clicked.connect(self.updateGroupsVisibilityInRepresentationAndProjection)
        p.button_importGroup.clicked.connect(self.importGroup)


    def updateGroupsVisibilityInRepresentationAndProjection(self):
        # =========================================================================
        # Desactivation de l'affichage si demandé dans la GUI
        # =========================================================================
        p = self.panel

        projTab = self.projections.projectionTab
        reprTab = self.representations.representationTab

        for tab in (projTab, reprTab):
            if tab == projTab:
                plot = self.projections.get2DProjectionCurvePlot()
            elif tab == reprTab:
                plot = self.representations.getRepresentationImagePlot()

        hide = p.button_hideGroups.isChecked()

        selected_groups = [item.title().text() for item in plot.get_items() if
                           "group" in item.title().text() and item.isVisible()]

        if hide: self._previousSelectedGroupsInShowMode = selected_groups

        previousSelectedGroupsInShowMode = getattr(self, "_previousSelectedGroupsInShowMode", [])

        groups_items = [item for item in plot.get_items() if "group" in item.title().text()]

        for item in groups_items:
            # on laisse selectionné les items qui ont étés cliqués pendant qu'on était en mode hide
            # sinon, on reactive ceux qui été selectionnés en mode show
            group_name = item.title().text()

            if hide:
                item.setVisible(False)
            elif group_name in previousSelectedGroupsInShowMode:
                item.setVisible(True)

        #correction d'un bug, l'affichage des groupes selectionnés ou non n'est pas mis à jour dans la liste sinon
        self.panel.findChild(PlotDialog, name = 'representationImage').panels["itemlist"].listwidget.itemSelectionChanged.emit()
        # =========================================================================

        plot.replot()


    def changeCurrentSelectionGroup(self):

        p = self.panel

        name = p.combo_currentSelectionGroup.currentText()

        self.bl.groups.setCurrentGroup(name)

        print(('selection Group is now "%s"' % (name)))

        # mise a jour du spectre affiché
        self.signals.signal_spectrumsToDisplayChanged.emit([])

        # on met à jour de l'affichage des groupes
        self.signals.signal_groupsUpdated.emit()


    def addSelectionGroup(self):
        """
        Methode appelée lorsque l'on clique sur "Ajouter un groupe"
        """

        print("inside addSelectionGroupClicked")

        ds = self.mcData.datasets.getDataset()

        groups = ds["groups"]

        p = self.panel


        # ============ Demande le group name a l'utilisateur ====================

        group_name = "Group%d" % (len(groups) + 1,)

        default_color = self.bl.getNextColor()

        dialog = InputDialogWithColorChoice(p)

        new_group_name, color, ok = dialog.getTextAndColor("Group Name input...",
                                                           "Enter a unique group name:",
                                                           group_name,
                                                           default_color)

        if ok:
            # =====On cree une entree dans le dictionnaire des selections=======
            self.addGroupToDict(new_group_name, color = color)

        else:
            return

    def editSelectionGroup(self):
        # 16-09-15: l'ordre des groupes changent avec le rename, a modifier si vraiment nescessaire

        print("inside editSelectionGroup")

        p = self.panel

        ds_name = self.mcData.datasets.currentDatasetName

        ds = self.bl.io.getDataset()

        groups = ds["groups"]

        old_group_name = p.combo_currentSelectionGroup.currentText()

        if not old_group_name:
            print("No group selected")
            return

        old_group_color = self.bl.groups.getGroupColor(ds_name, old_group_name)

        dialog = InputDialogWithColorChoice(p)

        new_group_name, color, ok = dialog.getTextAndColor("Group Name input...",
                                                           "Edit current group name:",
                                                           old_group_name,
                                                           old_group_color)

        if ok:

            print(('Group_name change from "%s" to "%s"' % (old_group_name, new_group_name)))

            # print groups.keys()
            # print "here",groups[str(old_group_name)]


            # on enregistre le groupe avant de le supprimer du dictionnaire
            tmp_group = copy.deepcopy(groups[str(old_group_name)])


            self.removeGroupFromDict(old_group_name)
            # cet appel creer l'entrée "vide" dans le dict + les curves necessaires à l'affichage
            self.addGroupToDict(new_group_name, color = color)

            # cette ligne remplie avec les valeurs du groupe initial
            ds["groups"][str(new_group_name)] = tmp_group

            # mise a jour de l'affichage nescessaire apres cette mise a jour "manuelle"
            self.signals.signal_groupsUpdated.emit()

        else:
            return

    def delSelectionGroup(self):
        # Pour les events et qmessagebox, voir
        # http://zetcode.com/gui/pyqt4/firstprograms/

        print("inside delSelectionGroup")

        p = self.panel

        s = p.combo_currentSelectionGroup

        group_name = str(s.currentText())

        # ============== Confirmation de suppression ============================

        reply = QtWidgets.QMessageBox.question(self.mainWindow, 'Confirmation',
                                               'Are you sure you want to delete the group "%s"?' % (group_name,),
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                               QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.Yes:
            # self.removeGroupFromDict(group_name)
            self.signal_removeGroupFromDict.emit(group_name, "", "", True)
        else:
            return

            # =======================================================================


    def addGroupToDict(self, name, family = '', indexes = [], dataset_name = '', color = None, updateDisplay = True):

        r = self.bl.groups.addGroupToDict(name,
                                          family = family,
                                          indexes = indexes,
                                          dataset_name = dataset_name,
                                          color = color)

        # ========================================================================================================
        #  tant qu'on aura pas annulé, demandé l'ecrasement ou entré un nom unique
        # ========================================================================================================
        while r == self.bl.groups.NameAlreadyExists:

            if family:
                f = 'in family "%s"' % (family,)
            else:
                f = ''

            s = '"%s" group already exist %s, change name or click OK to override' % (name, f)

            print(s)

            new_name, ok = QtWidgets.QInputDialog.getText(self.mainWindow,
                                                          "Group creation information",
                                                          s,
                                                          QtWidgets.QLineEdit.Normal,
                                                          name)

            new_name = str(new_name)

            if ok:

                if new_name == name:
                    print(('Overriding "%s"' % (name)))

                    # On garde la precedente couleur
                    # group_color = groups[name]["color"]

                    name = new_name

                    self.bl.groups.addGroupToDict(new_name,
                                                  family = family,
                                                  indexes = indexes,
                                                  dataset_name = dataset_name,
                                                  color = color,
                                                  override = True)
                    break

                else:
                    print("new_name different from name, checking if already exist")
                    print(new_name)

                    r = self.bl.groups.addGroupToDict(new_name,
                                                      family = family,
                                                      indexes = indexes,
                                                      dataset_name = dataset_name,
                                                      color = color,
                                                      override = False)
                name = new_name

            else:
                print("Group creation aborted")
                return

        # ==================================================================
        #       Mise a jour affichage
        # ==================================================================
        if updateDisplay:
            self.signal_updateCurrentSelectionGroup.emit(name)
            # 16-09-15: ne devait etre appelle que lors du changement de ds
            # self.updateGroupsList()
            self.signal_updateGroupsList.emit()
            self.signal_updateGroupsDisplayHolders.emit()
            self.signals.signal_groupsUpdated.emit()


            # TODO a implementer pour une mise ajour auto a l'appel de updateGroupsDatas
            # self._groupsDisplayHoldersHasBeenUpdated = False
            # self.updateGroupsDisplayDatas() aciver pour mettre a jour lors de la creation d'un groupe par les filtres??

            # TODO: faire pareil pour ds[groups"]?
            # self.selections = selections

    def removeGroupFromDict(self, name = '', dataset_name = '', family = '', updateDisplay = True):

        self.bl.groups.removeGroupFromDict(name = name,
                                           dataset_name = dataset_name,
                                           family = family)

        # =======================================================================
        #                      Suppression des curves
        # =======================================================================
        if not dataset_name: dataset_name = self.mcData.datasets.currentDatasetName

        curve_name = "curve_%s_%s_group" % (dataset_name, name)

        # ================= Sur le plot de cloudstab ============================
        # on supprime la Reference
        mc_logging.debug("removing '%s' from projectionTab" % (curve_name,))
        self.projections.projectionTab = {key: value for key, value in
                                          list(self.projections.projectionTab.items()) if
                                          key != curve_name}

        # =======================================================================
        # ===================  Sur le plot PCImage ==============================
        # on supprime la Reference
        #TODO supprimer la dependance
        mc_logging.debug("removing '%s' from representationTab" % (curve_name,))

        self.representations.representationTab = {key: value for key, value in
                                                  list(self.representations.representationTab.items())
                                                  if
                                                  key != curve_name}

        # =======================================================================

        if updateDisplay:
            # Mise a  jour de l'affichage des groupes
            self.signal_updateGroupsList.emit()
            self.signal_updateGroupsDisplayHolders.emit()


    # @my_pyqtSlot()
    def updateGroupsDisplayHolders_in_Representation_and_Projection(self):
        """
        mise a jour (dans projectionTab et dans representationTab) des groupes
        de selection en fonction du dataset selectionné
        Deselectionne l'attribut "visible" si demandé dans la gui
        """

        mc_logging.debug("---inside updateGroupsDisplayHolders---")

        ds_name = self.mcData.datasets.currentDatasetName

        ds = self.mcData.datasets.getDataset(ds_name)

        groups = ds["groups"]

        projTab = self.projections.projectionTab
        reprTab = self.representations.representationTab

        for tab in (projTab, reprTab):

            if tab == projTab:    plot = self.projections.get2DProjectionCurvePlot()
            elif tab == reprTab:  plot = self.representations.getRepresentationImagePlot()

            # ==================================================================
            #         if dataset has changed, reset all containers
            # ==================================================================

            if ds_name != tab.get("previous_dsname", ds_name):
                resetAllGroupsHolders = True

            else:
                resetAllGroupsHolders = False

            tab["previous_dsname"] = ds_name

            # ==================================================================


            # ==================================================================
            #         Conteneurs
            # ==================================================================
            old_group_items = [item for item in plot.get_items() if "group" in item.title().text()]

            new_group_items = []

            old_group_items_to_keep = []

            # on affiche tout les groupes du dataset en cour

            for group_name, group in groups.items():

                # ==============================================================
                # Check if already exists
                # ==============================================================

                item_already_exist = False

                for item in old_group_items:

                    if (group_name in item.title().text()) and not resetAllGroupsHolders:
                        item_already_exist = True

                        old_group_items_to_keep.append(item)

                # ==============================================================
                # Create holder if not
                # ==============================================================

                if not item_already_exist:

                    # mc_logging.debug("curve_%s_%s_group not in tab yet" % (ds_name, group_name))

                    group_color = self.bl.groups.getGroupColor(ds_name, group_name)

                    curve_repr, curve_proj = self.createGroupHolderForPlot(ds_name, group_name, group_color)

                    if tab == reprTab:
                        curve = curve_repr

                    else:
                        curve = curve_proj

                    # on garde la Reference
                    #                    tab[curve_name] = curve
                    #                    self.gui.projections.projectionTab[curve_name] = curve_proj  # on garde la Reference
                    #                    self.gui.representations.representationTab[curve_name] = curve_repr  # on garde la Reference

                    new_group_items.append(curve)

            # ======================================================================
            # On supprime toutes les curves/images des groupes qui ne sont plus
            # presents dans le dictionnaire des groupes
            # ======================================================================
            old_group_items_to_del = [item for item in old_group_items if item not in old_group_items_to_keep]

            for item in old_group_items_to_del:
                plot.del_item(item)

            for item in new_group_items:
                plot.add_item(item)

            plot.replot()

    def createGroupHolderForPlot(self, ds_name, group_name, group_color):
        """
        Creation d'un Item curve ou image pour contenir les groupes de points
        On enregistre les references vers les curves créées dans refs_dictionary
        """

        # =======================================================================
        #                      Creation des curves
        # =======================================================================
        # mc_logging.debug("inside createGroupCurve")

        # ================= Sur le plot de cloudstab ============================
        # curve_name = "curve_%s_%s_group" % (ds_name, group_name)
        # plot = self.gui.projections.get2DProjectionCurvePlot()
        curve_proj = make.curve([], [],
                                color = "red",
                                linestyle = "NoPen",
                                marker = "o",
                                markersize = self.main.marker_size,
                                markerfacecolor = group_color.name(),
                                markeredgecolor = "black",
                                title = '"%s" group' % (group_name,))  # self.getCurrentSelectionGroup(),))
        # =======================================================================

        # ===================  Sur le plot PCImage ==============================
        # curve_name = "curve_%s_%s_group" % (ds_name, group_name)
        # plot = self.gui.representations.getRepresentationImagePlot()
        curve_repr = make.curve([], [],
                                color = "red",
                                linestyle = "NoPen",
                                marker = "o",
                                markersize = self.main.marker_size,
                                markerfacecolor = group_color.name(),
                                markeredgecolor = "black",
                                title = '"%s" group' % (group_name,))  # self.getCurrentSelectionGroup(),))

        # ======================================================================
        return curve_repr, curve_proj

    ##@my_pyqtSlot(str)
    def updateCurrentSelectionGroup(self, group_name):
        """
        Ajoute le groupe "name" dans le combo des groupes du dataset courant
        et le selectionne
        """
        mc_logging.debug("inside updateCurrentSelectionGroup")

        ds_name = self.mcData.datasets.currentDatasetName

        ds = self.mcData.datasets.getDataset()

        groups = ds["groups"]

        s = self.panel.combo_currentSelectionGroup

        if group_name in groups:
            group_color = self.bl.groups.getGroupColor(ds_name, group_name)

        else:
            mc_logging.debug("%s not in groups!" % (group_name,))
            return

        icon = QtGui.QPixmap(40, 40)
        icon.fill(group_color)

        s.addItem(QtGui.QIcon(icon), group_name)
        s.setCurrentIndex(s.findText(group_name))



    # @my_pyqtSlot()
    def updateGroupsList(self):
        """
        Show group list depending of current dataset
        Mise a jour de la liste des groupes, a utiliser au changement de dataset seulement
        """
        p = self.panel

        ds_name = self.mcData.datasets.currentDatasetName

        ds = self.mcData.datasets.getDataset()

        groups = ds["groups"]

        s = p.combo_currentSelectionGroup

        previousGroup_selected = s.currentText()

        # Pour ne pas trigger a chaque ajout d'un groupe
        s.blockSignals(True)
        s.clear()

        mc_logging.debug("---inside updateGroupsList---")

        for group_name, group in groups.items():
            group_color = self.bl.groups.getGroupColor(ds_name, group_name)

            icon = QtGui.QPixmap(40, 40)

            icon.fill(group_color)

            s.addItem(QtGui.QIcon(icon), group_name)

            # s.setCurrentIndex(s.findText(group_name))

            # sera fait automatiquement?

            # self.changeCurrentSelectionGroup()

        # ======================================================================
        # on remet la selection comme avant si le groupe est toujours present,
        # sinon on selectionne le dernier de la liste pour trigger la mise a jour
        # de l'affichage
        # ======================================================================
        s.blockSignals(False)

        index = s.findText(previousGroup_selected)

        if index != -1: s.setCurrentIndex(index)
        else:           s.setCurrentIndex(s.findText(s.currentText()))



    def importGroup(self):

        print("inside importGroup")

        p = self.panel  # panel principal

        datasets = self.mcData.datasets

        ds_nameA = datasets.currentDatasetName

        dsA = datasets.getDataset(ds_nameA)

        # ====import GUI====================================

        d = uic.loadUi("assets//ui_files//import_groups.ui")

        d.setWindowTitle("Please select group(s) to import")

        # ======= On remplit le comboBox avec les datasets.py disponibles ==========

        items = [p.comboBox_datasets.itemText(i) for i in range(p.comboBox_datasets.count()) if
                 str(p.comboBox_datasets.itemText(i)) != datasets.currentDatasetName]

        # on le met avant le addItems pour que le callback soit appeler a l'initialisation

        d.combo_datasets.currentIndexChanged.connect(partial(self._importGroup_baseDatasetChanged, panel = d, parent_panel = p))
        d.combo_datasets.addItems(items)

        ok = d.exec_()

        # ============= On recupere les donnÃ©es de la gui =======================

        if ok:

            ds_nameB = str(d.combo_datasets.currentText())

            groups_names = [str(d.list_groups.item(i.row()).text()) for i in d.list_groups.selectedIndexes()]

            if not groups_names:
                print("No group selected")
                return

            print(("%d group(s) selected" % (len(groups_names))))

            for group_name in groups_names:

                imported_group_name = "%s - %s" % (ds_nameB, group_name)

                # ====calcul de la correspondance entre espace du ds externe et de l'actuel====

                dsB = datasets.getDataset(ds_nameB)

                group = dsB["groups"][group_name]

                # creation du groupe
                self.addGroupToDict(imported_group_name)
                #self.gui.groups.signal_addGroupToDict(imported_group_name)

                # ajout point par point apres recherche de correpondance

                # ici il faudrait prendre en compte la matrice de passage, taille des points etc...
                for i, _ in enumerate(group["indexes"]):

                    # ==========================================================
                    #   cas simple ou les ds rerivent l'un de l'autre
                    # ==========================================================

                    # dsA = current dataset
                    # dsB = imported dataset

                    xy_in_dsB  = group["xys"][i]
                    idx_in_dsB = group["indexes"][i]

                    # si on etait pas sur des jdd derivant l'un de l'autre, il faudrait

                    # faire une recherche avec inside shape ou equivalent

                    c1 = dsA["xys"][:, 0] == xy_in_dsB[0]
                    c2 = dsA["xys"][:, 1] == xy_in_dsB[1]
                    c3 = c1 & c2

                    idx_in_dsA = np.where(c3)[0]
                    xy_in_dsA  = dsA["xys"][idx_in_dsA]  # plus simplement xy_in_dsA = xy_in_dsB

                    if idx_in_dsA:
                        print(("xy_in_dsB", xy_in_dsB))
                        print(("xy_in_dsA", xy_in_dsA))
                        print(("idx_in_dsA", idx_in_dsA))
                        print(("idx_in_dsB", idx_in_dsB))

                    if idx_in_dsA:
                        self.bl.groups.addPointsToGroup(imported_group_name, ds_nameA, idx_in_dsA, xy_in_dsA, verbose = False)

                self.signals.signal_groupsUpdated.emit()
                # ==============================================================

    def _importGroup_baseDatasetChanged(self, panel, parent_panel):

        print("inside _importGroup_baseDatasetChanged")

        # p = parent_panel

        d = panel

        ds_name = d.combo_datasets.currentText()

        # ======================================================================
        # on affiche la liste des groupes associees au dataset dans la liste
        # des groupes disponibles
        # ======================================================================

        icon = QtGui.QPixmap(40, 40)

        d.list_groups.clear()

        for group_name in self.bl.groups.names(ds_name):
            print("adding", group_name)

            color = self.bl.groups.getGroupColor(ds_name, group_name)

            icon.fill(color)

            item = QtWidgets.QListWidgetItem(QtGui.QIcon(icon), group_name)

            d.list_groups.addItem(item)