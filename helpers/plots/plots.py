from plotpy.plot import PlotDialog
from plotpy.plot import PlotWidget

#from qwt.qt.QtGui import QFont, QColor, QBrush
from PyQt5.QtGui import QFont, QColor, QBrush

import qwt as Qwt
import plotpy
from plotpy.interfaces import ICurveItemType, IImageItemType
from PyQt5.QtCore import Qt
import numpy as np
from plotpy.builder import make

def getItemsInPlotMatchingName(plot, name):
    """
    Return items dictionarry with item title in key and item ref as value
    of all items in plot with a title containing "name"
    """

    items = dict()

    for item in plot.get_items():

        item_title = str(item.title().text())

        if name in item_title:
            items[item_title] = item

    return items



def getPlotByWidgetName(curveWidget_name, panel):

    cw = panel.findChild(PlotWidget, name = curveWidget_name)
    cd = panel.findChild(PlotDialog, name = curveWidget_name)

    if not cw and not cd:
        print("Can't find curveWidget or curveDialog")
        return

    if cw:   curve_holder = cw
    elif cd: curve_holder = cd

    plot = curve_holder.get_plot()

    return plot



def getDefaultCurveStyle(x, curvestyle = ''):
    """
    Get default curvestyle, linewidth and  color depending of x size and type
    """
    # ==========================================================
    # Application d'un style
    # ==========================================================
    stick_display_threshold = 25
    sticks_color = QColor(212, 149, 149, 220)
    #lines_color  = QColor(11, 64, 150, 255)
    lines_color  = QColor(220, 85, 37, 255)

    if not curvestyle:
        if len(x) < stick_display_threshold: curvestyle = "Sticks"
        else:                                curvestyle = "Lines"


    if curvestyle == "Sticks":
        bg_color = sticks_color
        linewidth = 30
        # make.curve veut du hexa, on ajoute un canal alpha en car QColor.name() sort #rrggbb
        alpha_hex = "%X" % (bg_color.alpha())
        color = bg_color.name() + alpha_hex.zfill(2)
    else:
        bg_color = lines_color
        linewidth = 1
        color = bg_color.name()

    #print("return curvestyle, linewidth, color:", curvestyle, linewidth, color)
    return curvestyle, linewidth, color



def displayAPlotInCurveWidget(curveWidget_name, title, x, y, panel, style = None, color = Qt.red):
    """
    Fonction inserant les data x vs y dans le plot d'un curveWidget a partir du
    nom du widget
    style: Lines, Sticks, Steps, Dots, UserCurve, NoCurve
    voir http://qwt.sourceforge.net/class_qwt_plot_curve.html#a9d5c81d3340aebf2ab8cf0dfee7e9c81
    """
    #print("inside _displayAPlotInCurveWidget")

    if x is None or y is None:
        print("no x or y specified")
        return

    plot = getPlotByWidgetName(curveWidget_name, panel = panel)

    if not plot:
        print("TODO: a gerer")
        print("ce widget n'existe pas curveWidget_name:",curveWidget_name)
        return

    # on enleve les elements dejas existants
    for item in plot.get_items(item_type = ICurveItemType):
        plot.del_item(item)

    curve = getCurveItem(x[:], y[:], curvestyle = style)

    plot.add_item(curve)

    #curve.attach(plot)

    title = Qwt.QwtText(title)
    title.setFont(QFont('DejaVu', 8, QFont.Light))
    plot.setTitle(title)

    plot.do_autoscale()
    plot.replot()

def getCurveItem(x, y, curvestyle = '', linewidth = 0, color = '', title = '', linestyle = None):
    """
    Convenient method returning a curve Item depending of len(x) and type(x)
    """
    cs, lw, col = getDefaultCurveStyle(x, curvestyle)

    if not curvestyle: curvestyle = cs
    if not linewidth:  linewidth  = lw
    if not color:      color      = col

    if np.issubdtype(type(x[0]), int) or np.issubdtype(type(x[0]), float):
        new_x = x[:]
    else:
        new_x = range(len(x))

    #print("new_x[0]:",new_x[0])
    #print("curvestyle in getCurveItem:",curvestyle)

    curve = make.curve(new_x, y[:], curvestyle = curvestyle, linewidth = linewidth, color = color, title = title, linestyle = linestyle)

    return curve