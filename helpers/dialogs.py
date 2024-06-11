from PyQt5 import QtGui, QtWidgets
from PyQt5 import uic


class InputDialogWithColorChoice(QtWidgets.QDialog):

    def __init__(self, parent = None):

        super().__init__()

        d = uic.loadUi("assets//ui_files//input_dialog_with_color_choice.ui")

        self.panel = d

    def getTextAndColor(self, windowsTitle, labelText, defaultText, defaultColor):

        d = self.panel

        d.setWindowTitle(windowsTitle)
        d.label.setText(labelText)
        d.lineEdit.setText(defaultText)
        d.colorButton.setStyleSheet("QWidget {background-color: %s}" % defaultColor.name())

        self.color = defaultColor
        d.colorButton.clicked.connect(self._getColor)

        ok = d.exec_()

        # ============= On recupere les donnees de la gui =======================

        if ok:
            text = d.lineEdit.text()
            color = self.color.getRgb()
            return str(text), color, ok

        else:
            return "", None, ok

    def _getColor(self):

        color = QtWidgets.QColorDialog.getColor()

        if color.isValid():
            self.color = color

        self.panel.colorButton.setStyleSheet("QWidget {background-color: %s}" % color.name())

class InputDialogText(QtWidgets.QDialog):

    def __init__(self, parent = None):

        super().__init__(parent)

        d = uic.loadUi("assets//ui_files//input_dialog_text.ui")

        self.panel = d

    def getText(self, windows_title, label_text, default_text = ""):

        d = self.panel

        d.setWindowTitle(windows_title)
        d.label.setText(label_text)
        d.lineEdit.setText(default_text)


        ok = d.exec_()

        # ============= On recupere les donnees de la gui =======================
        if ok:
            text = d.lineEdit.text()
            return str(text), ok

        else:
            return "", ok