from PyQt5 import QtWidgets
from PyQt5 import uic
from PyQt5.QtWidgets import QPushButton

from helpers import mc_logging
import math

class GroupsFromXYSlices(object):

    def __init__(self, bl, mcData, gui):
        super().__init__()

        self.tab = "Filtering"
        self.family = ""
        self.name   = "Groups from XY Slices"
        self.tooltip_text = "tooltip text..."

        self.menu_item = QPushButton("Slices",
                                     clicked = self.launchMainGui)

        self.bl = bl
        self.mcData = mcData
        self.gui = gui

        self.mainWindow = self.gui.main.mainWindow


    def launchMainGui(self):
        """
        Create Groups from user slices
        divide dataset in (x_groups * y_groups) groups
        """

        ds = self.mcData.datasets.getDataset()

        # ====import GUI====================================

        d = uic.loadUi("assets//ui_files//groups_slices_xy.ui")

        d.setWindowTitle("Automatic groups creation - XY profiling")

        # allowed_x_dividers = [str(x) for x in range(ds["width"]) if x != 0 and ds["width"] % x == 0]
        # allowed_y_dividers = [str(y) for y in range(ds["height"]) if y != 0 and ds["height"] % y == 0]

        allowed_x_dividers = [str(i) for i in range(1, 51)]
        allowed_y_dividers = [str(i) for i in range(1, 51)]

        d.combo_xGroups.addItems(allowed_x_dividers)
        d.combo_yGroups.addItems(allowed_y_dividers)

        ok = d.exec_()

        if ok:
            x_groups = int(d.combo_xGroups.currentText())
            y_groups = int(d.combo_yGroups.currentText())

            self._createGroupsFromXYSlices(x_groups, y_groups)

        #            myThread = Thread(target=self._createGroupsFromXYSlices, args = (x_groups, y_groups))
        #            myThread.daemon = True
        #            myThread.start()

    def _createGroupsFromXYSlices(self, x_groups, y_groups):
        """
        Create Groups from user slices
        divide dataset in (x_groups * y_groups) groups

        Devait etre lancé dans un thread, mais probleme de synchro avec la creation/affichage de la liste des groupes
        """

        MAX_ALLOWED_GROUPS_NB = 200

        if x_groups * y_groups >= MAX_ALLOWED_GROUPS_NB:
            # TODO: gerer l'affichage d'un grand nombre de group sans lag

            mc_logging.debug("Group number too high for display: %d requested, max %d" % (
            x_groups * y_groups, MAX_ALLOWED_GROUPS_NB))

            QtWidgets.QMessageBox.warning(self.mainWindow,
                                          "Error",
                                          "Group number too high for display ( max = %d )" % (MAX_ALLOWED_GROUPS_NB,))

            return

        #################"!!!on supprime si deja present, pas en SIGNAL car risque de decallage?
        self.gui.groups.removeGroupFromDict(family = "slices")
        # self.gui.main.signal_removeGroupFromDict.emit("","","slices",True)
        self.gui.signals.signal_groupsUpdated.emit()

        ds_name = self.mcData.datasets.currentDatasetName
        ds = self.mcData.datasets.getDataset()

        # ======================================================================
        # on calcul le nombre de ligne ou/et colonne à enlever pour avoir des
        # groupes de meme taille
        # ======================================================================

        width = ds["width"]
        height = ds["height"]

        used_width = (width - (width % x_groups))
        used_height = (height - (height % y_groups))

        # division euclidienne
        step_x = used_width // x_groups
        step_y = used_height // y_groups

        print("Groups size: (dx,dy) = (%d,%d)" % (step_x, step_y))
        print("Dataset used part (%d,%d) -> (%d,%d)" % (width, height, used_width, used_height))

        # ======================================================================

        idxs = ds["img_coo_to_idx"]

        used_idxs = idxs[0:used_height, 0:used_width]

        slices_arrays = self.blockshaped(used_idxs, step_y, step_x)

        for i, slice_idxs in enumerate(slices_arrays):
            slice_name = "(%d,%d)" % (i // x_groups, i % x_groups)

            self.gui.groups.addGroupToDict(slice_name, family = "slices", updateDisplay = False)

            indexes = slice_idxs.flatten().tolist()

            indexes = [int(point_idx) for point_idx in indexes if not math.isnan(point_idx)]

            xys = [ds["xys"][point_idx] for point_idx in indexes]

            self.bl.groups.addPointsToGroup(slice_name, dataset_name = ds_name, indexes = indexes, xys = xys, verbose = False)

            self.gui.main.displayProgressBar(100. * i / (x_groups * y_groups))

        self.gui.main.resetProgressBar()

        # ======================================================================
        # Ces 2 doivent etres appellés car on a demandé updateDisplay = false
        # TODO: faire autrement/automatiquement
        # ======================================================================

        self.gui.groups.signal_updateGroupsList.emit()
        self.gui.groups.signal_updateGroupsDisplayHolders.emit()
        # ======================================================================

        self.gui.signals.signal_groupsUpdated.emit()


    def blockshaped(self, arr, nrows, ncols):
        """
        Return an array of shape (n, nrows, ncols) where

        n * nrows * ncols = arr.size

        If arr is a 2D array, the returned array should look like n subblocks with
        each subblock preserving the "physical" layout of arr.

        """

        h, w = arr.shape

        return (arr.reshape(h // nrows, nrows, -1, ncols)
                .swapaxes(1, 2)
                .reshape(-1, nrows, ncols))


