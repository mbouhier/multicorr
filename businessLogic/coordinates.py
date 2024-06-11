import logging

import cv2
import numpy as np

from helpers.bigDataTools import getChunkSize


class MCBusinessLogic_coordinates(object):

    def __init__(self, mcData):
        print(type(self).__name__ + " initialized")
        self.mcData = mcData



    def getSpectrumIndexFromImageCoordinate(self, pixelX, pixelY, ds_name):
        """
        Recherche de la correspondance entre coordonnées image et data
        Normalement pixelX et pixelY doivent toujours etre bornés, sinon rique d'indice undefined
        """

        ds = self.mcData.datasets.getDataset(ds_name)
        if ds is None: return

        #TODO: calculé systematiquement au chargement? si oui test non necessaire
        if ds["img_coo_to_idx"] is None:

            indexes_layout = ds.get("indexes_layout", '')

            ds["img_coo_to_idx"], ds["idx_to_img_coo"] = self.getImageToDataIndexLUT(indexes_layout, ds_name=ds_name)

        w = ds["image_width"]
        h = ds["image_height"]

        if (0 <= pixelX <= w) and (0 <= pixelY <= h):

            spectrumIndex = ds["img_coo_to_idx"][pixelY, pixelX]

        else:
            print("XY image coordinate (%d,%d) out of range (%d x %d) for '%s'" % (pixelX, pixelY, w, h, ds_name))
            return []

        if np.isnan(spectrumIndex):
            print("spectrum not in current dataset...")
            return []

        spectrumIndex = int(spectrumIndex)

        return spectrumIndex

    def getImageCoordinateFromSpectrumIndex(self, index, ds_name):
        """
        convenient method to retrieve Image coordinate XY from spectrum index
        """

        ds = self.mcData.datasets.getDataset(ds_name)

        if 0 <= index <= len(ds["idx_to_img_coo"]):
            return ds["idx_to_img_coo"][index][1], ds["idx_to_img_coo"][index][0]

        else:
            return None

    def getXYFromImageCoordinate(self, X, Y, ds_name):
        """
        convenient method to retrieve Image coordinate XY from spectrum index
        """

        ds = self.mcData.datasets.getDataset(ds_name)

        index = self.getSpectrumIndexFromImageCoordinate(X, Y, ds_name)

        return ds["idx_to_img_coo"][index][1], ds["idx_to_img_coo"][index][0]

    def getImageCoordinateFromXY(self, x, y, ds_name):
        """
        convenient method to retrieve Image coordinate XY from spectrum index
        """
        ds = self.mcData.datasets.getDataset(ds_name)

        index = self.getSpectrumIndexFromXY(ds_name, x, y)

        if 0 <= index <= len(ds["idx_to_img_coo"]):

            return ds["idx_to_img_coo"][index][1], ds["idx_to_img_coo"][index][0]

        else:

            return None

    def getImageToDataIndexLUT(self, indexes_layout = '', ds_name = None, xys = None, imHeight = None, imWidth = None):
        '''
        Retourne un dictionnaire de correspondance entre les coordonnées images
        et les indices des datas correspondantes
        clefs sous la forme:
        array.shape = (img_idx_y,img_idx_x)
        array[img_idx_y,img_idx_x] = indice
    
        attention, une coordonnée x_img,y_img peut ne pas etre definie (spectres supprimés)
        dans ce cas:
        
        array[img_idx_y,img_idx_x] = np.nan
    
        retourne le tableau de correspondance a[x,y] -> idx et le dictionnaire d[idx] = (x,y)
    
        '''

        if not ds_name: ds_name = self.mcData.datasets.currentDatasetName

        if indexes_layout:
            msg = indexes_layout

        else:
            msg = "undefined"

        logging.debug("getImageToDataIndexLUT called with indexes_layout: " + msg)

        # si on ne specifie pas de liste xys, on prend ceux du ds en cour

        if (xys is not None and imHeight is not None and imWidth is not None):
            w = imWidth
            h = imHeight

        else:
            ds = self.mcData.datasets.getDataset(ds_name)

            w = ds["image_width"]
            h = ds["image_height"]
            xys = ds["xys"]

        # =====schemas de correspondance indices/xy connus======================

        if indexes_layout is not '':
            logging.debug("Known indexes layout: %s" % (indexes_layout,))
            img_coo_to_idx, idx_to_coo_list = self.getIndexImageCorrespondencesByLayout(indexes_layout, w, h)



        # ====si on ne connais pas la repartion des indices a priori=============

        else:
            logging.debug("calculating image coordinate to indexes matching (blind method)")
            img_coo_to_idx, idx_to_coo_list = self.getIndexImageCorrespondencesByXYs(xys, w, h)

        logging.debug("getImageToDataIndexLUT done")

        return img_coo_to_idx, idx_to_coo_list

    def isXYinsideDatasetRange(self, ds_name, x, y):

        ds = self.mcData.datasets.getDataset(ds_name)

        x_range = ds["x_range"]
        y_range = ds["y_range"]

        x_inside = max(x_range) >= x >= min(x_range)
        y_inside = max(y_range) >= y >= min(y_range)
        xy_inside = x_inside and y_inside

        return xy_inside


    def getSpectrumIndexFromXY(self, ds_name, x, y, xy_space = None):
        """
        Return indexes of data-point at x,y coordinates
        transformationMatrix is the matrix used to pass from x,y coordinate system
        to ds_name one.
        """

        ds = self.mcData.datasets.getDataset(ds_name)

        #        print "="*30
        #        print "inside getSpectrumIndexFromXY, for '%s'" % (ds_name,)



        # si l'espace de coordonnées de xy, n'est pas le meme que ds_name, on converti

        if xy_space:
            # print "using transformation matrix from", xy_space, "to", ds_name

            transformationMatrix = self.getTransformationMatrix(xy_space, ds_name)

            # print "x,y in space '%s':" % (xy_space), x,y

            a_shape = transformationMatrix.dot(np.array([x, y, 1]).T)

            x = a_shape[0] / a_shape[2]
            y = a_shape[1] / a_shape[2]

        # ======================================================================
        # Pour accelerer la recherche, on determine la position xy en
        # coordonnées images, puis on retourne l'index data associé
        # ======================================================================

        xin_min, xin_max = ds["x_range"]
        yin_min, yin_max = ds["y_range"]

        xout_min, xout_max = 0, ds["image_width"]
        yout_min, yout_max = 0, ds["image_height"]

        #        print "x,y in space '%s':" % (ds_name), x, y
        #        print "xin_min,xin_max:",xin_min,xin_max
        #        print "yin_min,yin_max:",yin_min,yin_max
        #        print "(xin_min <= x <= xin_min)",xin_min <= x <= xin_max
        #        print "(yin_min <= y <= yin_max)",yin_min <= y <= yin_max
        #        print "="*30

        if not self.isXYinsideDatasetRange(ds_name, x, y):
            return []

        x_img = int(self.remapValue(x, xin_min, xin_max, xout_min, xout_max))
        y_img = int(self.remapValue(y, yin_min, yin_max, yout_min, yout_max))

        #        print "x_img:",x_img
        #        print "y_img:",y_img

        index = self.getSpectrumIndexFromImageCoordinate(x_img, y_img, ds_name)
        #        print "getSpectrumIndexFromXY index:",index


        return index

    def setTransformationMatrixToIdentity(self, ds_name_from, ds_name_to):

        """
        set transformation matrix without GUI to identity, usefull for dataset
        derivated from another dataset
        """
        rls = self.mcData.relationships.relationships_dict

        # ds_from = self.mcData.datasets.py.getDataset(ds_name_from)
        # ds_to   = self.mcData.datasets.py.getDataset(ds_name_to)

        print("inside setTransformationMatrixToIdentity")

        c = "%s,%s" % (ds_name_from, ds_name_to)

        transformationMatrix = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]

        rls[c] = dict()  # raz ou creation de l'entree

        rls[c]["Mab"] = transformationMatrix

    def getTransformationMatrix(self, ds_name_from, ds_name_to):
        """
        Return transfer matrix translating coordinate in 'ds_name_from' (a) space
        to 'ds_name_to' (b)
        Mab = getTransformationMatrix(datasetA_name,datasetB_name)
        xys_B = Mab*xys_A
        TODO: faire la matrice Mab*Mb'c = Mac quand la relation n'existe pas directement
        """

        rls = self.mcData.relationships.relationships_dict

        # print "inside getTransformationMatrix"
        # print "from", ds_name_from, "to", ds_name_to

        c1 = "%s,%s" % (ds_name_from, ds_name_to)

        if c1 in list(rls.keys()):
            # for i in range(3): print rls[c1]["Mab"][i]
            return np.array(rls[c1]["Mab"], dtype = np.float32)

        else:
            # print "relationship doesn't exists, returning identity Matrix"
            return np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype = np.float32)

    def getWarpingTransformationMatrix(self, ds_name_from, ds_name_to):

        rls = self.mcData.relationships.relationships_dict

        print("inside getWarpingTransformationMatrix")

        print("rls.keys() in getWarpingTransformationMatrix:", rls.keys())
        print("from", ds_name_from, "to", ds_name_to)

        dsB = self.mcData.datasets.getDataset(ds_name_from)

        xr = dsB["x_range"]

        yr = dsB["y_range"]

        c1 = "%s,%s" % (ds_name_from, ds_name_to)

        if c1 not in rls:

            print("inside 'c1 not in rls'")

            return np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype = np.float32), xr[0], xr[1], yr[0], yr[1]

        else:

            print("relationship exists")

            r = rls[c1]

            # matrice permettant de dilater et translater le quadrilatere dans l'image
            # pour pouvoir superposer des images de resolution et origines differentes

            Mba = self.getTransformationMatrix(ds_name_from, ds_name_to)

            # Les coordonnées de ces points dans A permettront de definir celle de
            # la bounding-box de la projection de B dans A

            tlB = [xr[0], yr[0]]
            trB = [xr[1], yr[0]]
            brB = [xr[1], yr[1]]
            blB = [xr[0], yr[1]]

            # coordonnées coins images dans A forment un quadrilatère

            cornersB = np.float32([tlB, trB, brB, blB]).reshape(-1, 1, 2)
            cornersA = cv2.perspectiveTransform(cornersB, Mba)

            tlA = cornersA[0][0]
            trA = cornersA[1][0]
            brA = cornersA[2][0]
            blA = cornersA[3][0]

            # on cherche les coordonnées de la "bounding-box" (bb) de ce quadrilatère

            xmin_bbox, xmax_bbox = min([tlA[0], blA[0]]), max([trA[0], brA[0]])
            ymin_bbox, ymax_bbox = min([tlA[1], trA[1]]), max([blA[1], brA[1]])

            w_overlap = xmax_bbox - xmin_bbox
            h_overlap = ymax_bbox - ymin_bbox

            # on prend comme resolution un carré de max (res_x,res_y) pour avoir
            # une image correct même en cas de rotation à 90° de l'image init
            # limite de 2000px pour ne pas degrader trop les performances

            limit_res_x = 2000
            limit_res_y = 2000

            wb, hb = dsB["image_width"], dsB["image_height"]

            bbox_res_x = min(limit_res_x, max(wb, hb))
            bbox_res_y = min(limit_res_y, max(wb, hb))

            dx_px, dy_px = xmin_bbox, ymin_bbox

            # ====matrice de passage de A vers l'image HR incluse dans A ===========
            # ======================================================================

            # cv2.warpPerspective() transforme 2 images en pixel et suppose que les
            # le pixel est l'unité commune. Pour nous, les "pixels" ont des tailles
            # differentes. On prend donc les coordonnées data de l'imageB et on adapte
            # ces dernières pour mettre le pixel à la meme taille que ceux de
            # l'image A
            # points = r["pointsPositionA"]
            # points_in_baseA = [[coo for coo in points.itervalues()]]
            # points_in_baseA = np.array(points_in_baseA, dtype=np.float32)

            # rapport d'echelle des axes de l'imageA et l'imageB

            rx = bbox_res_x / w_overlap
            ry = bbox_res_y / h_overlap

            # print "rx,ry:",rx,ry

            Mac = np.array([[rx, 0, -dx_px * rx],
                            [0, ry, -dy_px * ry],
                            [0, 0, 1]])
            # ======================================================================

            Mtransfo = np.dot(Mac, Mba)

        # bbox_shape = [xmin_bbox,xmax_bbox,ymin_bbox,ymax_bbox]


        return Mtransfo, xmin_bbox, xmax_bbox, ymin_bbox, ymax_bbox

    def hasContiguousPoints(self, ds_name):
        """
        Retourne True/False si les points sont jointifs, false dans le cas de pointes Raman par example
        ou de streamline avec un pas different de la largeur de faisceau
        TODO: gerer les cas ou des points sont manquants?
        """
        ds = self.mcData.datasets.getDataset(ds_name)

        # Liste de conditions pour avoir des données continues
        c1 = ds["probe"]["shape"] == "rectangle"
        c2 = ds["probe"]["dx"] == ds["dx"]
        c3 = ds["probe"]["dy"] == ds["dy"]

        print("is shape rectangle:", c1)
        print("is probe_dx == data_dx:", c2)
        print("is probe_dx == data_dx:", c3)

        return all([c1, c2, c3])


    # ==============================================================================
    #                             SpacesMatching methods
    # ==============================================================================
    def getIndexImageCorrespondencesByXYs(self, xys, w, h):
        '''
        Retourne un dictionnaire de correspondance entre les coordonnées images
        et les indices des datas correspondantes
        clefs sous la forme:
        array.shape = (img_idx_y,img_idx_x)
        array[img_idx_y,img_idx_x] = indice

        attention, une coordonnée x_img,y_img peux ne pas etre definie (spectres supprimés)
        dans ce cas:
        array[img_idx_y,img_idx_x] = np.nan

        retourne le tableau de correspondance a[x,y] -> idx et le dictionnaire d[idx] = (x,y)
        '''
        # img_coo_to_idx  = np.zeros(shape = (h,w),dtype=np.int32)*np.nan
        workFile = self.mcData.workFile

        print("w,h", w, h)

        img_coo_to_idx  = workFile.getTempHolder((h, w))
        idx_to_coo_list = workFile.getTempHolder((w * h, 2))

        img_coo_to_idx[...] = np.nan
        # idx_to_coo_list = list()

        ys = np.unique(xys[:, 0])
        xs = np.unique(xys[:, 1])


        # idx_to_coo_list = [np.nan for i in range(w*h)]
        print("Processing indice/image lookup table, please wait...")

        # TODO: enlever la doucle boucle pour être plus efficace?
        for x_idx in range(w):
            for y_idx in range(h):
                if (x_idx * y_idx) % 700 == 0: print(".", end=' ')
                try:
                    c1 = xys[:, 0] == ys[y_idx]
                    c2 = xys[:, 1] == xs[x_idx]
                except IndexError as e:
                    # exception dans le cas ou le jdd est tronqué en idx
                    continue

                c3 = c1 & c2
                try:
                    dataIndex = np.where(c3)[0][0]
                    idx_to_coo_list[dataIndex] = (y_idx, x_idx)
                    img_coo_to_idx[y_idx, x_idx] = dataIndex
                # si il n'y a aucun point à ces coordonnées
                except IndexError:
                    img_coo_to_idx[y_idx, x_idx] = np.nan




        return img_coo_to_idx, idx_to_coo_list


    # ==============================================================================
    #                            Coorespondances
    # ==============================================================================
    def getIndexImageCorrespondencesByLayout(self, indexes_layout, w, h):
        '''
        Retourne un dictionnaire de correspondance entre les coordonnées images
        et les indices des datas correspondantes
        clefs sous la forme:
        array.shape = (img_idx_y,img_idx_x)
        array[img_idx_y,img_idx_x] = indice

        attention, une coordonnée x_img,y_img peux ne pas etre definie (spectres supprimés)
        dans ce cas:
        array[img_idx_y,img_idx_x] = np.nan

        retourne le tableau de correspondance a[x,y] -> idx et le dictionnaire d[idx] = (x,y)
        '''

        workFile = self.mcData.workFile

        img_coo_to_idx = workFile.getTempHolder((h, w))
        idx_to_coo_list = workFile.getTempHolder((h * w, 2))

        if indexes_layout == "left_to_right_line_by_line":
            img_coo_to_idx = np.arange(w * h, dtype=np.int32).reshape((h, w))

            try:
                idx_to_coo_list = [(i // w, i % w) for i in range(w * h)]

            except MemoryError as e:
                print("Process idx_to_coo_list by chunk...")
                idx_to_coo_list = workFile.getTempHolder((w * h, 2))
                chunk = getChunkSize((w * h,))
                nb_element = w * h
                for i in range(0, nb_element, chunk):
                    i_min, i_max = i, min(nb_element, i + chunk)
                    idx_to_coo_list[i_min:i_max] = np.array([(j // w, j % w) for j in range(i_min, i_max)])

        elif indexes_layout == "top_left_to_bottom_column_by_column":
            img_coo_to_idx = np.arange(w * h).reshape((w, h)).transpose()
            idx_to_coo_list = [(i % h, i // h) for i in range(w * h)]

        elif indexes_layout == "bottom_left_to_top_column_by_column":
            img_coo_to_idx = np.fliplr(np.arange(w * h).reshape((w, h))).transpose()
            idx_to_coo_list = [(h - 1 - i % h, i // h) for i in range(w * h)]

        else:
            # img_coo_to_idx  = np.zeros(shape=(h,w),dtype=np.int32)*np.nan
            img_coo_to_idx[...] = np.nan
            idx_to_coo_list = list()

        return img_coo_to_idx, idx_to_coo_list


    # TODO: a terminer pour la partie img_coo_to_idx
    def getIndexImageCorrespondencesFunctionsByLayout(self, indexes_layout, w, h):

        if indexes_layout == "left_to_right_line_by_line":
            img_coo_to_idx = np.arange(w * h).reshape((h, w))
            idx_to_coo_list = lambda indexes: [(i // w, i % w) for i in indexes]

        elif indexes_layout == "top_left_to_bottom_column_by_column":
            img_coo_to_idx = np.arange(w * h).reshape((w, h)).transpose()
            idx_to_coo_list = lambda indexes: [(i % h, i // h) for i in indexes]

        elif indexes_layout == "bottom_left_to_top_column_by_column":
            img_coo_to_idx = np.fliplr(np.arange(w * h).reshape((w, h))).transpose()
            idx_to_coo_list = lambda indexes: [(h - 1 - i % h, i // h) for i in indexes]

        else:
            img_coo_to_idx = np.full((h, w), np.nan)
            idx_to_coo_list = lambda indexes: list()

        return img_coo_to_idx, idx_to_coo_list


    # ==============================================================================
    #                             SpacesMatching methods
    # ==============================================================================


    # ==============================================================================
    #                             Other methods
    # ==============================================================================
    def remapValue(self, x, in_min, in_max, out_min, out_max):
        """
        remap value originaly inside [in_min,in_max] to [out_min,out_max]
        """
        #    print "---remap---"
        #    print "x,y,in_min,in_max,out_min,out_max:"
        #    print x,in_min,in_max,out_min,out_max
        #    print out_min + (x - in_min) * (out_max - out_min) / (in_max - in_min)
        return out_min + (x - in_min) * (out_max - out_min) / (in_max - in_min)