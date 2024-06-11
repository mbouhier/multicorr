from PyQt5.QtCore import QObject
import copy


#https://www.youtube.com/watch?v=ZLsRi6gY7y0&list=PL8B63F2091D787896&index=8

class MulticorrRelationships(QObject):
    def __init__(self, multicorrDatasets):
        super().__init__()
        self._relationships = dict()
        self._multicorrDatasets = multicorrDatasets

    def names(self):
        """
        Return datasets.py relationships
        """
        names = []

        for k in list(self._relationships.keys()):

            a, b = k.split(",")

            if a not in names: names.append(a)
            if b not in names: names.append(b)

        return names


class MulticorrRelationship(QObject):
    def __init__(self):
        super().__init__()



class MulticorrDatasets(QObject):
    def __init__(self):
        super().__init__()
        self._datasets = dict()
        self._currentDataset = None

    def getDataset(self):
        pass
    def add(self):
        pass
    def remove(self):
        pass
    def names(self):
        return self._datasets.keys()
    def count(self):
        pass


class MulticorrDataset(QObject):
    def __init__(self):
        super().__init__()
        self._dataset = dict()
        self.dict = self._dataset #pour faire l'intermediaire

    def groups(self):
        pass
    def color(self):
        pass
    def name(self):
        pass


class MulticorrGroups(QObject):

    def __init__(self):
        super().__init__()
        self._groups = dict()
        self._currentGroup = ''
        self._colorGenerator


    def add(self, name, family = '', indexes = [], color = None):
        """
        Cette methode ajoute le groupe 'name' dans le dictionnaire des groupes
        on peux lui fournir une "family" afin de supprimer par la suite l'ensemble
        des groupes associées à la famille "clustering" par exemple
        on peux creer un groupe vide ou fournir une liste d'indices lors de la creation
        du groupe
        """

        # TODO, ajouter un "groupe" None

        # = On cast les input en str pour eviter des QString venant de Qt
        name   = str(name)
        family = str(family)
        groups = self._groups

        # ========== On prend une couleur pour les points et la combobox ========
        # si pas precisé, on prend dans le liste des couleurs

        if not color:
            print("no color given")
            group_QColor = next(self._colorGenerator)
            group_color = group_QColor.getRgb()

        else:
            group_color = color

        print(('adding "%s" to groups dictionary' % (name)))  # (color:%s)' % (name,str(group_color))

        # =============on cree un nouvel entree==================================
        groups[name] = dict()

        # 15-09-15: ajout de deepcopy sinon la ref de la liste etait la même que celle passé en argument

        groups[name]["indexes"] = copy.deepcopy(indexes)
        groups[name]["xys"] = []

        # TODO: plus besoin avec ds["groups"], a supprimer

        groups[name]["family"] = family  # comment a été creer ce groupe? clustering, manuel etc..
        groups[name]["color"]  = group_color

        self._groups = groups

    def remove(self):
        pass
    def count(self):
        pass
    def names(self):
        pass
    def getGroup(self, groupName = ''):
        pass
    def currentGroup(self):
        return self._currentGroup


class MulticorrGroup(QObject):
    def __init__(self, color_generator):
        super().__init__()
        self._group = dict()
        self._color_generator = color_generator

    @property
    def color(self):

        group = self._group

        # Rattrappe le bug de chargement des couleurs des groupes depuis les anciens hdf5
        if not group.get("color", ""):

            group_QColor = next(self._color_generator)
            group["color"] = group_QColor.getRgb()

        else:
            c = group["color"]
            group_QColor = QtGui.QColor(c[0], c[1], c[2])

        # print("inside get group color")
        # print(group["color"])
        # print(group_QColor)

        return group_QColor

    @color.setter
    def color(self, group_QColor):
        self._group["color"] = group_QColor.getRgb()


    def idxs(self):
        pass
    def name(self):
        pass
    def family(self):
        pass