from PyQt5 import QtGui, QtWidgets
from PyQt5 import uic
from PyQt5.QtWidgets import *

from presentation.models import MulticorrGroupListModel


class MCPresentationView(object):

    def __init__(self, mcPresentationModel):
        print(type(self).__name__ + " initialized")

        self.model = mcPresentationModel()
