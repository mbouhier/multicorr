import numpy as np
import matplotlib.pyplot as pl

from filters.dataFilter import DataFilter, FilterException

class Filter_saturate(DataFilter):


    def __init__(self, workFile):

        super().__init__()

        if workFile: self.setWorkFile(workFile)

        self.button_title = "Saturate"


    def run(self, W, X, args_dict):


        print("inside filter saturation")

        seuilI = args_dict["Intensity threshold"]
        seuil0 = args_dict["Zeros number threshold"]
        print("seuils:",seuil0,seuilI)
        # moyenne de l'intensité de chaque spectre

        imean = np.sum(X, axis = 1) / len(W)

        over = np.where(imean > seuilI)

        indices_to_delI = list(over[0])

        # print "indices_to_del I",indices_to_delI,"combien=",len(indices_to_delI)


        # choix des spectres à supprimer critère intensité et nb de zéros
        zeroo = np.where(X == 0)

        # cree une liste indice du spectre et nb de fois qu'apparait 0
        unique_indices, counts = np.unique(zeroo[0], return_counts=True)
        nbz = np.column_stack((unique_indices, counts))

        nbzfiltre = np.where(nbz[:, 1] > seuil0)

        indices_to_del0 = list()

        for v in list(nbzfiltre[0]):
            indices_to_del0.append(nbz[v, 0])

        # print "indices_to_del 0",indices_to_del0,"combien=",len(indices_to_del0)

        idxs = list()

        for ii in range(len(X)):

            if ii in indices_to_delI and ii in indices_to_del0:
                idxs.append(ii)

        return X, idxs