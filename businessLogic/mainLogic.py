"""
This file contain all the methods to access/modify or insert datas into models
"""

import sys
import unittest

from businessLogic.representations import MCBusinessLogic_representations
from businessLogic.projections     import MCBusinessLogic_projections
from businessLogic.groups          import MCBusinessLogic_groups
from businessLogic.filters         import MCBusinessLogic_filters
from businessLogic.shapes          import MCBusinessLogic_shapes
from businessLogic.io              import MCBusinessLogic_io
from businessLogic.coordinates     import MCBusinessLogic_coordinates
from businessLogic.relationships   import MCBusinessLogic_relationships
from businessLogic.threading       import MCBusinessLogic_threading

class MCBusinessLogic(object):
    def __init__(self, mcData):
        #super(MCBusinessLogic, self).__init__()
        print(type(self).__name__ + " initialized")
        self.mcData = mcData

        #Pas d'autocompletion en faisant comme ça...
        # businessLogicNames = ["representations", "projections", "groups", "filters"]
        #
        # for bl_type in businessLogicNames:
        #     class_instance = getattr(sys.modules[__name__], "MCBusinessLogic_" + bl_type)(data)
        #     setattr(self, bl_type, class_instance)

        mainBusinessLogic = self


        self.representations = MCBusinessLogic_representations(mcData)
        self.projections     = MCBusinessLogic_projections(mcData)
        self.groups          = MCBusinessLogic_groups(mcData)
        self.filters         = MCBusinessLogic_filters(mcData)
        self.shapes          = MCBusinessLogic_shapes(mcData)
        self.coordinates     = MCBusinessLogic_coordinates(mcData)
        self.relationships   = MCBusinessLogic_relationships(mcData)
        self.io              = MCBusinessLogic_io(mcData)
        self.threading       = MCBusinessLogic_threading(mcData)


    def getNextColor(self):
        return next(self.mcData.colors)



if __name__ == "__main__":
    pass
    bl = MCBusinessLogic("test")
