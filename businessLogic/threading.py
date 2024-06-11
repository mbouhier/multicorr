import threading
from helpers import mc_logging
from PyQt5 import QtGui, QtWidgets


class ThreadingStates:
    STOP     = 0
    RESET    = 1
    FINISHED = 2

class MCBusinessLogic_threading(object):

    states = ThreadingStates()

    def __init__(self, mcData):
        #super().__init__()
        print(type(self).__name__ + "initialized")
        self.mcData = mcData

        self.Rlock = threading.RLock()  # http://stackoverflow.com/questions/22885775/what-is-the-difference-between-lock-and-rlock

    def setProcessingThreadFlag(self, state):

        if state == self.states.STOP:
            self.processingThreadStopEvent.set()

        elif state == self.states.FINISHED:
            self.processingThreadFinishedEvent.set()

        elif state == self.states.RESET:
            self.processingThreadStopEvent = threading.Event()
            self.processingThreadFinishedEvent = threading.Event()


    def askForProcessThreadCanceling(self):

        """
        Methode affichant un dialog indiquant qu'un fit et en cours
        Mise a jour des flag correspondant
        retourne True si l'annulation du Thread est confirmée, False sinon
        """

        reply = QtWidgets.QMessageBox.question(None, 'Confirmation',
                                               'Process already running, do you want to cancel current instance?',
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                               QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.Yes:

            mc_logging.debug("Canceling current processing instance...")

            self.setProcessingThreadFlag(self.states.STOP)

            ###################self.processingThreadFinishedEvent.wait()

            # RAZ de l'etat des flags

            self.setProcessingThreadFlag(self.states.RESET)

            mc_logging.debug("Processing instance terminated!")

        else:
            mc_logging.debug("Processing request canceled")
            return True

        return 0