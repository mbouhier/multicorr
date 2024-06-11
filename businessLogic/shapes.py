# ==========================================================================
#                 Methodes realtives aux shapes
# ==========================================================================
import numpy as np
#from guidata.qt import QtCore
from PyQt5 import QtCore

#from guidata.qt.QtGui import QPolygonF
from PyQt5.QtGui import QPolygonF

from businessLogic.coordinates import MCBusinessLogic_coordinates
from helpers import mc_logging


class MCBusinessLogic_shapes(object):
    def __init__(self, mcData):
        #super(MCBusinessLogic_shapes, self).__init__()
        print(type(self).__name__ + " initialized")
        self.mcData = mcData
        self.coordinates = MCBusinessLogic_coordinates(mcData)

    def getShapePointsFromSpectrumIndex(self, ds_name, spectrum_index = None, output_space = None):
        """
        return coordinate list of points defining the shape of the probe in
        the dataset "ds_name" cordinate system if output_space is None
        in the output_space coordinate systeme if given
        """

        ds = self.mcData.datasets.getDataset(ds_name)

        if not spectrum_index and spectrum_index != 0:
            return

        #        print "inside getShapePointsFromSpectrumIndex for '%s'" % (ds_name)
        #        print "spectrum_index:",spectrum_index
        #        print "ds[xys][spectrum_index]",ds["xys"][spectrum_index]

        probe_shape = ds["probe"]["shape"]
        probe_dx = ds["probe"]["dx"]
        probe_dy = ds["probe"]["dy"]
        probe_origin = ds["probe"]["origin"]

        xy = ds["xys"][spectrum_index]

        x0, y0 = xy[1], xy[0]

        # TODO mettre dans une variable PROBE_SHAPE_RECTANGLE

        if probe_shape == "rectangle" and probe_origin == "top-left":

            tl = [x0, y0]
            tr = [x0 + probe_dx, y0]
            br = [x0 + probe_dx, y0 + probe_dy]
            bl = [x0, y0 + probe_dy]

            shape = [tl, tr, br, bl]

            if output_space:
                M = self.coordinates.getTransformationMatrix(ds_name, output_space)

                a_shape = [M.dot(np.array([x, y, 1]).T) for x, y in shape]

                shape = [[x / s, y / s] for x, y, s in a_shape]

            return (shape)


        elif probe_shape == "ellipse" and probe_origin == "center":

            tl = [x0, y0]
            tr = [x0 + probe_dx, y0]
            br = [x0 + probe_dx, y0 + probe_dy]
            bl = [x0, y0 + probe_dy]

            poly_sides = 32  # nombre de points pour creer l'ellipse, TODO, mettre ailleur

            shape = [[x0 + probe_dx * np.cos(teta), y0 + probe_dy * np.sin(teta)] for teta in
                     np.linspace(0, 2 * np.pi, poly_sides)]

            if output_space:
                M = self.getTransformationMatrix(ds_name, output_space)

                a_shape = [M.dot(np.array([x, y, 1]).T) for x, y in shape]

                shape = [[x / s, y / s] for x, y, s in a_shape]

            return (shape)


        else:
            print("Error: probe_shape and origin combinaison not implemented")
            return [[]]
            #raise NotImplementedError

    def getShapeInOtherSpace(self, shape, shape_space, output_space):
        """
        return shape originaly in shape_space in output_space using
        transformation matrix
        """

        transformationMatrix = self.coordinates.getTransformationMatrix(shape_space, output_space)

        transformed_shape = []

        for point in shape:
            t = transformationMatrix.dot(np.array([point[0], point[1], 1]).T)

            transformed_shape.append([t[0] / t[2], t[1] / t[2]])

        return transformed_shape

    def getIndexesInsideShape(self, ds_name, shape, shapeSpace, callback_progress = None):

        """
        Return indexes of data-points of ds_name inside a given shape
        if shape and data coordinates are not in the space space, xys is
        translated using given transfer Matrix
        TODO: utiliser cette methode pour la selection au lasso dans les representations?
        retourne la liste des indices i et le taux probe_shape[i] compris dans shape
        callbackprogress = fnct(progress = [-1,100]) -1 corresponding to reset
        TODO: enlever les calculs inutiles si shapeSpace=ds_name
        """

        ds = self.mcData.datasets.getDataset(ds_name)

        dx = ds["dx"]
        dy = ds["dy"]

        xys = ds["xys"]

        w = ds["image_width"]
        h = ds["image_height"]

        x_range = ds["x_range"]
        y_range = ds["y_range"]

        shape = self.getShapeInOtherSpace(shape,
                                          shape_space = shapeSpace,
                                          output_space = ds_name)

        # print "shape5555:",shape

        # ======================================================================
        # on creer la bounding_box de la shape agrandi de dx de chaque coté
        # en x et dy de chaque coté en y
        # ======================================================================

        a_shape = np.array(shape)  # on converti en np array par commodité

        min_x = min(a_shape[:, 0])
        max_x = max(a_shape[:, 0])

        min_y = min(a_shape[:, 1])
        max_y = max(a_shape[:, 1])

        bounding_rect = [[max(x_range[0], min_x - dx), max(y_range[0], min_y - dy)],
                         [min(x_range[1], max_x + dx), max(y_range[0], min_y - dy)],
                         [min(x_range[1], max_x + dx), min(y_range[1], max_y + dy)],
                         [max(x_range[0], min_x - dx), min(y_range[1], max_y + dy)]]

        # On prend les extremas en coordonnées image

        top_left     = bounding_rect[0]
        bottom_right = bounding_rect[2]

        xys = np.array(xys)

        condition_x_1 = xys[:, 1] >= top_left[0]
        condition_x_2 = xys[:, 1] <= bottom_right[0]
        condition_y_1 = xys[:, 0] >= top_left[1]
        condition_y_2 = xys[:, 0] <= bottom_right[1]

        dataIdxs = np.where(condition_x_1 & condition_x_2 & condition_y_1 & condition_y_2)

        points_inside_bounding_rect = dataIdxs[0]

        indexes = []

        overlaps_ratios = []

        total_area_probes_in_container = 0.

        total_ratio = 0.

        polygon_containing = self.listToQPolygonF(shape)

        ########## voir polygon_containing.boundingRect()


        if not polygon_containing.isEmpty:
            mc_logging.warning("invalid polygon shape")

            return indexes, overlaps_ratios, total_ratio

        # probleme avec les arrondis 1.0000000000 -> 0.9999999998 etc

        # pour ne pas avoir des points avec un recouvrement infime on introduit un epsilon

        overlap_ratio_epsilon = 0.0001

        for i, index in enumerate(points_inside_bounding_rect):

            # ======================================================================
            #   on creer la shape associée
            # ======================================================================

            shape_points = self.getShapePointsFromSpectrumIndex(ds_name, index)

            probe_shape  = self.listToQPolygonF(shape_points)

            #            if not probe_shape.is_valid:
            #                print "invalid probe shape"


            overlapping = polygon_containing.intersected(probe_shape)

            overlap_ratio = 1.0 * self.getPolygonArea(overlapping) / self.getPolygonArea(probe_shape)

            total_area_probes_in_container += self.getPolygonArea(overlapping)

            if overlap_ratio > overlap_ratio_epsilon:
                indexes.append(index)

                overlaps_ratios.append(overlap_ratio)

            total_ratio = total_area_probes_in_container / self.getPolygonArea(polygon_containing)

            if callback_progress:
                callback_progress(100.0 * i / len(points_inside_bounding_rect))

        #ResetProgressBar
        if callback_progress: callback_progress(-1)

        return indexes, overlaps_ratios, total_ratio

    def listToQPolygonF(self, shape):

        myQPointFList = []
        for p in shape:
            myQPointFList.append(QtCore.QPointF(p[0], p[1]))

        return QPolygonF(myQPointFList)

    def getPolygonArea(self, myQPolygonF):
        xs, ys = [], []
        for p in myQPolygonF:
            if type(p) is QtCore.QPointF:
                xs.append(p.x())
                ys.append(p.y())
            else:
                xs.append(p[0])
                ys.append(p[1])
        return 0.5 * np.abs(np.dot(xs, np.roll(ys, 1)) - np.dot(ys, np.roll(xs, 1)))

    # ==========================================================================
    #                 Methodes relatives aux overlaps
    # ==========================================================================
    def getOverlapRatio(self, shape_containing, shape_contained, shape_containing_space, shape_contained_space = None):
        """
        Overlap ratio beetween two shapes
        if shape_contained_space is None, same shape for both
        """

        if not shape_contained_space: shape_contained_space = shape_containing_space

        shape_contained = self.getShapeInOtherSpace(shape_contained, shape_contained_space, shape_containing_space)

        polygon_containing = self.listToQPolygonF(shape_containing)

        polygon_contained = self.listToQPolygonF(shape_contained)

        overlapping = polygon_containing.intersected(polygon_contained)

        # print "overlapping:",overlapping

        overlap_ratio = 1.0 * self.getPolygonArea(overlapping) / self.getPolygonArea(polygon_contained)

        return overlap_ratio

    def resetOverlapMap(self, ds_contained, ds_containing):
        pass

    def getOverlapMap(self, ds_contained, ds_containing):
        """
        Methode retournant les indices et les taux de recouvrement des pixels de

        ds_contained dans ds_containing


        om = relationship["ds_contained,ds_containing"]["overlap_map"]

        om["indexes_inside"] = liste de taille ds_containing contenant pour chaque indice de

        ds_containing les indices des points de ds_contained correspondant
Dossier complété, appréciation du responsable rédigée
        om["indexes_inside_ratios"] = liste contenant pour chacuns des points ci-dessus,

        le pourcentage du "pixel" de ds_contained contenue dans celui de ds_containing

        om["overlap_ratio"]= liste des taux de remplissage des pixels de ds_containing avec

        ceux de "indexes_inside"

        """

        rs = self.mcData.relationships.relationships_dict

        ds = self.mcData.datasets.getDataset(ds_containing)

        key = "%s,%s" % (ds_containing, ds_contained)

        # print "self.relationships.keys():",self.relationships.keys()

        if key not in self.mcData.relationships.names():
            print("Can't get OverlapMap, %s relationship doesn't exists" % (key,))

            return

        # on creer un conteneur vide si n'existe pas deja

        if "overlap_map" not in rs[key]:
            print("Creating empty overlap map")

            rs[key]["overlap_map"] = dict()
            rs[key]["overlap_map"]["indexes_inside"] = ['' for i in range(ds["size"])]
            rs[key]["overlap_map"]["indexes_inside_ratios"] = ['' for i in range(ds["size"])]
            rs[key]["overlap_map"]["overlap_ratio"] = [0. for i in range(ds["size"])]

        overlap_map = rs[key]["overlap_map"]

        # print "for %s,%s initial overlap map:" % (ds_contained, ds_containing), id(overlap_map)

        return overlap_map

    # ==========================================================================

    def getDatasetNameWithBiggerProbeSize(self, dataset_names, output_space):

        """

        Return name of dataset having the bigger probe size in datasets.py list

        on ne prend pas en compte le fait que la taille de la probe puisse varier

        en fonction de xy à cause de la matrice de transformation

        On compare simplement le point index = 0

        """

        if not dataset_names: return None

        probes_areas = [0 for i in dataset_names]

        for i, ds_name in enumerate(dataset_names):
            # ds = self.getDataset(ds_name)

            probe_shape = self.getShapePointsFromSpectrumIndex(ds_name, 0, output_space)

            probes_areas[i] = self.getPolygonArea(probe_shape)

        imax = probes_areas.index(max(probes_areas))

        return dataset_names[imax]