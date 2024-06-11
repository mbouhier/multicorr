from businessLogic.io import MCBusinessLogic_io


class MCBusinessLogic_filters(object):


    def __init__(self, mcData):
        #super(MCBusinessLogic_filters, self).__init__()
        print(type(self).__name__ + " initialized")
        self.data = mcData

        self.io = MCBusinessLogic_io(mcData)

