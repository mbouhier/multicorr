import plotpy



from plotpy.tools import InteractiveTool,SelectPointTool, FreeFormTool, RectangleTool,DefaultToolbarID,SelectTool
#from guidata.qt.QtCore import Qt, QObject, QPointF, Signal
from PyQt5.QtCore import Qt, QObject, QPointF, pyqtSignal as Signal


from plotpy.events import (setup_standard_tool_filter, ObjectHandler,
                           KeyEventMatch, StandardKeyMatch,
                           QtDragHandler, ZoomRectHandler,
                           RectangularSelectionHandler, ClickHandler)

from plotpy.items import (Axes, RectangleShape, Marker, PolygonShape,
                           EllipseShape, SegmentShape, PointShape,
                           ObliqueRectangleShape)

from plotpy.items import Marker

from functools import partial



class CorrelationBoxTool(RectangleTool):

    ICON = "bin/icons/corr_matrix.png"


class CorrelationInfoTool(InteractiveTool):

    ICON = "bin/icons/corr_matrix.png"
    MARKER_STYLE_SECT = "plot"
    MARKER_STYLE_KEY = "marker/curve"
    CURSOR = Qt.PointingHandCursor

    def __init__(self, manager, mcData, correlation_matrix_cb):
        super(CorrelationInfoTool, self).__init__(manager, toolbar_id = DefaultToolbarID)
        self.mcData = mcData
        self.correlation_matrix_cb = correlation_matrix_cb

        self.mode = "reuse"
        self.marker = None
        self.last_pos = None
        self.on_active_item = False
        self.end_callback = None

        self.marker_style_sect = self.MARKER_STYLE_SECT
        self.marker_style_key  = self.MARKER_STYLE_KEY



    def set_marker_style(self, marker):
        marker.set_style(self.marker_style_sect, self.marker_style_key)

    def setup_filter(self, baseplot):
        filter = baseplot.filter
        # Initialisation du filtre
        start_state = filter.new_state()
        # Bouton gauche :
        handler = QtDragHandler(filter, Qt.LeftButton, start_state=start_state)
        handler.SIG_START_TRACKING.connect(self.start)
        handler.SIG_MOVE.connect(self.move)
        handler.SIG_STOP_NOT_MOVING.connect(self.stop)
        handler.SIG_STOP_MOVING.connect(self.stop)
        return setup_standard_tool_filter(filter, start_state)

    def start(self, filter, event):

        constraint_cb = None
        label_cb = partial(self.label_callback, filter = filter)

        self.marker = Marker(label_cb = label_cb,
                             constraint_cb = constraint_cb)

        self.set_marker_style(self.marker)

        self.marker.attach(filter.plot)
        self.marker.setZ(filter.plot.get_max_z() + 1)
        self.marker.setVisible(True)

        self.marker.move_local_point_to(0, event.pos())
        filter.plot.replot()

    def label_callback(self, x, y, filter):

        ds = self.mcData.datasets.getDataset()

        x, y = int(x), int(y)

        inside_range_x = (x >= 0 and x < len(ds["W"]))
        inside_range_y = (y >= 0 and y < len(ds["W"]))

        if inside_range_x and inside_range_y:
            #x_str, y_str = filter.plot.get_coordinates_str(x, y)

            cm = self.correlation_matrix_cb()
            cc = cm[x,y]

            str = "<b>Correlation</b><br>"
            str += "corr(%s - %s) = %f" % (ds["W"][int(x)], ds["W"][int(y)], cc)

            return str
        else:
            return ''


    def stop(self, filter, event):
        self.move(filter, event)

        self.marker.detach()
        self.marker = None

        if self.end_callback:
            self.end_callback(self)

    def move(self, filter, event):
        if self.marker is None:
            return  # something is wrong ...
        self.marker.move_local_point_to(0, event.pos())
        filter.plot.replot()
        self.last_pos = self.marker.xValue(), self.marker.yValue()

    def get_coordinates(self):
        return self.last_pos
