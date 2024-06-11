from PyQt5 import QtGui
from PyQt5 import QtCore
#=================================================================
# Models pour les elements de la GUI A FINIR
#=================================================================

class MulticorrGroupListModel(QtCore.QAbstractListModel):
    def __init__(self, datasets, parent = None):
        super().__init__(parent)
        self.__datasets = datasets

    def rowCount(self, parent = None):
        ds = self.__datasets.getDataset()
        return ds.groups.count()

    # def setData(self, QModelIndex, Any, role=None):
    #     pass
    def flags(self, QModelIndex):
        pass

    def data(self, index, role):

        ds = self.__datasets.getDataset()
        row = index.row()
        value = self.ds.groups.names()[row]
        group = self.ds.groups.getGroup(value)

        if role == QtCore.Qt.DisplayRole:
            return value

        elif role == QtCore.Qt.EditRole:
            return value

        elif role == QtCore.Qt.DecorationRole:
            color = group.color()
            icon = QtGui.QPixmap(40, 40)
            icon.fill(color)
            return icon

        elif role == QtCore.Qt.ToolTipRole:
            count   = group.count()
            percent = count/ds.size()
            family  = group.family()

            txt = "count: %d points\ncoverage: %.2f%% of %d\nfamily: %s" % (count, 100.*percent, ds.size(), family)
            return txt


class MulticorrDatasetListModel(QtCore.QAbstractListModel):

    def __init__(self, datasets, parent=None):
        super().__init__(parent)
        self.__datasets = datasets

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return "Dataset Name"
            else:
                return QtCore.QString("dataset %1").arg(section)

    def rowCount(self, parent=None):
        return self.__datasets.count()

    def data(self, index, role):

        ds = self.__datasets
        row = index.row()
        value = self.ds.names()[row]

        if role == QtCore.Qt.DisplayRole:
            return value

        elif role == QtCore.Qt.EditRole:
            return value

        elif role == QtCore.Qt.DecorationRole:
            color = self.ds.getDataset(value).color()
            icon = QtGui.QPixmap(40, 40)
            icon.fill(color)
            return icon