import numpy as np
import qwt as Qwt
from PyQt5.QtCore import QObject

from plotpy.builder import make
from plotpy.interfaces import ICurveItemType
from plotpy.items import LabelItem

from PyQt5.QtGui import QFont, QColor, QBrush

from helpers.data import singleton
from helpers.plots import plots
from presentation.controllers import main, signals, menu, datasets, representations, spectrums, projections

from PyQt5 import QtCore,QtWidgets

import re
from helpers.dialogs import InputDialogText



@singleton
class MCPresentationController_spectrums(QObject):

    #================================================================
    # Display modes
    #================================================================
    DISP_CLICKED = 0
    DISP_ALL_SELECTED = 1
    DISP_SELECTED_AVERAGE = 2

    _displayModeLabels = {DISP_CLICKED: "clicked",
                          DISP_ALL_SELECTED: "all selected",
                          DISP_SELECTED_AVERAGE: "selected average"
                         }
    #================================================================
    # Normalisation methods (non utilisé pour l'instant)
    #================================================================
    NORM_SUM = 0
    NORM_MAX = 1
    NORM_COLUMNS_SUM = 2
    NORM_COLUMNS_MAX = 3
    NORM_COLUMNS_STD = 4
    NORM_INERTIA = 5

    _normalisationMethodsLabels = {NORM_SUM: "sum",
                                   NORM_MAX: "max",
                                   NORM_COLUMNS_SUM: "columns_sum",
                                   NORM_COLUMNS_MAX: "columns_max",
                                   NORM_COLUMNS_STD: "columns_std",
                                   NORM_INERTIA: "inertia"
                                   }


    def __init__(self, qt_panel, mcBusinessLogic, mcData, mainWindow):

        super().__init__()
        print(type(self).__name__ + " initialized (id:{})".format(id(self)))

        self.bl     = mcBusinessLogic
        self.mcData = mcData
        self.panel  = qt_panel
        self.mainWindow = mainWindow

        self.main = main.MCPresentationController_main(qt_panel, mcBusinessLogic, mcData, mainWindow)
        self.signals = signals.MCPresentationController_signals()
        self.menu = menu.MCPresentationController_menu(qt_panel, mcBusinessLogic, mcData, mainWindow)

        #self.spectrums = spectrums.MCPresentationController_spectrums(qt_panel, mcBusinessLogic, mcData, mainWindow)

        self.signals = signals.MCPresentationController_signals()


        # self.view  = mcPresentationView
        # self.model = mcPresentationModel

    def makeConnections(self):
        p = self.panel

        print("inside makeConnections in MCPresentationController_spectrum")

        self.attachSpectrumChooserCallbackOnDoubleClickInExplorerWidgets()

    #============================================================================
    #  Modes d'affichages
    #============================================================================
    @property
    def displayMode(self):
        p = self.panel
        display_mode = p.combo_dispSpectrums.currentIndex()
        return display_mode

    @displayMode.setter
    def displayMode(self, mode):
        p = self.panel
        p.combo_dispSpectrums.setCurrentIndex(mode)

    def getDisplayModes(self):
        return self._displayModeLabels

    @property
    def stdDisplay(self):
        p = self.panel
        std_display = p.combo_std_deviation.currentText()
        return std_display



    #============================================================================
    #  Normalisation TODO: renvoyer un ID plutot qu'un str
    #============================================================================
    @property
    def normalizeMethod(self):
        p = self.panel
        return str(p.combo_normalisation_type.currentText())

    @property
    def useNormalizedData(self):
        p = self.panel
        return p.checkBox_normalizeDatas.isChecked()



    def setDisplayMode(self, display_mode, ds_name, update = False):
        """
        set Display mode in Spectrums Explorers
        """
        p = self.panel

        # on le change dans la combo de la GUI
        index = p.combo_dispSpectrums.findText(display_mode, QtCore.Qt.MatchFixedString)

        if index >= 0:
            p.combo_dispSpectrums.setCurrentIndex(index)
        else:
            print("can't set '%s' spectrum diplay mode")


    def _get_indexes_depending_of_display_mode(self, display_mode, ds_name, spectrum_indexes, autoselect_indexes):

        ds = self.bl.io.getDataset(ds_name)
        groups = ds["groups"]
        group_name = self.bl.groups.getCurrentGroup()

        indexes = []

        if display_mode == self.DISP_CLICKED:

            if autoselect_indexes:
                csi = self.mcData.currentSpectrumIndex

                if csi or csi == 0: indexes = [csi]
                else:               indexes = []

            else:
                if spectrum_indexes:  indexes = spectrum_indexes
                else:                 indexes = []


        elif display_mode == self.DISP_ALL_SELECTED:
            # ==============================================================
            # cas ou on demande d'afficher tous les spectres d'un groupe
            # ==============================================================
            if autoselect_indexes:
                if group_name in groups:
                    group = groups[group_name]
                    indexes = group["indexes"]
            # ===========================================================================
            # cas ou on demande d'afficher tous les spectres dont les indices sont donnés
            # ===========================================================================
            else:
                indexes = spectrum_indexes

        elif display_mode == self.DISP_SELECTED_AVERAGE:

            if autoselect_indexes:
                if group_name in groups:
                    group = groups[group_name]
                    indexes = group["indexes"]
            else:
                indexes = spectrum_indexes

        # else:
        #     indexes = []

        return indexes


    def updateDisplayedSpectrumsInWidgetByDsName(self, widget_ref, ds_name, spectrum_indexes = [], title_prefix = None,
                                                 title_sufix = None, overrided_title = None, autoselect_indexes = False):
        """
        if title_prefix, append at begin of autogenerated title
        if title_suffix, append at the end of autogenerated title
        if title, override autogenerated title
        """

        p  = self.panel
        ds = self.bl.io.getDataset(ds_name)

        # print("autoselect_indexes:", autoselect_indexes)
        # print("spectrum_indexes:", spectrum_indexes)

        # pour eviter de surcharger l'affichage
        # TODO: si >, faire un tirage aleatoire? et mettre dans
        # une variables self.gui_parameters["max_displayed_spectrums"]
        # TODO: mettre ailleur

        MAX_SP_DISP = self.main.limits.max_curves_on_plot

        disp_limited = False  # flag to remind that display had been limited to MAX_SP_DISP

        if self.useNormalizedData:   X = ds["X_normalized"]
        else:                        X = ds["X"]

        #On converti en list si ce n'est pas le cas
        #On met le flag autoselect = true si list vide
        if type(spectrum_indexes) is not list:
            if np.issubdtype(type(spectrum_indexes), int):
                spectrum_indexes = [spectrum_indexes]
        else:
            if not spectrum_indexes: autoselect_indexes = True


        # ======================================================================
        # attention, ici on creer une echelle d'entiers si les W ne sont pas numeriques
        # TODO: creer une echelle avec des valeurs string
        # ======================================================================
        W = self.mcData.datasets.getNumericVersionOfW(ds_name)
        # ======================================================================

        widget = widget_ref

        display_mode = self.displayMode

        # =======================================================================
        # choix des indices des spectres à afficher en fonction du type
        # =======================================================================
        indexes = self._get_indexes_depending_of_display_mode(display_mode,
                                                              ds_name,
                                                              spectrum_indexes,
                                                              autoselect_indexes)

        # ==================================================================
        #
        # ==================================================================
        curvePlot = widget.get_plot()
        title_txt = ""

        # =========suppression des curves ou image existantes====================
        for item in curvePlot.get_items(item_type = ICurveItemType):
            curvePlot.del_item(item)
        # =======================================================================


        # les indices doivents être triées pour utiliser X[indices]
        try:
            indexes = sorted(indexes)
        except TypeError:
            pass


        if display_mode == self.DISP_SELECTED_AVERAGE and indexes:

            # pour l'affichage de la deviation standard
            std_display = self.stdDisplay

            # ===========Creation et attache de la nouvelle curve ===========
            group_mean_spectrum = np.mean(X[indexes], axis = 0)
            group_std_deviation = np.std(X[indexes], axis = 0)

            average_curve = plots.getCurveItem(W, group_mean_spectrum, title = 'average')

            curvePlot.add_item(average_curve)

            if std_display == "sigma":

                sima_curve_plus = plots.getCurveItem(W,
                                                     group_mean_spectrum + group_std_deviation,
                                                     title = 'average + sigma',
                                                     color = "red",
                                                     linestyle = "DashDotLine")

                sima_curve_minus = plots.getCurveItem(W,
                                                      group_mean_spectrum - group_std_deviation,
                                                      title = 'average - sigma',
                                                      color = "red",
                                                      linestyle = "DashDotLine")

                curvePlot.add_item(sima_curve_plus)
                curvePlot.add_item(sima_curve_minus)



            elif std_display == "2*sigma":

                sima_curve_2plus = plots.getCurveItem(W,
                                                      group_mean_spectrum + 2 * group_std_deviation,
                                                      title = 'average + sigma',
                                                      color = "red",
                                                      linestyle = "DashDotLine")

                sima_curve_2minus = plots.getCurveItem(W,
                                                       group_mean_spectrum - 2 * group_std_deviation,
                                                       title = 'average - sigma',
                                                       color = "red",
                                                       linestyle = "DashDotLine")

                curvePlot.add_item(sima_curve_2plus)
                curvePlot.add_item(sima_curve_2minus)

            curvePlot.do_autoscale()
            curvePlot.replot()

            # =====================Titre du graph 1/2============================
            if autoselect_indexes:
                title_txt = 'Average Spectrum (group "%s")' % (self.bl.groups.getCurrentGroup(),)
            else:
                title_txt = 'Average Spectrum (%d spectrums)' % (len(indexes),)
            # ===================================================================

        else:
            # ==============================================================
            # On reduit le nombre de spectres à afficher si besoin
            # ==============================================================
            sp_nb = len(indexes)

            if sp_nb >= MAX_SP_DISP:
                disp_limited = True
                max_i = MAX_SP_DISP

            else:
                max_i = len(indexes)

            indexes = indexes[0:max_i]

            if disp_limited:
                print("display limited to %d spectrums" % (MAX_SP_DISP,))

            # ==============================================================
            # Et on trace toutes les courbes
            # ==============================================================
            #TODO: changer l'affichage si on a plusieurs curve et mode barstick

            for idx in indexes:
                #==========================================================
                # Creation et ajout de la nouvelle curve
                #==========================================================
                curve = plots.getCurveItem(W, X[idx][:], title = "Sp. %d" % (idx,))
                curvePlot.add_item(curve)

                # =====================Titre du graph 1/2========================

                if len(indexes) > 1:
                    title_txt = "Selected Spectrums"

                    if disp_limited:
                        title_txt += " (display limited to %d/%d) " % (MAX_SP_DISP, sp_nb)

                else:
                    original_idx = ds["base_infos"]["original_idxs"][idx]
                    title_txt = 'Spectrum %d' % (idx)

                    if original_idx != idx:
                        title_txt = title_txt + " (original index: %d)" % (original_idx,)

                    self.addFitOverlayOnPlot(curvePlot = curvePlot, ds_name = ds_name)
                    self.addMetadataOverlayOnPlot(curvePlot = curvePlot, ds_name = ds_name, spectrumIndex = idx)

                # ===============================================================
                curvePlot.do_autoscale()
                curvePlot.replot()


        if len(indexes) == 0:
            # Affichage "No Data si aucun index"
            title_txt = "NO DATA"

            empty_curve = make.curve([], [], title = 'no data')
            curvePlot.add_item(empty_curve)

            # curvePlot.do_autoscale()
            curvePlot.replot()

        self.addLabelsOnPlot(curvePlot)


        # ================ Ajout des unitées ===============================
        bottom_axis_id = curvePlot.get_axis_id("bottom")
        left_axis_id   = curvePlot.get_axis_id("left")

        curvePlot.set_axis_unit(bottom_axis_id, ds["x_unit"])
        curvePlot.set_axis_unit(left_axis_id, ds["y_unit"])

        # =========mise en forme du titre en fonction des options===========
        if overrided_title: title_txt = overrided_title
        if title_prefix:    title_txt = title_prefix + title_txt
        if title_sufix:     title_txt = title_txt + title_sufix

        title = Qwt.QwtText(title_txt)

        # =====================Titre du graph 2/2==========================
        title.setFont(QFont('DejaVu', 8, QFont.Light))
        curvePlot.setTitle(title)
        # =================================================================




    def addFitOverlayOnPlot(self, curvePlot, replot = False, ds_name = None):

        p = self.panel

        ds = self.mcData.datasets.getDataset(ds_name)

        spectrumIndex = self.mcData.currentSpectrumIndex

        # print "inside addFitOverlayOnPlot"

        # ==================================================================
        #     En surrimpression du spectre, on affiche, si disponible
        #     le spectre reconstruit à partir de l'equation du fit
        #     en option, on trace egalement le residu et un label avec les
        #     valeurs des parametres de fit
        # ==================================================================
        if "fits" not in ds:   return

        else:
            # TODO: prendre le nom du fit et checker si affichage demander dans la GUI

            display_fit = True

            fit_name = str(p.combo_equations.currentText())

            if display_fit and fit_name and fit_name in ds["fits"]:

                f = ds["fits"][fit_name]

                equation = f["equation"]

                c_names = f["parameters"]["names"]

                c_names_alias = f["parameters"]["names_alias"]

                c_values = f["parameters"]["values"][spectrumIndex]
                print("c_values:")
                print(c_values)

                if equation == "":
                    # print "no equation available for this spectrum"
                    pass

                else:
                    # ==============================================================
                    # on creer les variables contenu dans l'equation et on
                    # remplace les parametres par leurs valeurs numeriques
                    # ==============================================================

                    # print "equation du spectre %d avant remplacement:" % (spectrumIndex)
                    #                    print "len(c_values)",len(c_values)
                    #                    print "len(c_names)",len(c_names)
                    #                    print "c_values:",c_values
                    #                    print "c_names",c_names
                    print("equation avant remplacement:",equation)
                    for i, c_name in enumerate(c_names):
                        print("replacing",c_name,"by",c_values[i])
                        equation = equation.replace(c_name, str(c_values[i]))

                    print("equation du spectre %d apres remplacement:" % (spectrumIndex,))
                    print(equation)

                    #remplacement des coefficients par leurs valeurs
                    # print("coeffs names:",c_names)
                    # print("coeffs names_alias:",c_names_alias)
                    # print("values:",c_values)


                    x = self.mcData.datasets.getNumericVersionOfW(ds_name)

                    # on cree la variable refs (fit sur spectres du ds) si present
                    try:
                        refs = ds['metadatas']['references_sp_list']  # on s'en sert dans eval(equation)

                    except KeyError as e:
                        pass

                    if 1:
                        #print("equation:",equation)
                        fitted = eval(equation)

                        # =======================================================
                        #  On trace la courbe fittée
                        # =======================================================
                        curve_fit = plots.getCurveItem(x, fitted, title = fit_name, color = "green", linestyle = "DashDotLine")
                        curvePlot.add_item(curve_fit)



                    if 0:#except Exception as e:
                        print("Error during equation evaluation")
                        print(e)
                    #                        print fitted
                    #                        print x
                    #                        print e

                if replot: curvePlot.replot()

    def addMetadataOverlayOnPlot(self, curvePlot, replot = False, ds_name = None, spectrumIndex = None):

        p = self.panel

        meta_type = self.menu.display.getMetadataDisplayedMode(ds_name)

        ds = self.mcData.datasets.getDataset(ds_name)

        if spectrumIndex is None:
            spectrumIndex = self.mcData.currentSpectrumIndex

        # print "inside addMetadataOverlayOnPlot"
        #        print meta_type

        label = None

        meta = "<span style='white-space: pre-wrap;'>"

        # print "meta_type",meta_type

        if meta_type == "projection values":

            # ===============construction du label des metadatas===============
            meta = meta + "<b>Projection values</b>:<br/>"

            # TODO: mettre a jour la liste des projections au lieu d'utiliser cette liste de representation

            # current_projection_name = self.gui.projections.getProjectionName()

            current_projection_name = str(p.combo_representations_family.currentText())

            if current_projection_name in ds["projections"]:

                proj = ds["projections"][current_projection_name]

                # print 'p["vectors_names_selected"]',p["vectors_names_selected"]

                for v_name in proj["vectors_names_selected"]:
                    meta = meta + "%s:\t%f<br/>" % (v_name, proj["values_by_vector"][v_name][spectrumIndex])

                meta = meta + "</span>"

                label = make.label(meta, "TR", (-10, 10), "TR", "metadatas")



        elif meta_type == "channel values":

            max_channel_to_disp = 15

            if self.useNormalizedData:
                X = self.datasets.getDataset_X_normalized()

            else:
                X = ds["X"]

            meta = meta + "<b>Channel values:</b>:<br/>"

            for i, channel in enumerate(ds["W"]):

                if i < max_channel_to_disp:
                    meta = meta + "%s:\t%f<br/>" % (channel, X[spectrumIndex][i])

            if len(ds["W"]) > max_channel_to_disp:
                meta = meta + "...<br/>"

            meta = meta + "</span>"

            label = make.label(meta, "TR", (-10, 10), "TR", "metadatas")



        elif "fit results" in meta_type:

            # meta = meta + "<b>Fit results</b>:<br/>"

            fit_name = str(p.combo_equations.currentText())

            if fit_name and fit_name in ds["fits"]:

                f = ds["fits"][fit_name]

                equation = f["equation"]

                c_names = f["parameters"]["names"]

                c_names_alias = f["parameters"]["names_alias"]

                if meta_type == "fit results normalized":

                    meta = meta + "<b>Fit results Normalized</b>:<br/>"

                    if "values_normalized" in f["parameters"]:

                        c_values = f["parameters"]["values_normalized"][spectrumIndex]

                    else:

                        return



                else:

                    meta = meta + "<b>Fit results</b>:<br/>"
                    c_values = f["parameters"]["values"][spectrumIndex]

                if len(c_values) > 0:
                    # =======================================================
                    #  On ajoute les legendes
                    # =======================================================

                    for j, c_name_alias in enumerate(c_names_alias):
                        meta = meta + "%s:\t%f<br/>" % (c_name_alias, c_values[j])

                    meta = meta + "</span>"

                    # ==========================================================

                    label = make.label(meta, "TR", (-10, 10), "TR", "metadatas")

            else:
                # print "No projection defined"
                return

        # ==================================================================
        #    Affichage des metadatas dans la section info
        # ======================================================================

        # ======================================================================
        # On commence par supprimer les metadatas precedentes
        # ======================================================================

        # label.labelparam.move_anchor()

        if label:

            items = [item for item in curvePlot.get_items() if "metadatas" in item.title().text()]

            if items:
                # on sauvegarde la position du precedent labe
                # x,y = items[0].labelparam.xc,items[0].labelparam.yc
                # TODO, bouger à la position sauvegardée
                # print "x,y:",x,y
                # label.labelparam.xc,label.labelparam.yc = x,y
                # print "label.labelparam.xc,label.labelparam.yc",label.labelparam.xc,label.labelparam.yc
                curvePlot.del_items(items)

                # ======================================================================

            # On l'ajoute au curvePlot avec une transparence du fond
            label.bg_brush = QBrush(QColor(255, 255, 255, 150))

            curvePlot.add_item(label)

            if replot: curvePlot.replot()

        else:
            # on supprime un eventuel precedent label
            for item in curvePlot.get_items():
                if isinstance(item, LabelItem): curvePlot.del_item(item)



    def addLabelsOnPlot(self, curvePlot):
        # ================== Ajout des labels si type(W) = str===============
        # Si type W est str, on ajoute des labels
        ds = self.mcData.datasets.getDataset()
        W = ds["W"]

        labelBrush = QBrush(QColor(255, 255, 255, 160))

        for i in range(len(W)):
            if (isinstance(W[i], str)):
                name_label = make.label(W[i], (i, 0), (0, -20), "C")
                name_label.bg_brush = labelBrush
                curvePlot.add_item(name_label)



    def attachSpectrumChooserCallbackOnDoubleClickInExplorerWidgets(self):

        from presentation.controllers import representations, projections

        qt_panel = self.panel
        mcBusinessLogic = self.bl
        mcData = self.mcData
        mainWindow = self.mainWindow

        projections = projections.MCPresentationController_projections(qt_panel, mcBusinessLogic, mcData,mainWindow)
        representations = representations.MCPresentationController_representations(qt_panel, mcBusinessLogic, mcData, mainWindow)

        widget_refs = [projections.getExplorerWidgetRef(),
                       representations.getExplorerWidgetRef()]

        for widget in widget_refs:
            widget.mouseDoubleClickEvent = self.spectrumChooserCallback


    def spectrumChooserCallback(self, event):
        """
        Display a popup to go to a spectrum given it indice
        """
        #print("inside spectrumChooserCallback")
        p = self.panel

        dialog = InputDialogText(p)
        idxs, ok = dialog.getText("Goto Spectrum by indexes...",
                                  "Enter one or more indexes:")

        ds = self.bl.io.getDataset()

        if ok and idxs:

            # on met sous forme de liste les int separés par tout type de separateur
            str_idxs_list = re.findall(r"[\w']+", idxs)
            int_idxs_list = []

            for idx in str_idxs_list:

                try:
                    idx = int(idx)

                except ValueError:
                    QtWidgets.QMessageBox.warning(self.mainWindow,
                                                  "Error",
                                                  "Invalid index: Integer required")
                    return

                if idx < 0 or idx >= ds["size"]:
                    QtWidgets.QMessageBox.warning(self.mainWindow,
                                                  "Error",
                                                  "Index out of bound [%d,%d[" % (0, ds["size"]))
                    return

                int_idxs_list.append(idx)

            print(int_idxs_list)

            if len(int_idxs_list) > 1:
                self.displayMode = self.DISP_ALL_SELECTED
                self.signals.signal_spectrumsToDisplayChanged.emit(int_idxs_list)
            else:
                self.displayMode = self.DISP_CLICKED
                self.mcData.currentSpectrumIndex = int_idxs_list[0]
                self.signals.signal_spectrumsToDisplayChanged.emit([])

