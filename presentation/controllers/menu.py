from PyQt5.QtCore import pyqtSignal, QObject

from presentation.controllers.menus import display


from helpers.data import singleton

from PyQt5 import QtGui, QtCore,QtWidgets




@singleton
class MCPresentationController_menu(QObject):

    def __init__(self, qt_panel, mcBusinessLogic, mcData, mainWindow):
        super().__init__()
        print(type(self).__name__ + " initialized")

        self.bl     = mcBusinessLogic
        self.mcData = mcData
        self.panel  = qt_panel
        self.mainWindow = mainWindow

        self.display = display.MCPresentationController_menu_display(qt_panel, mcBusinessLogic, mcData, mainWindow)


    def makeConnections(self):
        pass

    def addMenu(self, menu_widget, tab_name):

        p = self.panel
        top_menu = p.tabWidget_toolbar

        if menu_widget:

            if type(menu_widget) is QtWidgets.QPushButton:
                menu_widget.setMaximumSize(65, 65)

            # create TopMenu Tab if not exist
            if tab_name not in self._getTopMenuNames():
                self._createTabMenu(tab_name)

            for i in range(top_menu.count()):
                if top_menu.tabText(i) == tab_name:
                    layout = top_menu.widget(i).layout()

                    print("layout name:",layout.objectName(),tab_name)
                    try:
                        layout.insertWidget(layout.count() - 1, menu_widget)
                    except Exception as e:
                        print("EEEEEEEEEEEEEEEEEEEEEEEEEEEE")
                        print(e)

    def _createTabMenu(self, name):
        p = self.panel

        widget = QtWidgets.QWidget()
        widget_layout = QtWidgets.QHBoxLayout()
        widget_layout.addStretch(10)

        widget.setLayout(widget_layout)

        p.tabWidget_toolbar.addTab(widget, name)

    def _getTopMenuNames(self):
        p = self.panel
        top_menu = p.tabWidget_toolbar
        tab_names = []

        for i in range(top_menu.count()):
            tab_name = top_menu.tabText(i)
            tab_names.append(tab_name)

        return tab_names
