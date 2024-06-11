import numpy as np
from PyQt5 import QtWidgets
from PyQt5 import uic
from scipy.cluster.vq import kmeans, vq

from helpers import mc_logging


class Clustering(object):

    def __init__(self, bl, mcData, gui):
        super().__init__()

        self.tab = "Clustering"
        self.family = ""
        self.name   = "clustering"
        self.tooltip_text = "tooltip text..."

        self.menu_item  = self.getTopMenuWidget()
        self.mainView = None

        self._make_connections()

        self.bl = bl
        self.mcData = mcData
        self.gui = gui

        self.mainWindow = self.gui.main.mainWindow

    def _make_connections(self):
        p = self.menu_item
        p.button_launchCluster.clicked.connect(self.processClustering)
        #p.slider_clusterDimensions.valueChanged.connect(self.clusterDimensionsChanged)
        p.button_reprChoice.clicked.connect(self.chooseRepresentationsForClustering)
        p.comboBox_clusteringSource.currentIndexChanged.connect(self.clusterDataSourceChanged)


    def getTopMenuWidget(self):
        return uic.loadUi("assets//ui_files//clustering_menu.ui")



    def getParametersFromGui(self):
        p = self.menu_item

        proj = self.gui.projections.getCurrentProjection()
        cluster_nb = p.slider_clusterNumber.value()
        #clusterDim = p.slider_clusterDimensions.value()
        source = str(p.comboBox_clusteringSource.currentText())
        delPrevGroups = p.checkBox_clusterRemovePrevious.isChecked()

        return proj, cluster_nb, source, delPrevGroups

    def processClustering(self):
        """
        26/05/2015: ajout fonction clustering automatique sur PCs
        Cette methode crée des N groupes de données automatiquement en se basant
        sur un Kmean à M dimensions
        """

        ds_name = self.mcData.datasets.currentDatasetName
        ds = self.mcData.datasets.getDataset(ds_name)

        proj, cluster_nb , source, delPrevGroups = self.getParametersFromGui()

        print("Processing clustering with data source:", source)
        print("delPrevious Group:", delPrevGroups)

        if source == "Selected Projection":
            if not proj:
                mc_logging.debug("No projection available for clustering")
                QtWidgets.QMessageBox.information(self.mainWindow,
                                                  'No Projection',
                                                  "No projection available for clustering")
                return

            else:
                data = proj["values"][:, :]#proj["values"][:, 0:clusterDim]


        elif source == "Representations":

            data = ds['metadatas'].get('reduced_dataset_from_representations', None)

            if data is None:
                QtWidgets.QMessageBox.information(self.mainWindow,
                                                  'No Data',
                                                  "Please select at least one representation from list")
                return
            else:
                data = data[:]
                #clusterDim = data.shape[1]

        # =======================================================================

        print("Processing clustering...", end = '')# on %d dimensions..." % (clusterDim), end=' ')

        # computing K-Means with cnb (cnb clusters)
        centroids, _ = kmeans(data, cluster_nb)

        # assign each sample to a cluster
        labels, _ = vq(data, centroids)

        print("Done!")

        # ==============================================================
        # On construit autant de groupes que de nombre de clusters
        # ==============================================================

        if delPrevGroups:
            # on supprime les precedents clusters si demandé, on enleve les groupes tagés "clustering"
            self.gui.groups.removeGroupFromDict(family = "clustering")

        for i in range(len(centroids)):
            group_name = "cluster %d" % (i)

            self.gui.groups.addGroupToDict(group_name, family = "clustering")

            indexes = np.where(labels == i)[0].tolist()

            xys = [ds["xys"][point_idx] for point_idx in indexes]

            self.bl.groups.addPointsToGroup(group_name,
                                            dataset_name = ds_name,
                                            indexes = indexes,
                                            xys = xys)

        self.gui.signals.signal_groupsUpdated.emit()


    def chooseRepresentationsForClustering(self):
        """
        Cette methode ouvre une GUI permettant de selectionner les representations
        à utiliser pour le clustering
        """

        mc_logging.debug("inside chooseRepresentationsForClustering")

        p = self.menu_item

        ds_name = self.mcData.datasets.currentDatasetName

        ds = self.mcData.datasets.getDataset()

        # =====================================================================
        #              import GUI
        # =====================================================================

        d = uic.loadUi("assets//ui_files//multiple_choice_from_list.ui")

        d.setWindowTitle("Please select representations to use")

        # ======= On remplit la listBox avec les representations disponibles ==========
        list_reprs = self.bl.representations.getAvailableRepresentations(ds_name)

        list_reprs = ["%s - %s" % (family, repr_name) for family, repr_name in list_reprs]

        d.list_availableItems.addItems(list_reprs)

        ok = d.exec_()

        # =====================================================================
        #               On recupere les donnees de la gui
        # =====================================================================

        if ok:

            requested_repr_names = [str(d.list_availableItems.item(i.row()).text()) for i in
                                    d.list_availableItems.selectedIndexes()]

            print("requested_repr_names:", requested_repr_names)

            # =================================================================
            #               Creation d'un conteneur
            # =================================================================
            nb_chanels = len(requested_repr_names)

            ds_size = ds["size"]

            values = self.bl.io.workFile.getTempHolder((ds_size, nb_chanels))

            print("Creating data matrix...")

            for i, family_and_repr_name in enumerate(requested_repr_names):
                family_name, repr_name = family_and_repr_name.split(" - ")

                rep = self.bl.representations.getRepresentation(ds_name, family_name, repr_name)

                vals = self.bl.representations.getValuesFromImage(rep["image"])

                values[:, i] = vals[:, 0]

                self.gui.main.displayProgressBar(100.0 * i / nb_chanels)

            self.gui.main.resetProgressBar()

            print("Data matrix creation done!")

            ds['metadatas']["reduced_dataset_from_representations"] = values

            # label d'infos sur le nombre de canaux
            p.label_clusterDimensions.setText(str(nb_chanels))


    # def clusterDimensionsChanged(self):
    #     """
    #     Display only, update cluster label "baseVect[0] to baseVect[x]" when cluster dimension change
    #     """
    #     p = self.menu_item
    #
    #     clusterDim = p.slider_clusterDimensions.value()
    #
    #     if clusterDim > 0:
    #         p.label_clusterDimensions.setText("bv[0] to bv[%d]" % (clusterDim + 1))
    #     else:
    #         p.label_clusterDimensions.setText("bv[0]")

    def clusterDataSourceChanged(self):
        """
        Display only, update cluster label "baseVect[0] to baseVect[x]" when datasource
        changed. Disable/enable dimensions choice
        """

        p = self.menu_item

        data_source = str(p.comboBox_clusteringSource.currentText())

        ds = self.mcData.datasets.getDataset()

        data = ds['metadatas'].get('reduced_dataset_from_representations', None)

        if data_source == "Selected Projection":

            #p.slider_clusterDimensions.setEnabled(True)
            p.button_reprChoice.setEnabled(False)

            #self.clusterDimensionsChanged()

        else:
            #p.slider_clusterDimensions.setEnabled(False)
            p.button_reprChoice.setEnabled(True)

            if data is not None:
                clusterDims_label = str(data.shape[1])
            else:
                clusterDims_label = 'no data'

            #p.label_clusterDimensions.setText(clusterDims_label)