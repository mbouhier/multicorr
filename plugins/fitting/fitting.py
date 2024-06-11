import numpy as np
from PyQt5 import QtWidgets
from PyQt5 import uic
from scipy.cluster.vq import kmeans, vq

from helpers import mc_logging
from PyQt5.QtWidgets import QFileDialog
from XMLModelLoader import XMLModelLoader
import os
from lmfit import minimize, Parameters#, report_errors
#import matplotlib.pyplot as pl
import matplotlib.pyplot as pl
from threading import Thread
from functools import partial
from PyQt5 import QtCore
from helpers.plots import plots
from helpers.io.datasetsImporter import DatasetsImporter
from scipy.interpolate import interp1d



from PyQt5.QtCore import pyqtSignal, QObject


import time

#Faire heriter toute les classes buisness logic d'une classe mere qui integrerais QObject
class Fitting(QObject):

    signal_updateFitsList = pyqtSignal()
    signal_updateSpectrumsRefsList = pyqtSignal()

    def __init__(self, bl, mcData, gui):
        super().__init__()

        self.tab = "Fit"
        self.family = ""
        self.name   = "fitting"
        self.tooltip_text = "tooltip text..."

        self.menu_item  = self.getTopMenuWidget()
        self.mainView = None

        self.bl = bl
        self.mcData = mcData
        self.gui = gui

        self._make_connections()
        self._init_vars()
        self._init_gui()

        self.mainWindow = self.gui.main.mainWindow

    def _make_connections(self):
        p = self.menu_item

        p.button_loadXMLModels.clicked.connect(self.loadXMLModels)
        p.button_launch_fit.clicked.connect(self.launchXMLModelsFit)
        p.button_addSpectrumReference.clicked.connect(partial(self.updateRefsForHybridFit, "add"))
        p.button_delSpectrumReference.clicked.connect(partial(self.updateRefsForHybridFit, "remove"))
        p.button_loadDataModels.clicked.connect(self.loadDataModels)

        self.signal_updateFitsList.connect(self.updateFitsList)
        self.signal_updateSpectrumsRefsList.connect(self.updateSpectrumsRefsList)

        self.gui.datasets.signal_updateDisplayOnDatasetChange.connect(self.updateSpectrumsRefsList)
        self.gui.projections.signal_updateProjectionList.connect(self.projectionListChanged)


    def _init_vars(self):
        fit_method_id = {'Levenberg-Marquardt': 'leastsq',
                         #                           'Nelder-Mead':'nelder',
                         #                           'L-BFGS-B':'lbfgsb',
                         #                           'Powell':'powell',
                         #                           'Conjugate Gradient':'cg',
                         #                           'Newton-CG':'newton',
                         #                           'COBYLA':'cobyla',
                         #                           'Truncated Newton':'tnc',
                         #                           'Trust Newton-CGn':'trust-ncg',
                         #                           'Dogleg':'dogleg',
                         #                           'Newton-CG':'newton',
                         #                           'Sequential Linear Squares Programming':'slsqp',
                         #                           'Differential Evolution':'differential_evolution',
                         }

        self.fit_method_id = fit_method_id

    def getTopMenuWidget(self):
        return uic.loadUi("assets//ui_files//fitting.ui")

    def _init_gui(self):
        p = self.menu_item
        p.combo_fit_methods.addItems(sorted(self.fit_method_id.keys()))


    def loadXMLModels(self):

        p = self.menu_item

        loader = XMLModelLoader()

        modelFitXMLfilenames = QFileDialog.getOpenFileNames(self.mainWindow, "Select XMLModel reference files...", "*.xml")[0]
        modelFitXMLfilenames = list(map(str, modelFitXMLfilenames))

        # ============pour debug seulement, on charge automatiquement===========

        preload_debug = False

        if preload_debug:
            cdir = os.path.dirname(os.path.abspath(__file__)) + "\\"  # current directory

            # ==========================================================================
            # Chargement images .jpg, .jpeg
            # ==========================================================================

            modelFitXMLfilenames = [

                cdir + 'bin\\XMLs fit models\\fh2r.xml',
                cdir + 'bin\\XMLs fit models\\fluo_SplitLine.xml',
                cdir + 'bin\\XMLs fit models\\goethite12.xml',
                cdir + 'bin\\XMLs fit models\\goethiteG3.xml',
                #       cdir + 'bin\\XMLs fit models\\hematite.xml',
                cdir + 'bin\\XMLs fit models\\lepidocrocite.xml',
                cdir + 'bin\\XMLs fit models\\akaganeite.xml',
                cdir + 'bin\\XMLs fit models\\maghemite.xml',
                #        cdir + 'bin\\XMLs fit models\\magnetite.xml',
                #        cdir + 'bin\\XMLs fit models\\\wustite.xml'
            ]

        # ======================================================================


        if not modelFitXMLfilenames: return
        # On met à jour l'affichage des models disponibles et on enregistre
        # les noms chemins des XML associés

        modelsPaths = dict()

        list_items = []

        for filename in modelFitXMLfilenames:
            model_name = loader.getModelName(filename)
            modelsPaths[model_name] = filename
            list_items.append(model_name)

        p.list_XMLModels.clear()
        p.list_XMLModels.addItems(list_items)

        self.modelsPaths = modelsPaths

    def projectionListChanged(self):
        p = self.menu_item

        #TODO, prendre plutot l'information dans le bl.projection
        proj_name = self.gui.projections.getProjectionNameInGui()

        if proj_name: p.checkBox_use_projection.setEnabled(True)
        else:         p.checkBox_use_projection.setEnabled(False)

    def launchXMLModelsFit(self):
        """
        voir http://cars9.uchicago.edu/software/python/lmfit/lmfit.pdf
        et   http://lmfit.github.io/lmfit-py/parameters.html
        """

        p = self.menu_item

        ds = self.mcData.datasets.getDataset()

        modelsPaths = getattr(self, 'modelsPaths', [])

        # externalRefs = getattr(sel,'data_refs_dict',dict())

        current_index = self.mcData.currentSpectrumIndex#self.currentIdx

        fit_mode = str(p.combo_fit_option.currentText())
        fit_method = str(p.combo_fit_methods.currentText())
        use_projection = p.checkBox_use_projection.isChecked()

        # use_hybridFit  = p.checkBox_use_hybridFit.isChecked()



        if self.gui.spectrums.useNormalizedData:
            X = self.gui.datasets.getDataset_X_normalized()

        else:
            X = ds["X"]

        # =====================================================================#
        # On recupere la liste des models selectionnés et l'adresse des XMLs  #
        # =====================================================================#

        selected_models = self.getSelectedModelsNames_forFit()

        # pour debug seulement
        # selected_models = [str(p.list_XMLModels.item(i).text()) for i in range(p.list_XMLModels.count())]


        selected_spRefs = self.getSelectedSpectrumsRefsNames_forFit()

        print("debug, selected_spRefs:", selected_spRefs)

        if not (selected_models or selected_spRefs):
            s = "Please select at least one model"
            QtWidgets.QMessageBox.information(self.mainWindow, 'Error', s)
            print(s)
            return

        # ======================================================================
        #                      Fit XML
        # ======================================================================

        print("XML Mode fit, %d models selected:" % (len(selected_models),))

        for m in selected_models: print("   -%s" % (m))

        modelFitXMLfilenames = [modelsPaths[model_name] for model_name in selected_models]

        # ======================================================================
        #                    Fit spectres du ds et externe
        # ======================================================================

        print("Ref spectrum Mode fit, %d models selected:" % (len(selected_spRefs),))

        for m in selected_spRefs: print("   -%s" % (m))

        try:
            print("ds['metadatas']['references_sp']", ds["metadatas"]["references_sp"])

        except Exception as e:
            pass

        refsFitSpectrums = {ref_name: ds["metadatas"]["references_sp"][ref_name] for ref_name in selected_spRefs}

        #        #======================================================================
        #        #                    Fit des references externes
        #        #======================================================================
        #        print "External spectrums Mode fit, %d models selected:" % (len(externalRefs),)
        #        for m in externalRefs.keys():
        #            print "   -%s" % (m)



        # =====================================================================#
        # On charge l'equation, les noms des parametres et leurs bornes       #
        # depuis les XMLs                                                     #
        # =====================================================================#
        loader = XMLModelLoader()

        try:

            # coeffs_bounds n'est pas utilisé mais definit via la GUI
            models, equationXML, coeffs_names, _, match_names = loader.loadModels(modelFitXMLfilenames)

        except Exception as e:

            print("Error: Can't load Models ")
            print(e)
            return

        # print "equation:",equation



        print("--- total equation matching names (XML) ---")

        for idx, c_name in enumerate(coeffs_names):
            print(c_name, ":", match_names[c_name])

        model_nb = len(models)

        # print "equation apres chargement XML",
        # print equationXML



        # =====================================================================#
        # On prepare l'ajout les references autres que XML (jdd+externes)              #
        # =====================================================================#

        if (equationXML and selected_spRefs):
            equationRefs = " + "

        else:
            equationRefs = ""

        # ======================================================================
        # on met les spectres reference dans une liste pour les envoyer
        # à la fonction evaluant l'equation
        # ======================================================================

        # refsFitIndexes   = []
        # refsFitSpectrums = []


        # =====================================================================#
        # On rajoute les references contenues dans refsFitSpectrums            #
        # =====================================================================#

        for j, (ref_name, ref) in enumerate(refsFitSpectrums.items()):

            coeff_idx = len(coeffs_names)

            match_names["coeff[%d]" % (coeff_idx)] = ref_name

            coeffs_names.append("coeff[%d]" % (coeff_idx,))

            equationRefs = equationRefs + "coeff[%d]*refs['%s']" % (len(coeffs_names) - 1, ref_name,)

            if j != (len(selected_spRefs) - 1): equationRefs = equationRefs + "+"

        # print "ref_equation = ",equationRefs



        if selected_spRefs:
            # on enregistre quelques informations pour affichage par la suite

            ds['metadatas']['references_sp_list'] = refsFitSpectrums

        # ===== on compile l'equation XML et reference =========================

        equation = equationXML + equationRefs

        print("equation apres concatenation:")
        print(equation)


        # ====================================================================#
        # On prepare le fit                                                   #
        # =====================================================================#

        params = Parameters()

        for idx, c_name in enumerate(coeffs_names):
            # value_init = 0.5*(coeffs_bounds[idx][1] - coeffs_bounds[idx][0])

            value_init = 1. / len(coeffs_names)

            params.add(name = c_name.replace("[", "").replace("]", ""),
                       value = value_init,
                       #                       min  = coeffs_bounds[idx][0],
                       #                       max  = coeffs_bounds[idx][1]
                       )

        # =====================================================================#
        # On prepare les données                                              #
        # =====================================================================#

        ds = self.mcData.datasets.getDataset()

        W = ds["W"]

        groups = ds["groups"]

        currentGroup = self.bl.groups.getCurrentGroup()

        # ==================================================================
        # conteneurs pour l'enregistrement des resultats
        # ==================================================================
        parameters_values = [[0 for c in coeffs_names] for i in range(ds["size"])]


        # ======================================================================
        #  Essai sur les projections
        # ======================================================================

        if use_projection:

            info_fit_txt = ''

            projection_name = self.gui.projections.getProjectionNameInGui()

            if not projection_name:
                print("no projection available")

                return

            # ======Affichage GUI de parametrage du fit===========================

            coeffs_bounds, coeffs_isNormalized, cancel = self.getCoeffsBoundsFromGUI(
                    coeffs_names = [match_names[coeff_name] for coeff_name in coeffs_names],
                    verbose = False)

            if cancel:
                mc_logging.debug("user cancel Projection fit request (after gui)")

                return

            projection = ds["projections"][projection_name]

            # pour test seulement,

            # TODO, prendre ceux selectionnés dans une liste de la GUI

            # projection["vectors_names_selected"] = ["mean_data","PC0","PC1","PC2","PC3","PC4","PC5","PC6"]

            v_names = projection["vectors_names_selected"]

            vectors_nb = len(v_names)

            print("model_nb:", model_nb)
            print("vectors_nb:", vectors_nb)

            # ==== Creation de la matrice de passage de l'espace ===============

            # ===== de projection (ex: PCA) à celui des references =============

            Mpr = np.zeros((vectors_nb, model_nb))

            pl.figure()  # pour test affichage des fit des PCs

            fit_values = None  # on declare ici pour avoir acces aux noms des coeff en dehors de la boucle

            # ==== on fit tous les vecteurs de la base de projection  ====

            for i, v_name in enumerate(v_names):

                print('fitting "%s" vector' % (v_name,))

                X = projection["vectors"][v_name]

                fit_values, lmfit = self.fitData(W[:], X[:],
                                                 params,
                                                 equation,
                                                 verbose = False,
                                                 refs = refsFitSpectrums,
                                                 method = self.fit_method_id[fit_method])

                for key, value in fit_values.items():

                    idx = int(key.split("coeff")[1])

                    print("pcfit coeff[%d]:%.6f (%s)" % (idx, value, match_names["coeff[%d]" % (idx)]))

                    if idx < model_nb:
                        Mpr[i, idx] = value

                # ============================================================
                # Temporaire: Tracé des fits dans une fenetre annexe (matplotlib)
                # ============================================================

                if i < 8:

                    x = W

                    coeff = [0 for k in range(len(fit_values))]

                    for key, value in fit_values.items():
                        idx = int(key.split("coeff")[1])

                        coeff[idx] = value

                    refs = refsFitSpectrums

                    fitted = eval(equation)

                    pl.subplot(2, 4, i + 1)
                    pl.title(v_name)
                    pl.plot(W, X, W, fitted, W, lmfit.residual)

                    info_fit_txt = info_fit_txt + "\t- for '%s' chi-square:%.3f,reduced chi-square:%.3f" % (

                        v_name, lmfit.chisqr, lmfit.redchi) + "\n"

            pl.show()

            QtWidgets.QMessageBox.information(self.mainWindow, 'Fit result', info_fit_txt)

            # ============================================================
            # partie test à supprimer=====================================
            # ============================================================

            print("Matrice de passage de la base de projection à celle du fit:")

            print(Mpr)

            print("Mpr shape", Mpr.shape)

            # projection des coefficients "projection" sur la base du fit
            # on vas creer des images pour les models selectionnés
            # on creera ensuite des images à pars pour les coefficients "internes"
            # aux modèles, qui ne doivent pas être projetés car pas forcement lineaire(???)

            selected_vectors_idxs = [projection["vectors_names"].index(s) for s in projection["vectors_names_selected"]]

            # print "selected_index:",selected_vectors_idxsself.updateDisplayedSpectrumsInExplorerWidgets()



            pr_values = projection["values"][:, selected_vectors_idxs]

            # print "pr_values:",pr_values

            # equ_dict = dict() #pour le dictionnaire des coefficients pour "equation"



            # TODO
            # les vecteurs de la base de projection pour le dictionnaire
            # les valeurs projectés sur ces vecteurs

            vmatrix = np.zeros((ds["size"], model_nb))

            coeffs_names = []

            for i, model in enumerate(models):

                print("model.name", model.name)

                values = np.zeros(ds["size"])

                for j in range(ds["size"]):
                    a = sum([np.dot(Mpr[:, i], pr_values[j, :])])

                    values[j] += a

                coeffs_names.append(model.name)

                vmatrix[:, i] = values

            # ==================================================================
            #               Pour essai, on normalise
            # ==================================================================

            try:

                for j in range(vmatrix.shape[0]):


                    vmatrix[j, coeffs_isNormalized] = vmatrix[j, coeffs_isNormalized] + abs(
                            min(vmatrix[j, coeffs_isNormalized]))  # on remet tout >0

                    sum_coeffs = 1.0 * sum(vmatrix[j, coeffs_isNormalized])

                    # print "sum:", sum_coeffs

                    vmatrix[j, coeffs_isNormalized] = vmatrix[j, coeffs_isNormalized] / sum_coeffs

                np.nan_to_num(vmatrix)
                vmatrix[np.isinf(vmatrix)] = 0
                vmatrix[np.isnan(vmatrix)] = 0

            except Exception as e:
                print("exeption during normalisation...")
                print(e)

            # ==================================================================
            # ==================================================================

            # par faciliter pour reouverture dans programme de comparaison annexe
            # TODO: a ranger plus proprement

            ds["coeffs_matrix"] = vmatrix
            ds["coeffs_names"] = np.array(coeffs_names, dtype=np.str)



            # ====== on prepare l'insertion dans le dictionnaire des fits ======
            # TODO: a verifier, il n'est pas possible d'obtenir l'equation du fit avec cette methode
            # de fit sur PCA, mais seulement les coefficients principaux (a,b,c de a*ref1+b*ref2...)
            # les coefficients "internes" n'etant pas lineaires et variant avec chaque PC

            insertFit = True

            insertRepresentation = True

            # ============quelques preparatifs==================================

            for spectrum_index in range(ds["size"]):
                parameters_values[spectrum_index] = vmatrix[spectrum_index, :].tolist()


            print("iciiiiiiiiiiiiiiiiiiiiiiiiiiiii parameters_values")
            print(parameters_values)

            parameters_names = ["coeff[%d]" % (i,) for i in range(len(list(fit_values.keys())))]

            parameters_names_alias = [model.name for j, model in enumerate(models)]

            if insertFit:
                self.insertFitInDatasetDict(fit_name = "fit based on %s" % (projection_name,),
                                            # on peux changer/incrementer le nom du fit ici
                                            equation = "",
                                            parameters_names = parameters_names,
                                            parameters_names_alias = parameters_names_alias,
                                            parameters_values = parameters_values,
                                            create_representation = False
                                            )

            if insertRepresentation:

                # print parameters_names_alias

                for i, pna in enumerate(parameters_names_alias):
                    values = np.array(parameters_values)

                    # print "values.shape()",values.shape

                    values[values == -np.inf] = 0
                    values[values == +np.inf] = 0

                    image = self.bl.representations.getImageFromValues(values[:, i])

                    self.gui.representations.insertRepresentationInDatasetDict("fit on PCA", pna, image)

            return  # Fin du fit su PCA


        # ======================================================================
        # =============== sur les spectres directement =========================
        # ======================================================================

        else:

            # ==================================================================
            #    On demande les bornes + normalisation par GUI               ==
            # ==================================================================

            cancel = False

            if self.isFitThreadRunning():
                cancel = self.bl.threading.askForProcessThreadCanceling()

            else:
                self.bl.threading.setProcessingThreadFlag(self.bl.threading.states.RESET)

            if cancel:
                mc_logging.debug("user cancel fit request")

                return

            # ======Affichage GUI de parametrage du fit===========================

            c_names = [match_names[coeff_name] for coeff_name in coeffs_names]

            coeffs_bounds, coeffs_isNormalized, cancel = self.getCoeffsBoundsFromGUI(coeffs_names = c_names,
                                                                                     verbose = False)

            if cancel:
                mc_logging.debug("user cancel fit request (after gui)")
                return

            # ==================================================================
            #    on definit les spectres a fitter
            # ==================================================================

            spectrums_to_fit = []  # conteneur pour les indices des spectres à fitter

            if fit_mode == "current spectrum":
                print("fitting spectrum", current_index)
                spectrums_to_fit = [current_index]

            elif fit_mode == "whole dataset":
                print("fitting entire dataset...")
                spectrums_to_fit = list(range(ds["size"]))

            elif fit_mode == "current selection group":
                if not currentGroup or currentGroup not in ds["groups"]:
                    QtWidgets.QMessageBox.information(self.mainWindow, "Can't launch fit",
                                                      "Please select a valid group for group fitting or change fit options")

                    return

                print("fitting selected group...")

                spectrums_to_fit = ds["groups"][currentGroup]["indexes"]

            # ==================================================================
            #     Calcul des valeurs initiales pour le Fit
            # ==================================================================

            coeffs_init_based_on_mean_data = False

            if coeffs_init_based_on_mean_data:
                # =============================================================
                #     Based on mean data
                # =============================================================

                if self.gui.spectrums.useNormalizedData:
                    X = self.gui.datasets.getDataset_MeanDatas_normalized()

                else:
                    X = ds["mean_datas"]

                fit_values, _ = self.fitData(W[:], X[:],
                                             params,
                                             equation,
                                             refs = refsFitSpectrums,
                                             method = self.fit_method_id[fit_method], verbose=True)

                coeff = [0 for fv in fit_values]

                coeffs_init = [0 for fv in fit_values]

                for key, value in fit_values.items():
                    idx = int(key.split("coeff")[1])

                    coeff[idx] = value

                coeffs_init = coeff

                print("coeffs init based on mean data:", coeffs_init)

            # =============================================================
            #     equiprobables
            # =============================================================

            else:
                coeffs_init = [1. / len(params) for _ in params]
                print("coeffs init equiprobables", coeffs_init)

            # ==================================================================
            #     boucle de fit et affichage lancés dans un thread            =
            # ==================================================================

            self.fitRunning = True

            myThread = Thread(target=self.fitThread, args=(ds,
                                                           spectrums_to_fit,
                                                           equation,
                                                           coeffs_names,
                                                           match_names,
                                                           coeffs_init,
                                                           coeffs_bounds,
                                                           refsFitSpectrums,
                                                           fit_method,
                                                           coeffs_isNormalized,
                                                           self.bl.threading.processingThreadStopEvent,
                                                           self.bl.threading.processingThreadFinishedEvent))

            myThread.daemon = True
            myThread.start()


    def getSelectedSpectrumsRefsNames_forFit(self):
        p = self.menu_item
        return [str(p.list_spectrumRefs.item(i.row()).text()) for i in p.list_spectrumRefs.selectedIndexes()]

    def getSelectedModelsNames_forFit(self):
        p = self.menu_item
        return [str(p.list_XMLModels.item(i.row()).text()) for i in p.list_XMLModels.selectedIndexes()]


    def loadDataModels(self):

        print("inside loadDataModels")

        # p  = self.gui.panel

        ds = self.mcData.datasets.getDataset()

        importer = DatasetsImporter(workFile = self.bl.io.workFile)

        # Choix des fichiers
        filenames = QFileDialog.getOpenFileNames(self.mainWindow, "Open Dataset File...")[0] #liste des path dans getOpenFileNames[0
        #filenames = [str(name) for name in fn]

        data_refs_container = dict()

        print("filenames",filenames)
        if not filenames:
            print("no file specified")
            return


        else:
            pl.figure()
            pl.title("Loaded references")

            for filename in filenames:
                print("filename:",filename)
                try:
                    spectrums, W, xys, args = importer.loadFile(filename, qt_mode = True)
                    #W = self.mcData.datasets.py.getNumericVersionOfW(ds_name)

                except IOError as e:
                    print(("Error: Can't open", filename))
                    print(e)
                    return

                if len(spectrums) != 1:
                    QtWidgets.QMessageBox.warning(self.mainWindow, "Error", "Reference data must have only one spectrum by file")
                    return

                # il faut adapter les W, on interpole si differents
                # print "Wref:",W
                # print "W_dataset",ds["W"]

                try:
                    f = interp1d(W, spectrums[0], kind='linear')
                    interpolated_spectrum = f(ds["W"])

                except Exception as e:
                    print("Error: Can't interpolate data")
                    print(e)
                    QtWidgets.QMessageBox.warning(self.mainWindow, "Error",
                                                  "Can't interpolate data, reference spectral range [%.2f,%.2f] must contain [%.2f,%.2f]" % (
                                                  W[0], W[-1], ds["W"][0], ds["W"][-1]))

                    return


                pl.plot(W, spectrums[0])
                pl.plot(ds["W"], interpolated_spectrum)
                print("filename:", filename)
                data_refs_container[filename.split("\\")[-1]] = interpolated_spectrum

            self.updateRefsForHybridFit("add", spectrums = data_refs_container)


    def insertFitInDatasetDict(self, fit_name, equation, parameters_names, parameters_names_alias, parameters_values,
                               lmfits_list = None, parameters_values_normalized = None, create_representation = True):

        """
        inserting a fit in ds["fits"] dictionnary

        f = ds["fits"][name]

        f["equations"]  = str()   : str contenant l'equation utilisé pour fitter les données, sous forme de texte à evaluer (fonction eval())
        f["parameters"] = dict()  : dictionnaire contenant les noms et les valeurs des variables contenues dans les equations
        f["parameters"]["names"] = list()           : list contenant le nom des variables, telles qu'elles apparaissent dans l'expresion litterales des equations ( ex: "coeff[0]", "coeff[9]"...)
        f["parameters"]["names_alias"] = list()     : list contenant le nom des variables plus "explicites" ( ex: ["akaganeite", "2eme pic goethite"...])
        f["parameters"]["values"] = list()          : liste de taille ds["size"], contenant des listes de tailles len(f["parameters"]["names"])

        """
        ds_name = self.mcData.datasets.currentDatasetName

        ds = self.mcData.datasets.getDataset(ds_name)

        print("inserting fit in dataset dict...")

        fit = dict()
        fit["equation"] = equation
        fit["parameters"] = dict()
        fit["parameters"]["names"] = parameters_names
        fit["parameters"]["names_alias"] = parameters_names_alias
        fit["parameters"]["values"] = np.array(parameters_values)

        if parameters_values_normalized:
            fit["parameters"]["values_normalized"] = parameters_values_normalized

        ds["fits"][fit_name] = fit

        # ========= On met a jour l'affichage de la GUI =======================#
        self.signal_updateFitsList.emit()

        # =================================================================
        #   Creation des representations
        # ==================================================================

        if create_representation:

            # ==================================================================
            #   Creation des representations de chaque coefficient
            # ==================================================================

            mc_logging.debug("creating representation from coeffs")

            last_repr = len(parameters_names_alias) - 1

            for i, pna in enumerate(parameters_names_alias):

                values = np.array(parameters_values)

                # values[values == -np.inf] = 0
                # values[values == +np.inf] = 0

                image = self.bl.representations.getImageFromValues(values[:, i])

                self.gui.representations.insertRepresentationInDatasetDict(fit_name, pna, image)

                # ==================================================================

                if parameters_values_normalized:
                    values_normalized = np.array(parameters_values_normalized)

                    image = self.bl.representations.getImageFromValues(values_normalized[:, i])

                    self.gui.representations.insertRepresentationInDatasetDict(fit_name + " (normalized)", pna, image)

            # Et on demande l'update de l'affichage

            self.gui.representations.signal_updateRepresentationsFamilyList.emit()
            self.gui.representations.signal_updateRepresentationDisplay.emit(fit_name, pna, True)

        print("done!")


    def updateFitsList(self):

        print("inside updateFitsList")

        p = self.gui.main.panel

        ds_name = self.mcData.datasets.currentDatasetName
        ds = self.mcData.datasets.getDataset(ds_name)

        s = p.combo_equations
        s.clear()

        items = [pr_name for pr_name in list(ds["fits"].keys())]

        s.addItems(items)

    def updateSpectrumsRefsList(self):

        print("inside updateSpectrumsRefsList")

        p = self.menu_item

        dsReferences = self.getReferencesSpectrums()

        # TODO: fusionner avec la list_XML_Models?

        list_items = []

        for ref_name, sp_idx in dsReferences.items():
            list_items.append(ref_name)

        #print("spectrums list_items:",list_items)

        p.list_spectrumRefs.clear()
        p.list_spectrumRefs.addItems(list_items)

        # Menu pour affichage de la ref au click droit

        p.list_spectrumRefs.contextMenuEvent = self.contextMenuRefSpectrums_event

    def contextMenuRefSpectrums_event(self, event):
        """
        Methode appellée lors du click droit dans la liste des references
        Cette methode creer les elements du menus et associe une action
        """

        print("contextMenuRefSpectrums_event")

        p = self.menu_item

        widget = p.list_spectrumRefs

        menu = QtWidgets.QMenu(self.mainWindow)

        index = widget.indexAt(event.pos())

        clicked_item = widget.itemFromIndex(index)

        ref_name = str(clicked_item.text())

        menu_item = menu.addAction("Display Plot...")

        menu_item.triggered.connect(partial(self.contextMenuRefSpectrums_showRef, ref_name = ref_name))

        parentPosition = widget.mapToGlobal(QtCore.QPoint(0, 0))

        menu.move(parentPosition + event.pos())

        menu.show()

        mc_logging.debug("context menus, right click on %s" % (ref_name,))

    def contextMenuRefSpectrums_showRef(self, ref_name):

        ds = self.mcData.datasets.getDataset()

        # TODO: faire plus propre

        dsReferences = self.getReferencesSpectrums()

        pl.figure("Reference spectrums")

        pl.xlabel(ds["x_unit"])
        pl.ylabel(ds["y_unit"])

        pl.title('References')

        print("min(dsReferences[ref_name]):", min(dsReferences[ref_name]))
        print("max(dsReferences[ref_name]):", max(dsReferences[ref_name]))

        pl.plot(ds["W"], dsReferences[ref_name], label=ref_name)
        pl.legend(loc = 'upper right')
        pl.show()

    # ============================================================================
    #    Methodes specifiques à l'affichages des spectres
    # ============================================================================

    def getReferencesSpectrums(self):
        """
        Renvoi un dictionnaire contenant les spectres de references du ds en cour
        TODO: ranger ça plus proprement dans le hdf5
        """
        ds = self.mcData.datasets.getDataset()
        return ds["metadatas"].get("references_sp", dict())


    def processFit_results(self, parameters_values, coeffs_isNormalized, equation, match_names, lmfits_list):
        """
        Cette methode se charge de:

        - Normaliser les parametres si besoin
        - Mettre en forme les resultats du fit pour les inserer dans le jdd
        - Inserer les resltats dans le dictionnaire dataset

        """

        ds = self.mcData.datasets.getDataset()

        params_nb = len(parameters_values[0])

        parameters_names = ["coeff[%d]" % (i,) for i in range(params_nb)]

        # parameters_names_alias = [model.name for j,model in enumerate(models)]

        parameters_names_alias = [match_names[coeff_name] for coeff_name in parameters_names]

        # ==================================================================
        #   On ajoute les valeurs pour Chi² et reduced Chi²
        # ==================================================================

        print('parameters_values before :', parameters_values[0])

        if lmfits_list:

            mc_logging.debug("creating ChiSquare entries")

            assert (len(lmfits_list) == len(parameters_values))

            for i, lmfit in enumerate(lmfits_list):

                if lmfit:
                    chisqr, redchi = lmfit.chisqr, lmfit.redchi

                else:
                    chisqr, redchi = np.nan, np.nan  # chisqr,redchi = 0,0

                parameters_values[i] = parameters_values[i] + [chisqr, redchi]

            parameters_names = parameters_names + ["Chi2", "Reduced_Chi2"]

            parameters_names_alias = parameters_names_alias + ["Chi2", "redChi2"]

        print('parameters_values after :', parameters_values[0])

        # ==================================================================
        # ==================================================================




        mc_logging.debug("parameters_names: %s " % (parameters_names,))
        mc_logging.debug("parameters_names_alias: %s " % (parameters_names_alias,))

        # ======================================================================
        # on normalise les parameters en fonction de ce qui a ete demande dans la GUI
        # ======================================================================

        indexes_of_params_to_normalize = [i for i, isNormalized in enumerate(coeffs_isNormalized) if

                                          isNormalized == True]

        parameters_values_array = np.array(parameters_values)

        parameters_values_normalized = [0 for i in parameters_values]

        for k in range(len(parameters_values)):
            sum_coeffs = 1.0 * sum(parameters_values_array[k, indexes_of_params_to_normalize])

            # if k==self.currentIdx: print "sum:", sum_coeffs:

            parameters_values_array[k, indexes_of_params_to_normalize] = 1.0 * parameters_values_array[k, indexes_of_params_to_normalize] / sum_coeffs

            # if k==self.currentIdx: print "old parameters_values:",parameters_values[k]

            parameters_values_normalized[k] = parameters_values_array[k].tolist()

            # if k==self.currentIdx: print "new parameters_values",parameters_values[k]

        # s'il n'y avait aucun element dans la liste, on met la liste a None

        if not indexes_of_params_to_normalize: parameters_values_normalized = None

        # ======= sauvegarde dans le dictionnaire des fits =================

        self.insertFitInDatasetDict(fit_name = "least squares",  # on peux changer/incrementer le nom du fit ici
                                    equation = equation,
                                    parameters_names = parameters_names,
                                    parameters_names_alias = parameters_names_alias,
                                    parameters_values = parameters_values,
                                    parameters_values_normalized = parameters_values_normalized,
                                    lmfits_list = lmfits_list
                                    )

        # ======================================================================
        #          sauvegarde dans le dictionnaire des projections (TODO)
        # ======================================================================

        parameters_names = ["coeff[%d]" % (i,) for i in range(params_nb)]

        parameters_names_alias = [match_names[coeff_name] for coeff_name in parameters_names]

        if 0:
            vectors = []
            x = ds["W"]

            # on cree la variable refs (fit sur spectres du ds) si present

            try:
                refs = ds['metadatas']['references_sp_list']  # on s'en sert dans eval(equation)

            except KeyError as e:
                pass

            # if len(modelNames) == len(coeffs_names):

            pl.figure()

            for i, parameter_names in enumerate(parameters_names):
                coeff = [0 for j in range(params_nb)]
                coeff[i] = 1
                print("equation\n", equation)
                ref = eval(equation)
                vectors.append(ref)
                pl.plot(x, ref, label=parameters_names_alias[i])

            pl.legend()
            pl.show()



    def launchFitLoop(self, ds, spectrums_to_fit, equation, coeffs_names, coeff_init, coeffs_bounds,
                      coeffs_isNormalized, refsFitSpectrums, fit_method, stop_event, finished_event):
        """
        Cette boucle est lancée par le thread de fit.
        Idelaement on utiliserais le multithreading ou multiprocessing mais la methode
        "minimize" de lmfit semble ne pas etre compatible
        On a quand meme creer une fonction fitThreadUnit compatible avec les "queue" du module multithreading
        mais on utilise qu'un seul thread (donc pas de multithread!) et en plus on lock a l'appel de minimize dans
        fitThreadUnit (ne serait pas nescessaire si minimize etait thread-safe)
        """
        # ==================================================================
        # conteneurs pour l'enregistrement des resultats
        # ==================================================================
        parameters_values = [[0 for c in coeffs_names] for i in range(ds["size"])]
        lmfits_list = [None for i in range(ds["size"])]

        # ==================================================================

        t0 = time.clock()

        use_multithread = False

        #        if use_multithread:
        #            #TODO: regler probleme de fonctionnement ou supprimer
        #            #=====on rempli la queue(liste des spectres à traiter)=================
        #            num_threads = 1
        #            queue = Queue.Queue()
        #            for spectrum_index in spectrums_to_fit:
        #                queue.put(spectrum_index)
        #
        #            #=========on demare N threads de traitement============================
        #            for i in range(num_threads):
        #                #version thread
        #                t = threading.Thread(target = self.fitUnit_threadVersion, args = (ds, spectrums_to_fit, equation, coeffs_names, coeff_init, coeffs_bounds, coeffs_isNormalized, refsFitSpectrums, fit_method, stop_event, finished_event, parameters_values, queue,))
        #                t.deamon = True
        #                t.start()
        #
        #            #============on attend que toutes les taches soit traitées=============
        #            print "Waiting for all queue to be processed!"
        #            nb_sp_to_fit = len(spectrums_to_fit)
        #            while not queue.empty():
        #                qs = queue.qsize()
        #                self.emit(SIGNAL("updateProgress"),100.0*(nb_sp_to_fit - qs)/nb_sp_to_fit)
        #                time.sleep(0.001)
        #
        #            #queue.join() #normalement a enlever
        #            print "all queue processed!"
        #

        if 1:
            print("coeff_init:", coeff_init)

            self.fitUnit(ds, spectrums_to_fit, equation, coeffs_names, coeff_init, coeffs_bounds, coeffs_isNormalized,
                         refsFitSpectrums, fit_method, stop_event, finished_event, parameters_values, lmfits_list)

        self.gui.main.signal_updateProgress.emit(-1)
        mc_logging.info("fitting done! %d spectrum(s)" % (len(spectrums_to_fit)))

        self.bl.threading.setProcessingThreadFlag(self.bl.threading.states.FINISHED)

        mc_logging.info("Total fit duration for %d spectrums: %.2f" % (time.clock() - t0, len(spectrums_to_fit)))

        return parameters_values, lmfits_list


    def fitThread(self, ds, spectrums_to_fit, equation, coeffs_names, match_names, coeff_init, coeffs_bounds,
                  refsFitSpectrums, fit_method, coeffs_isNormalized, stop_event, finished_event):

        """
        Thread lancé lorseque l'on demande le fit du spectre/groupe/dataset
        Ce dernier se charge de lancer la boucle de fit
        """

        parameters_values, lmfits_list = self.launchFitLoop(ds,
                                                            spectrums_to_fit,
                                                            equation,
                                                            coeffs_names,
                                                            coeff_init,
                                                            coeffs_bounds,
                                                            coeffs_isNormalized,
                                                            refsFitSpectrums,
                                                            fit_method,
                                                            stop_event,
                                                            finished_event)

        # on indique que le fit n'est plus en cour

        self.fitRunning = False

        if not stop_event.is_set():
            # self.lock.acquire() #necessaire?

            self.processFit_results(parameters_values,
                                    coeffs_isNormalized,
                                    equation,
                                    match_names,
                                    lmfits_list)

            self.gui.signals.signal_spectrumsToDisplayChanged.emit([])
            # self.lock.release()#necessaire?


    def isFitThreadRunning(self):
        return getattr(self, 'fitRunning', False) and not self.bl.threading.processingThreadFinishedEvent.is_set()


    def getCoeffsBoundsFromGUI(self, coeffs_names, example_values = None, verbose = True):
        """
        demande à l'utilisateur quelles bornes utilisées pour les coeffs
        donne en example les valeurs dans exampleValues si specifiées
        """

        d = uic.loadUi("assets//ui_files//parameters_bounds_input.ui")

        d.setWindowTitle("Please enter parameters bounds")

        coeffs_bounds = []
        coeffs_isNormalized = []

        # Charge les valeurs precedentes si disponibles precedentes en memoire
        previous_values = getattr(self, '_fit_gui_params_previous_values', dict())

        # ==================== On rempli la gui ================================

        scrollArea = d.scrollArea

        scrollAreaLayout = QtWidgets.QVBoxLayout(scrollArea)
        scrollAreaLayout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)

        coeffs_widgets = [QtWidgets.QWidget() for c in coeffs_names]

        for i, coeff_name in enumerate(coeffs_names):

            sizer = QtWidgets.QHBoxLayout()

            nl = QtWidgets.QLabel(coeff_name)
            nl.setMinimumWidth(150)

            al = QtWidgets.QLabel("min:")

            ai = QtWidgets.QLineEdit()
            ai.setObjectName("min_%i" % (i,))

            bl = QtWidgets.QLabel("max:")

            bi = QtWidgets.QLineEdit()
            bi.setObjectName("max_%i" % (i,))

            cc = QtWidgets.QCheckBox("normalize")
            cc.setObjectName("normalize_%i" % (i,))

            # on prerempli si possible avec les valeurs precedements donnees par l'utilisateur

            if coeff_name in previous_values:

                pv = previous_values[coeff_name]

                # print "pv:",pv

                if pv[0] is not None: ai.setText(str(pv[0]))
                if pv[1] is not None: bi.setText(str(pv[1]))

                cc.setChecked(bool(pv[2]))

            for w in (nl, al, ai, bl, bi, cc):
                w.setMinimumHeight(25)
                sizer.addWidget(w)

            coeffs_widgets[i].setLayout(sizer)
            scrollAreaLayout.addWidget(coeffs_widgets[i])

            # scrollAreaLayout.addSpacing(50)

        ok = d.exec_()

        # ============= On recupere les donnÃ©es de la gui =====================

        # ======================================================================

        if ok:

            for i, name in enumerate(coeffs_names):
                min_raw = d.findChild(QtWidgets.QLineEdit, "min_%d" % (i,)).text()
                max_raw = d.findChild(QtWidgets.QLineEdit, "max_%d" % (i,)).text()
                normalize = d.findChild(QtWidgets.QCheckBox, "normalize_%d" % (i,)).isChecked()

                try:
                    min_value = float(min_raw)

                except ValueError as e:
                    min_value = None

                try:
                    max_value = float(max_raw)

                except ValueError as e:
                    max_value = None

                if min_value == max_value:
                    min_value = max_value = None

                coeffs_isNormalized.append(normalize)
                coeffs_bounds.append((min_value, max_value))



        else:
            return [(None, None) for i in coeffs_names], [False for i in coeffs_names], True

        # ======================================================================

        # ======================================================================
        if verbose:
            print("Values of coeffs_bounds and coeffs_isNormalized from GUI:")
            print(coeffs_bounds, "\n", coeffs_isNormalized)
        # ======================================================================

        # On garde les valeurs actuelles en memoire pour preremplir au prochain appel
        current_values = dict()

        for i, name in enumerate(coeffs_names):
            current_values[name] = (coeffs_bounds[i][0], coeffs_bounds[i][1], coeffs_isNormalized[i])

        self._fit_gui_params_previous_values = current_values
        # ======================================================================


        return coeffs_bounds, coeffs_isNormalized, False

    def fitData(self, x, y, params, equation, refs = [], verbose = True, method = 'leastsq'):

        if verbose:
            print("fitting data")

        t0 = time.clock()

        # lmfit = minimize(self.residualslmfit, params, args=(y, x, equation),method=method)

        lmfit = minimize(self.residualslmfit, params, args=(y[:], x[:], equation, refs), method=method)

        if verbose:

            mc_logging.debug("Ellapsed for lmfit: %.2fs" % ((time.clock() - t0)))

            try:
                #probleme avec report_errors
                print(params)
                #print(report_errors(params))

            except Exception as e:
                print("exception during report")

        # ci = lmfit.conf_interval()
        return lmfit.params, lmfit #06/12/2047, changement dans lmfit
        #return lmfit.values, lmfit

    def residualslmfit(self, parameters, y, x, equation, refs = []):

        coeff = list()

        for key, value in parameters.valuesdict().items():
            # print "key,value:",key,value

            coeff.append(value)

        # print "coeff:", coeff

        err = y - eval(equation)

        return err

    def updateRefsForHybridFit(self, add_or_remove, spectrums = dict()):
        """
        if spectrums is empy, current selected spectrum is added to references
        dictionnary
        else all entries of spectrums are added
        """

        print("inside updateRefsForHybridFit")

        p = self.menu_item

        ds = self.mcData.datasets.getDataset()

        currentIdx = self.mcData.currentSpectrumIndex

        # TODO: faire plus propre

        dsReferences = ds["metadatas"].get("references_sp", dict())

        # ======================================================================
        # ajout d'un spectre en tant que reference, on demande un nom ou
        # on en creer un par defaut
        # ======================================================================

        if add_or_remove == "add":

            if not spectrums:

                print("Adding current selected spectrum (sp.%s) to reference list" % (currentIdx,))

                default_name = "sp%d" % (currentIdx,)

                ref_name, ok = QtWidgets.QInputDialog.getText(self.mainWindow,
                                                              "Reference Name input...",
                                                              "Choose a name:",
                                                              QtWidgets.QLineEdit.Normal,
                                                              default_name)

                if ok:
                    print("spectrum %d now known as '%s'" % (currentIdx, ref_name,))

                else:
                    return

                # on ajoute au dictionnaire des references

                if not self.gui.spectrums.useNormalizedData:
                    dsReferences[str(ref_name)] = ds["X"][currentIdx]

                else:
                    dsReferences[str(ref_name)] = self.gui.datasets.getDataset_X_normalized()[currentIdx]

            else:
                for ref_name, spectrum in list(spectrums.items()):
                    dsReferences[ref_name] = spectrum



        # ======================================================================
        # suppression d'une des references
        # ======================================================================

        elif add_or_remove == "remove":

            selected_spRefs = [str(p.list_spectrumRefs.item(i.row()).text()) for i in
                               p.list_spectrumRefs.selectedIndexes()]

            for ref_name in selected_spRefs:

                print("Removing '%s' from reference list" % (ref_name,))

                if ref_name in dsReferences: del dsReferences[ref_name]

        # ======================================================================
        # Mise à jour de la liste des references en metadatas
        # ======================================================================
        ds["metadatas"]["references_sp"] = dsReferences

        # =====================================================================
        # Mise à jour de la liste des references dans l'affichage
        # =====================================================================
        self.signal_updateSpectrumsRefsList.emit()

    # @my_pyqtSlot()



    def fitUnit(self, ds, spectrums_to_fit, equation, coeffs_names, coeff_init, coeffs_bounds, coeffs_isNormalized,
                refsFitSpectrums, fit_method, stop_event, finished_event, parameters_values, lmfits_list):

        nb_sp_to_fit = len(spectrums_to_fit)

        # ============Pour la normalisation====================
        if coeffs_isNormalized.count(True) >= 2:
            indexes_of_params_to_normalize = [idx for idx, is_normalized in enumerate(coeffs_isNormalized) if is_normalized]

        else:
            indexes_of_params_to_normalize = []

        # ==========================================================

        for i, spectrum_index in enumerate(spectrums_to_fit):

            # Ämc_logging.debug("fitting spectrum %d/%d" % (i, nb_sp_to_fit))
            if stop_event.is_set(): return

            if self.gui.spectrums.useNormalizedData:
                X = self.gui.datasets.getDataset_X_normalized()[spectrum_index]

            else:
                X = ds["X"][spectrum_index]

            W = ds["W"]

            # =================================================================
            # On remet à zero les valeurs precedement trouvéees pour les parametres
            # =================================================================
            params = Parameters()

            for idx, c_name in enumerate(coeffs_names):

                coeff_idx = int(c_name.split("coeff[")[1].split("]")[0])

                name_wt_brackets = c_name.replace("[", "").replace("]", "")

                # ================= mise au point de l'expression===============
                #               if indexes_of_params_to_normalize:
                #                   expr = '1'
                #                   for coeff_idx_j in indexes_of_params_to_normalize:
                #                       if coeff_idx_j != coeff_idx and (coeff_idx_j==0 or coeff_idx_j==1):
                #                           expr = expr + "-" + "coeff%d" % (coeff_idx_j,)
                #               else:
                #                   expr = ''
                #
                #               print "expr for %s:  %s" % (name_wt_brackets,expr)



                # pas propre, mais semble bugger quand on donne None à min et/ou max

                if coeffs_bounds[idx][0] is not None and coeffs_bounds[idx][1] is not None:
                    params.add(name = name_wt_brackets,
                               value = coeff_init[coeff_idx],
                               min = coeffs_bounds[idx][0],
                               max = coeffs_bounds[idx][1],
                               )

                elif coeffs_bounds[idx][0] is not None:
                    params.add(name = name_wt_brackets,
                               value = coeff_init[coeff_idx],
                               min = coeffs_bounds[idx][0],

                               )

                elif coeffs_bounds[idx][1] is not None:
                    params.add(name = name_wt_brackets,
                               value = coeff_init[coeff_idx],
                               max = coeffs_bounds[idx][1],
                               )

                else:
                    params.add(name = name_wt_brackets,
                               value = coeff_init[coeff_idx])

            # ====================================================================#
            # Et on envoie à la methode de fit                                    #
            # ====================================================================#
            # pour gerer parallelement plusieurs fit voir:
            # https://docs.python.org/2/library/queue.html
            # http://stackoverflow.com/questions/17554046/how-to-let-a-python-thread-finish-gracefully
            # utilisation de Queue, get(), task_done()

            fit_values, lmfit = self.fitData(W[:], X[:],
                                             params,
                                             equation,
                                             refs = refsFitSpectrums,
                                             method = self.fit_method_id[fit_method],
                                             verbose = False)

            # =====================================================================#
            # On garde en memoire les resultats
            # =====================================================================#

            lmfits_list[spectrum_index] = lmfit

            # TODO: pas tres optimisé...

            for key, value in fit_values.items():
                idx = int(key.split("coeff")[1])

                with self.bl.threading.Rlock:
                    parameters_values[spectrum_index][idx] = value

            # ======== Et on affiche le  fit effectué, pendant qu'on y est ============

            # on demande pas trop de mise a jour de l'affichage par seconde, sinon ca bug...

            # print "ellapsed since last_update",time.time() - self.last_update_time

            if (time.time() - self.gui.main.last_update_time) > self.gui.main.limits.min_refresh_delay / 1000.:
                self.gui.signals.signal_spectrumsToDisplayChanged.emit([spectrum_index])
                self.gui.main.signal_updateProgress.emit(100.0 * i / nb_sp_to_fit)
                self.gui.last_update_time = time.time()

            time.sleep(0.0001)  # pour pas bloquer le thread?
