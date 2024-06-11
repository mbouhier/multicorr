from PyQt5 import QtWidgets


#=========================================================================#
#     Class de laquelle doivent heriter tous les filters                  #
#=========================================================================#


class DataFilter(QtWidgets.QMainWindow):

    button_title = ""
    button_icon = ""
    tooltip = "tooltip_test"
    category = "test_cat"

    def __init__(self):
        super().__init__()

    def useWorkFile(self):
        return hasattr(self, "workFile")

    def setWorkFile(self, workFile):
        self.workFile = workFile


class FilterException(Exception):
    """Exception raised for errors/messages returned by dataFilter
        message:explanation of the error
    """
    def __init__(self, message):
        super().__init__()
        self.message = message



if __name__ == "__main__":
    pass


