import h5py
import numpy as np
import randomcolor
from PyQt5 import QtGui

from dataAccess.mcWorkFile import McWorkFile, McProjectFile


class McData(object):
    def __init__(self, tempPath = None):

        if not tempPath: tempPath = "bin\\temp"

        self.datasets      = MulticorrDatasets()
        self.relationships = MulticorrRelationships()
        self.colors        = colorGenerator() #TODO: a mettre plutot dans un helper?
        self.workFile      = McWorkFile(tempPath)
        self.projectFile   = McProjectFile(tempPath)

def colorGenerator( hue = None):

    static_mode = False
    # version Statique:

    COLORS = [(43, 250, 250), (219, 0, 115), (0, 255, 0), (145, 50, 49), (20, 35, 255), (240, 195, 0),
              (136, 77, 167), (86, 130, 3), (0, 127, 255), (102, 0, 255), (109, 7, 26), (255, 220, 18),
              (222, 49, 99), (219, 23, 2), (1, 215, 88), (204, 0, 204), (153, 102, 204), (255, 204, 255),
              (204, 255, 255), (102, 51, 51), (153, 153, 51)]

    # Avec le module randomColor https://github.com/kevinwuhoo/randomcolor-py

    rand_color = randomcolor.RandomColor()
    while True:
        if static_mode:
            for color in COLORS:
                yield QtGui.QColor(color[0], color[1], color[2])
        else:
            c = rand_color.generate(hue=hue, format_="Arrayrgb")[0]
            print("generated color:", c)
            yield QtGui.QColor(c[0], c[1], c[2])



class MulticorrRelationships(object):
    def __init__(self):
        self._relationships = dict()

    @property
    def relationships_dict(self):
        return self._relationships

    @relationships_dict.setter
    def relationships_dict(self, value):
        self._relationships = value

    def names(self):
        return list(self._relationships.keys())

    def removeByDatasetName(self, ds_name):

        print("removing relationships associated to '%s' datasets.py" % (ds_name))

        ds_name = str(ds_name)

        r = self._relationships

        # on recreer un dico sans la key "name", meilleur moyen?
        # version dictionnary, todel apres passage hdf5
        if type(r) is dict:
            r = {key: value for key, value in list(r.items()) if ds_name not in key}

        # version hdf5
        elif type(r) is h5py.Group:

            # attention, la clef est supprimé mais l'espace dans le hdf5 n'est pas liberé!

            print("debug remove dataset version hdf5")

            for key in list(r.keys()):

                if ds_name in key: del r[key]

        self._relationships = r



#TODO: utiliser une classe dataset qui encapsulerai le dataset HDF5
class MulticorrDataset(object):
    def __init__(self):
        pass



class MulticorrDatasets(object):
    def __init__(self):
        self._datasets = dict()
        self._currentDatasetName = None
        self._currentSpectrumIndex = []

    @property
    def currentDatasetName(self):
        return self._currentDatasetName

    @currentDatasetName.setter
    def currentDatasetName(self, value):
        if value in self.names():
            self._currentDatasetName = value
        else:
            raise NameError("'%s' not in datasets dict"%(value,))

    #TODO: mettre ailleur?
    @property
    def currentSpectrumIndex(self):
        return self._currentSpectrumIndex

    @currentSpectrumIndex.setter
    def currentSpectrumIndex(self, value):
        ds = self.getDataset()
        if value >= 0 and value < len(ds["X"]):
            self._currentSpectrumIndex = value
        else:
            raise IndexError("Spectrum Index out of bounds" % (value,))

    @property
    def datasets_dict(self):
        return self._datasets

    @datasets_dict.setter
    def datasets_dict(self,value):
        self._datasets = value

    def reset(self):
        self._datasets = dict()

    def pushDataset(self, dataset, name):
        # version dictionnaire
        self._datasets[name] = dataset

    def add(self):
        pass

    def remove(self, ds_name):
        print("removing dataset from datasets dictionary")

        ds_name = str(ds_name)

        d = self._datasets

        # on recreer un dico sans la key "name", meilleur moyen?
        # version dictionnary, todel apres passage hdf5
        if type(d) is dict:
            d = {key: value for key, value in list(d.items()) if not (key == ds_name)}

        # version hdf5
        elif type(d) is h5py.Group:
            # attention, la clef est supprimé mais l'espace dans le hdf5 n'est pas liberé!
            print("debug remove dataset version hdf5")
            del d[ds_name]

        self._datasets = d

        #on remet le current_dataset au premier de la liste par default
        if len(self.names()) != 0:
            self._currentDatasetName = self.names()[0]
        else:
            self._currentDatasetName = None


    def names(self):
        return list(self._datasets.keys())

    def count(self):
        return len(self._datasets.keys())

    def getDataset(self, name = None):
        """
        retourne le jdd "name" ou le jdd courant si name non specifié et None si n'existe pas
        """
        # version dictionnaire (?)
        if not name: name = self.currentDatasetName

        #self.mc_datasets.getDataset(name)
        return self._datasets.get(name, None)


    def getNumericVersionOfW(self, ds_name = None):

        """
        return ds["W"] if not containing strings label, range(lends["W"]) otherwise
        """

        ds = self.getDataset(ds_name)

        if not self.axisWContainsTextLabels(ds_name):
            W = ds["W"]
            #print("spectral axis is numeric")

        else:
            #W = list(range(len(ds["W"])))
            W = np.arange(len(ds["W"]))
            #print("spectral axis contain text, W set to range(len(W))")

        return W

    def axisWContainsTextLabels(self, ds_name = None):

        ds = self.getDataset(ds_name)

        W = ds["W"]

        has_str = False

        for i in range(len(W)):

            w_data_type = type(W[i])

            if np.issubdtype(w_data_type, float) or np.issubdtype(w_data_type, int):
                pass

            else:
                has_str = True

        return has_str


    def datasetInfos(self, ds_name):
        """
        Printable infos about dataset
        """
        ds = self.getDataset(ds_name)

        infos  = "\n"
        infos += "===================== dataset infos ===========================\n"
        infos += "name:\t\t%s\n" % (ds_name,)
        infos += "spNb:\t\t%s\n" % (ds["size"],)
        infos += "xNb:\t\t%s\n" % (len(ds["W"]),)
        infos += "Image width:\t%s\n" % (ds["image_width"],)
        infos += "Image height:\t%s\n" % (ds["image_height"],)
        infos += "Image ratio:\t%s\n" % (ds["aspect_ratio"],)
        infos += "x_unit:\t\t%s\n" % (ds["x_unit"],)
        infos += "y_unit:\t\t%s\n" % (ds["y_unit"],)
        infos += "spatial_unit:\t%s\n" % (ds["spatial_unit"],)
        infos += "===============================================================\n"
        infos +="\n"

        return infos