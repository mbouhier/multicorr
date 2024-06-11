import numpy as np
import matplotlib.pyplot as pl

from filters.dataFilter import DataFilter, FilterException
from PyQt5 import uic
import copy


class Filter_fluo(DataFilter):


    def __init__(self, workFile):

        super().__init__()

        if workFile: self.setWorkFile(workFile)

        self.button_title = "Fluo"


    def run(self, W, X, args_dict):

        # 17/09/15: ajout d'une interface graphique

        # =====================================================================#
        d = uic.loadUi("assets\\ui_files\filter_fluo.ui")
        ok = d.exec_()

        # ============= On recupere les donnees de la gui =======================

        if ok:

            threshold = d.spinbox_slopeThreshold.value()
            split_value = d.spinbox_splitValue.value()

        else:
            return

        # =====================================================================#





        # TODO: il faudrait eviter de tomber sur un pic au debut ou à la fin

        # il faudrait prendre la mediane d'un emsemble de n points au lieu de X[0] et X[-1]

        spectrum_size = len(X[1])

        # pas encore utilisé

        split_index = np.abs(W - split_value).argmin()

        print(10 * "-", "Fluo Filter", 10 * "-")

        # Pas encore utilisé

        # print "SplitLine at W[%d] = %.3f (closest value for %.3f)" % (split_index,W[split_index],split_value)

        print("filtering threshold for slopes >", threshold)

        idxs = []

        Xf = copy.deepcopy(X)

        for i in range(len(X)):

            # pente de la premiere section et coo à l'origine

            alpha1 = (X[i, split_index] - X[i, 0]) / (W[split_index] - W[0])
            # pente de la deuxième section
            alpha2 = (X[i, -1] - X[i, split_index]) / (W[-1] - W[split_index])
            alpha2 = (X[i, -1] - X[i, split_index]) / (W[-1] - W[split_index])

            # pente "generale"

            alpha3 = (X[i, -1] - X[i, 0]) / (W[-1] - W[0])

            # si le seuil fluo est franchi

            if alpha3 >= threshold:

                idxs.append(i)

                # on applique les corrections

                for ii in range(0, spectrum_size):

                    new_value = X[i, ii] - alpha3 * W[ii]

                    # Xf[i,ii] = new_value

                    if new_value < 0:
                        Xf[i, ii] = 0  # evite d'avoir des valeurs negatives

                    else:
                        Xf[i, ii] = new_value


                    #                #on applique les corrections
                    #                for ii in range(0, spectrum_size):
                    #                    if ii < split_index:
                    #                        new_value = X[i,ii] - alpha1*W[ii]
                    #                    else:
                    #                        new_value = X[i,ii] - alpha2*W[ii]
                    #                    #Xf[i,ii] = new_value
                    #                    if new_value < 0 : Xf[i,ii] = 0 #evite d'avoir des valeurs negatives
                    #                    else: Xf[i,ii] = new_value
                    # print 'new_value',new_value

        return Xf, idxs