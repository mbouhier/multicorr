from PyQt5.QtWidgets import QWidget

import importlib
import pkgutil

#TODO, charger de maniere automatique les classes presentes dans les sous-dossiers de "plugins"
from plugins.spectral_rois.spectral_roi_creation import SpectralRoiCreation
from plugins.spikes_removal.spikes_removal import SpikesRemoval
from plugins.groups_from_XY_slices.groups_from_XY_slices import GroupsFromXYSlices
from plugins.clustering.clustering import Clustering
from plugins.dataset_linker.dataset_linker import DatasetLinker
from plugins.fitting.fitting import Fitting
from plugins.mcr.mcr import MultivariateCurveResolution
from plugins.likeness_spectral_picker.likeness_spectral_picker import LikenessSpectralPicker


class Plugins(object):

    def __init__(self, bl, mcData, gui):
        self._plugins_dict = {}

        self.bl = bl
        self.mcData = mcData
        self.gui = gui

        self.load_all()

    def __iter__(self):
        return iter(self._plugins_dict.items())


    def load_all(self):
        print("loading all plugins in folder...")

        for plugin in (SpectralRoiCreation,
                       SpikesRemoval,
                       GroupsFromXYSlices,
                       Clustering,
                       DatasetLinker,
                       Fitting,
                       MultivariateCurveResolution,
                       LikenessSpectralPicker):

            p = plugin(self.bl, self.mcData, self.gui)
            self._plugins_dict[p.name] = p


    def get_plugins_names(self):
        return self._plugins_dict.keys()

    def get_plugin_by_name(self, name):

        if name in self._plugins_dict:
            return self._plugins_dict[name]
        else:
            raise(ImportError("No plugin named '{}'".format(name)))


class McPlugin(object):

    def __init__(self):
        pass

    # def getMainMenu(self):
    #     w = Qwidget()
    #     return w
    #
    # def getLeftMenu(self):
    #     w = Qwidget()
    #     return w
    #
    # def getMainWindow(self):
    #     w = Qwidget()
    #     return w

if __name__ == "__main__":
    pass