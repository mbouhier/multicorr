import copy

import h5py
import numpy as np
from PyQt5 import QtGui

from helpers import mc_logging


class MCBusinessLogic_groups(object):

    NameAlreadyExists = 0
    InsertDone        = 1
    currentGroup = None

    def __init__(self, mcData):
        #super(MCBusinessLogic_groups, self).__init__()
        print(type(self).__name__ + " initialized")
        self.mcData = mcData

    def _updatePointsInGroup(self, group_name, dataset_name, indexes, xys, add_or_remove = "add", verbose = True):
        """
        TODO: pourquoi doit-on fournir les xys au lieu de les recuperer dans ds["xys"][indexes] ??
        """
        datasets = self.mcData.datasets

        # ================ Tests avant mise à jour du groupe ===================

        if isinstance(indexes, np.ndarray):
            indexes = indexes.tolist()

        if type(indexes) == h5py.Dataset:
            indexes = indexes[:].tolist()

        if not isinstance(indexes, list):
            indexes = [indexes]  # si il n'y a qu'un index
            xys     = [xys]

        if len(xys) != len(indexes):
            print("'xys' and 'indexes' must have the same size")
            return

        if dataset_name not in datasets.names():
            print(("'%s' not in dataset dictionary" % (dataset_name)))
            return

        else:
            ds = datasets.getDataset(dataset_name)

        if group_name not in ds["groups"]:
            print(("'%s' group not in '%s' dataset" % (group_name, dataset_name)))
            return

        else:
            group = ds["groups"][group_name]
        # ======================================================================

        # ========= calcul des nouveaux indices/xys du groupe ==================

        # TODO: si il y a une incoherence entre les indices et les xys ->exception non gérée

        counter = 0

        if add_or_remove == "add":

            for i, idx in enumerate(indexes):
                if idx not in group["indexes"]:
                    group["indexes"].append(idx)
                    group["xys"].append(xys[i])
                    counter = counter + 1

        elif add_or_remove == "remove":

            for i, idx in enumerate(indexes):

                if idx in group["indexes"]:
                    idx_position = group["indexes"].index(idx)
                    group["indexes"].pop(idx_position)
                    group["xys"].pop(idx_position)  # remove idx_position_th element
                    counter = counter + 1

        # ======================================================================
        if verbose:
            if add_or_remove == "add":
                mc_logging.info("%d points added to group (%d given)" % (counter, len(indexes)))

            else:
                mc_logging.info(("%d points removed from group (%d given)" % (counter, len(indexes))))

    def addPointsToGroup(self, group_name, dataset_name, indexes, xys, verbose = True):

        self._updatePointsInGroup(group_name,
                                  dataset_name,
                                  indexes,
                                  xys,
                                  add_or_remove = "add",
                                  verbose = verbose)

    def removePointsFromGroup(self, group_name, dataset_name, indexes, xys, verbose = True):

        self._updatePointsInGroup(group_name,
                                  dataset_name,
                                  indexes,
                                  xys,
                                  add_or_remove = "remove",
                                  verbose = verbose)

    def removeGroupFromDict(self, name = '', dataset_name = '', family = ''):
        """
        Supprime un groupe du dictionnaire
        """
        # utile?
        mc_logging.info("Removing group from Dict")
        mc_logging.info("family:", family)
        mc_logging.info("name:", name)
        mc_logging.info("dataset_name:", dataset_name)

        if not name and not dataset_name and not family: return

        # ============ Choix du dataset dans lequel supprimer le groupe ========

        # ================== par default, dataset en cour  =====================

        # if not dataset_name:
        #     ds_name = self.currentDatasetName
        #
        # else:
        #     if not dataset_name in self.getDatasets():
        #         print(("Can't remove group, dataset '%s' doesn't exists" % (dataset_name)))
        #         return
        #     ds_name = dataset_name

        ds = self.mcData.datasets.getDataset(dataset_name)

        groups = ds["groups"]

        #print("group")
        #print(groups)

        # ============ Suppression de l'entrÃ©e dans le dictionnaire =============

        if name:
            mc_logging.info(('Removing "%s" from groups dictionary' % (name)))
            groups = {key: value for key, value in list(groups.items()) if key != name}

        if family:
            mc_logging.info(('Removing groups of "%s" family from dictionary:' % (family)))
            groups = {key: value for key, value in list(groups.items()) if not (groups[key]['family'] == family)}

        # for key,value in groups.iteritems():
        #                print "group:%s  family:%s" % (key,groups[key]['family'])
        #                if not(groups[key]['family'] == family):
        #                    groups[key] = value
        #                else:
        #                    print key,

        #        for key,value in groups.iteritems():
        #            print "group:%s  family:%s" % (key,groups[key]['family'])
        #
        #
        # enregistrement, mais pourquoi ne s'enregistre pas de lui-même

        # Ne se copies pas par reference
        # 16-09-15 --> non car on redefinit groups = {...}!

        #ds = self.mcData.datasets.py..getDataset(dataset_name)#TODO: a supprimer car en doublons?

        ds["groups"] = groups

    def addGroupToDict(self, name, family = '', indexes = [], dataset_name = '', color = None, override = False):
        """
        Cette methode ajoute le groupe 'name' dans le dictionnaire des groupes
        on peux lui fournir une "family" afin de supprimer par la suite l'ensemble
        des groupes associées à la famille "clustering" par exemple
        on peux creer un groupe vide ou fournir une liste d'indices lors de la creation
        du groupe
        return name_already_exists
        """

        # TODO, ajouter un "groupe" None

        # = On cast les input en str pour eviter des QString venant de Qt
        name         = str(name)
        dataset_name = str(dataset_name)
        family       = str(family)

        # si on ne precise pas, le groupe est ajouté au dataset en cours

        if not dataset_name:
            ds_name = self.mcData.datasets.currentDatasetName

        else:
            if not dataset_name in self.mcData.datasets.names():
                mc_logging.debug(("Can't add group, dataset '%s' doesn't exists" % (dataset_name)))
                return

            ds_name = dataset_name

        ds = self.mcData.datasets.getDataset(ds_name)

        groups = ds["groups"]

        # ========== On prend une couleur pour les points et la combobox ========

        # si pas precisé, on prend dans le liste des couleurs

        if not color:
            print("no color given")
            group_QColor = next(self.mcData.colors)
            group_color = group_QColor.getRgb()

        else:
            group_color = color

        # =============on verifie l'unicite du nom===============================
        if name in groups:
            if not override:
                return self.NameAlreadyExists
            else:
                # On supprime la precedente occurence du groupe
                self.removeGroupFromDict(name, dataset_name)

        # =======================================================================


        mc_logging.info(('adding "%s" to groups dictionary' % (name)))  # (color:%s)' % (name,str(group_color))

        # =============on cree un nouvel entree==================================

        groups[name] = dict()

        # 15-09-15: ajout de deepcopy sinon la ref de la liste etait la même que celle passé en argument

        groups[name]["indexes"] = copy.deepcopy(indexes)

        groups[name]["xys"] = []

        # TODO: plus besoin avec ds["groups"], a supprimer

        groups[name]["family"] = family  # comment a été creer ce groupe? clustering, manuel etc..

        groups[name]["color"] = group_color

        self.mcData.datasets.getDataset(ds_name)["groups"] = groups

        return self.InsertDone

    def getGroupColor(self, ds_name, group_name):

        ds = self.mcData.datasets.getDataset(ds_name)

        group = ds["groups"][group_name]

        # Rattrappe le bug de chargement des couleurs des groupes depuis les anciens hdf5

        c = group.get("color", None)

        if c is None or type(c) is str:
            group_QColor = next(self.mcData.colors)
            group["color"] = group_QColor.getRgb()

        else:
            group_QColor = QtGui.QColor(c[0], c[1], c[2])

        # print("inside get group color")
        # print(group["color"])
        # print(group_QColor)

        return group_QColor

    def setGroupColor(self, ds_name, group_name, group_QColor):

        ds = self.mcData.datasets.getDataset(ds_name)

        group = ds["groups"][group_name]

        group["color"] = group_QColor.getRgb()

    def names(self, ds_name):

        ds = self.mcData.datasets.getDataset(ds_name)

        if ds: return ds["groups"].keys()
        else : return []

    def getCurrentGroup(self):
        return self.currentGroup

    def setCurrentGroup(self, name):
        self.currentGroup = name

