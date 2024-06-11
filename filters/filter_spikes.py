import time
from functools import partial
from threading import Thread

import numpy as np
import matplotlib.pyplot as pl

import time
from functools import partial
from threading import Thread

from PyQt5 import uic
from PyQt5.QtCore import pyqtSignal
from plotpy.builder import make

from filters.dataFilter import DataFilter, FilterException


class Filter_spikes(DataFilter):


    def __init__(self, workFile):

        super().__init__()

        if workFile: self.setWorkFile(workFile)

        self.button_title = "Spikes"


    def run(self, W, X, args_dict):

        print("inside filter spikes")

        max_ratio_mean_data = args_dict["maximum ratio mean data"]
        max_ratio_window    = args_dict["maximum ratio"]
        window_size         = args_dict["window size"]

        idxs = []

        # =========Spikes detection=====================

        W_size = len(W)

        for i in range(len(X)):

            imean = np.sum(X[i]) / W_size
            maxi  = np.amax(X[i])

            if maxi > max_ratio_mean_data * imean:
                idxs.append(i)

        # ==============================================


        # ==============================================
        # Pour chaques spectres pour lesquels on a detecté un spikes
        # Recherche des maximas dans un fenetre de taille
        # window_size dans les spectres precedents
        # ===============================================

        print("Processing spike correction on %d spectrum(s):" % (len(idxs)))

        for sp_idx in idxs:

            print(".", end=' ')
            spectrum = X[sp_idx]
            W_idxs = []  # indices en W

            # ==== on balaye la fenetre sur tout W ========

            for i in range(0, W_size - window_size):

                window = spectrum[i: i + window_size]

                # valeur au premier et dernier point de la fenetre
                a = window[0]
                b = window[-1]

                # valeur max dans la fenetre

                maxv = np.amax(window)

                if maxv > max_ratio_window * (a + b) / 2:
                    W_idxs.append(i + window_size / 2)
            # ==============================================

            # contiendra des groupes ex [[1,2,3,4],[53,54,55,56,57,58],[145,146,147]]
            groups_pics = []
            count = 1
            min_count = 0

            # == on garde seulement les points quand au moins min_count se suivent ===

            if len(W_idxs) < min_count:
                break  # on s'arrete la et on passe au spectre suivant

            group = []  # contenant temporaire pour un groupe d'indices

            print("W_idxs for spectrum %d" % (sp_idx), W_idxs)

            for i in range(1, len(W_idxs)):

                # si la valeur en cours suit la precedente

                if W_idxs[i] == W_idxs[i - 1] + 1:

                    count = count + 1

                    if count == min_count:

                        for j in range(min_count - 1, -1, -1):
                            group.append(W_idxs[i - j])

                    if count > min_count:
                        group.append(W_idxs[i])



                else:  # reinitialisation

                    count = 1

                    if group: groups_pics.append(group)

                    group = []

            # si on est a la derniere iteration de la boucle

            if group: groups_pics.append(group)

            print("for spectrum %d, groups_pics:" % (sp_idx), groups_pics)

            pl.figure()
            pl.plot(W, X[sp_idx], c='r')

            for group in groups_pics:

                # on se met un peus avant et un peus apres pour faire une droite

                offset = 3

                i_min = group[0] - offset
                i_max = group[-1] + offset

                if i_min < 0: i_min = 0
                if i_max > len(W) - 1: i_max = len(W) - 1

                # droite d'equation ax + b

                a = (spectrum[i_min] - spectrum[i_max]) / (W[i_min] - W[i_max])
                b = spectrum[i_min] - a * W[i_min]

                print("a:", a)
                print("imin,imax", i_min, i_max)

                for i in range(i_min, i_max):
                    spectrum[i] = a * W[i] + b

                X[sp_idx] = spectrum

                pl.scatter(W[group], X[sp_idx][group], c='b')

            pl.plot(W, X[sp_idx], c='g')

        pl.show()

        print("done")

        return X, idxs