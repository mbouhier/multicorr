import unittest

import cv2
import numpy as np
from plotpy.mathutils import colormap
import qwt as Qwt


class MCBusinessLogic_representations(object):

    def __init__(self, mcData):
        #super(MCBusinessLogic_representations, self).__init__()
        print(type(self).__name__ + " initialized")
        self.mcData = mcData

    def count(self, ds_name):
        """
        Return number of representation available for ds_name
        """
        return len(self.getAvailableRepresentations(ds_name))

    def getAvailableRepresentations(self, ds_name, family_name = "", output_type = "tuples"):

        """
        si family_name est specifié, seules les representation de cette famille seront données
        
        output_type = "dict"

        return a dict with family as key and list of representation for

        each familly as values

        d["family1"] = ["repr1","repr2","repr3","repr4"]

        d["family2"] = ["repr1a","repr2a"]

        output_type = "tuples"

        return a list containing (family,repr_name) tuples

        d = [ ("family1","repr1"), ... ,("family1","repr4"), ("family2","repr1a"),("family2","repr1b")]

        output_type = "repr_name"

        return a list of all repr_names

        d = [ "repr1", ... ,"repr4","repr1a","repr1b"]

        output_type = "family - repr_name"

        d = [ "family1 - repr1", ... ,"family1 - repr4","family2 - repr1a","family2 - repr2a"]

        output_type = "repr_name (family)"

        d = [ "repr1 (family1)", ... ,"repr2a (family2)"]

        """

        ds = self.mcData.datasets.getDataset(ds_name)

        print("getRepr for", ds_name)

        if output_type == "dict":

            r = dict()

            for family, representations in ds["representations"].items():
                r[family] = list(representations.keys())



        else:

            r = list()

            for family, representations in ds["representations"].items():

                if family_name and family != family_name: continue

                for repr_name in list(representations.keys()):

                    tuple_i = (family, repr_name)

                    if output_type == "tuples":

                        r.append(tuple_i)

                    elif output_type == "repr_name":

                        r.append(repr_name)

                    elif output_type == "family - repr_name":

                        r.append("%s - %s" % (tuple_i[0], tuple_i[1]))

                    elif output_type == "repr_name (family)":

                        r.append("%s (%s)" % (tuple_i[1], tuple_i[0]))

                    else:

                        raise NotImplemented("output_type '%s' not available" % (output_type,))

        return r

    def getRepresentation(self, ds_name, repr_family, repr_name):

        ds = self.mcData.datasets.getDataset(ds_name)

        # print "repr_family:",repr_family

        rf = ds["representations"].get(repr_family, {})

        r = rf.get(repr_name, {})

        return r

    def getRepresentationImage(self, ds_name, repr_family, repr_name, version = ""):
        """
        Return float32, rgb, rgba depending of version argument
        """

        r = self.getRepresentation(ds_name, repr_family, repr_name)

        # print("ds_name", ds_name)
        # print("repr_family",repr_family)
        # print("repr_name",repr_name)
        # print("repr.keys():")
        # print(r.keys())

        if not r:
            raise RuntimeError("Can't get representation image!")


        raw_image = r["image"]

        # ==================================================================
        # Quel est le format original de la representation ?
        # ==================================================================

        if len(raw_image.shape) == 2:
            #print("raw_image has 1 channel")
            nb_channel = 1

        else:
            nb_channel = raw_image.shape[2]
            #print("raw_image has %d channels" % (nb_channel))

        # ==================================================================
        #
        # ==================================================================

        if version == "":
            # On envoi l'image "brute"
            repr_image = r["image"]


        elif version == "float32":
            # TODO: Convertir en grayscale si le raw_image est rgb

            if nb_channel == 1:
                repr_image = r["image"]

            elif nb_channel == 3:
                repr_image = cv2.cvtColor(r["image"], cv2.COLOR_RGB2GRAY)  # TODO BGR ou RGB??

            elif nb_channel == 4:
                raise NotImplementedError


        elif version == "rgb":

            rgb_image = self.getRepresentationRGBImage(ds_name,
                                                       repr_family,
                                                       repr_name)

            #print("Converted to rgb!", rgb_image.shape)
            repr_image = rgb_image



        elif version == "rgba":

            rgba_image = self.getRepresentationRGBAImage(ds_name,
                                                         repr_family,
                                                         repr_name)
            #print("Converted to rgba!", rgba_image.shape)
            repr_image = rgba_image


        else:
            raise RuntimeError("image version '%s' not recognized" % (version,))

        # else:
        #            logging.error("Representation doesn't exists")
        #            representation = None

        return repr_image

    def getRepresentationColorMapAndLutRange(self, ds_name, repr_family, repr_name):

        r = self.getRepresentation(ds_name, repr_family, repr_name)

        #raw_image = r["image"]
        raw_image = self.getRepresentationImage(ds_name, repr_family, repr_name)

        # ==============================================================
        # Si aucune map definie on transforme un mapcolor 'jet' en rgb
        # en prenant pour bornes [mean - 1*std,mean + 1*std]
        # ==============================================================

        meanv = np.mean(raw_image)
        stdv = np.std(raw_image)

        if r["color_map"]: cmap_name = r["color_map"]
        else:              cmap_name = "jet"

        color_map = colormap.get_cmap(cmap_name)

        if r["lut_range"]:
            lut_range = r["lut_range"]

        else:
            lut_range = [meanv - 1 * stdv, meanv + 1 * stdv]

        return color_map, lut_range

    def getRepresentationColorMapAndLutRange(self, ds_name, repr_family, repr_name):

        r = self.getRepresentation(ds_name, repr_family, repr_name)

        #raw_image = r["image"]
        raw_image = self.getRepresentationImage(ds_name, repr_family, repr_name)

        # ==============================================================
        # Si aucune map definie on transforme un mapcolor 'jet' en rgb
        # en prenant pour bornes [mean - 1*std,mean + 1*std]
        # ==============================================================

        meanv = np.mean(raw_image)
        stdv = np.std(raw_image)

        if r["color_map"]: cmap_name = r["color_map"]
        else:              cmap_name = "jet"

        color_map = colormap.get_cmap(cmap_name)

        if r["lut_range"]:
            lut_range = r["lut_range"]

        else:
            lut_range = [meanv - 1 * stdv, meanv + 1 * stdv]

        return color_map, lut_range


    def getRepresentationRGBImage(self, ds_name, repr_family, repr_name):

        raw_image = self.getRepresentationImage(ds_name, repr_family, repr_name)

        #print("raw_image.shape:", raw_image.shape)

        if len(raw_image.shape) == 2:

            color_map, lut_range = self.getRepresentationColorMapAndLutRange(ds_name, repr_family, repr_name)

            #        print "inside getRepresentationRGBImage for",repr_family, repr_name
            #        print "color_map:", color_map
            #        print "lut_range:",lut_range

            interval = Qwt.QwtInterval(lut_range[0], lut_range[1])

            to_rgb = lambda x: color_map.color(interval, x).getRgb()

            to_rgb = np.vectorize(to_rgb)

            result = to_rgb(raw_image)

            rgb_image = np.ones((raw_image.shape[0], raw_image.shape[1], 3), dtype=np.uint8)

            rgb_image[..., 0] = result[0]
            rgb_image[..., 1] = result[1]
            rgb_image[..., 2] = result[2]


        else:

            return raw_image

        return rgb_image

    def getRepresentationRGBAImage(self, ds_name, repr_family, repr_name):

        rgb_image = self.getRepresentationRGBImage(ds_name, repr_family, repr_name)

        rgba_image = np.ones((rgb_image.shape[0], rgb_image.shape[1], 4), dtype=np.uint8)

        rgba_image[..., 0:3] = rgb_image
        rgba_image[..., 3] = 255

        print("rgbaimagshape",rgba_image.shape)
        return rgba_image
    # def createRepresentationFromValues(self, values):
    #
    #     if "My value1" in values: self.result = "OK"
    #     else: self.result = "FAIL"

    def createDefaultRepresentationForDataset(self, ds_name):
        """
        Create a representation taking values for one random channel (center of W)
        or a blank image
        """

        ds = self.mcData.datasets.getDataset(ds_name)

        blank = False

        if not blank:

            channel_id = int(len(ds["W"]) / 2.)

            #repr_name = "{} (channel {})".format(ds["W"][channel_id], channel_id)
            if(not np.issubdtype(type(ds["W"][channel_id]), np.str_)):
                repr_name = "{:.2f} {} (channel {})".format(ds["W"][channel_id], ds["x_unit"], channel_id)
            else:
                repr_name = "{} {} (channel {})".format(ds["W"][channel_id], ds["x_unit"], channel_id)

            image = self.getImageFromValues(ds["X"][:, channel_id], ds_name)

            self.insertRepresentationInDatasetDict("default",
                                                   repr_name,
                                                   image,
                                                   ds_name = ds_name)

        else:

            self.insertRepresentationInDatasetDict("default",
                                                   "raw",
                                                   np.zeros((ds["height"], ds["width"]), dtype = np.int8),
                                                   ds_name = ds_name)

    def getValuesFromImage(self, image):

        """"
        Return values from an image with the same order as ds["X"]
        TODO: facon de faire non optimisee!
        """

        ds = self.mcData.datasets.getDataset()

        h, w = image.shape

        if ds["img_coo_to_idx"] is None:
            indexes_layout = ds.get("indexes_layout", '')

            ds["img_coo_to_idx"], ds["idx_to_img_coo"] = self.getImageToDataIndexLUT(indexes_layout)

        holder = self.mcData.workFile.getTempHolder((ds["size"], 1))  # pour image monocanal uniquement

        for x_idx in range(w):

            for y_idx in range(h):

                try:

                    dataIndex = int(ds["img_coo_to_idx"][y_idx, x_idx])

                    holder[dataIndex, 0] = image[y_idx, x_idx]

                except Exception as e:

                    print("except image")

                    print(e)

        return holder

    def getImageFromValues(self, values, ds_name = None):
        """
        Return an image on the form of a (height x width) numpy array base on
        values list. len(values) must be height x width.
        height and width are those of current dataset
        """
        ds = self.mcData.datasets.getDataset(ds_name)

        w = ds["image_width"]
        h = ds["image_height"]

        # on regarde si le tableau de correspondance imgs -> index existe, sinon
        # on demande à le calculer et on l'ajoute aux données du dataset

        if ds["img_coo_to_idx"] is None:
            # schema d'indexation 1,2,3 4,5,6 7,8,9 ou 1,4,7 2,5,6 3,6,9 etc...

            indexes_layout = ds.get("indexes_layout", '')

            ds["img_coo_to_idx"], ds["idx_to_img_coo"] = self.getImageToDataIndexLUT(indexes_layout)

        print("Returning image (%dx%dpx)" % (w, h))

        # Mettre en < float32?
        image = np.zeros((h, w), 'float32')

        for x_idx in range(w):
            for y_idx in range(h):

                try:
                    # dataIndex = ds["img_coo_to_idx"]["(%d,%d)" % (x_idx,y_idx)]
                    dataIndex = int(ds["img_coo_to_idx"][y_idx, x_idx])  # pourquoi ne sors pas deja en int?...

                    # print "dataIndex:",dataIndex
                    # print "dataIndex at (%d,%d):%d" % (x_idx,y_idx,dataIndex)
                    # print "value:",values[dataIndex][0]


                    # si values[dataIndex] est une liste
                    # TODO voir pourquoi ce n'est pas un scalar dans tous les cas

                    try:
                        # print "y_idx",type(y_idx)
                        # print "x_idx",type(x_idx)
                        # print "dataIndex",type(dataIndex)
                        image[y_idx, x_idx] = values[dataIndex][0]

                    except Exception as e:
                        # print "exception:",e
                        image[y_idx, x_idx] = values[dataIndex]

                except Exception as e:
                    # print "(x:%d,y:%d)" % (x_idx,y_idx), "not defined in this dataset"
                    # print e
                    pass

        return image

    def insertRepresentationInDatasetDict(self, family, repr_name, image, dataset = None, override = True, ds_name = None):

        """
        insert a dataset representation in ds["representations"] dict()
        ds["representations"][family_name] = dict(
        ds["representations"][family_name][repr_name]["image"] = array(imwidth,imheight)

        if display = True, change current selected representation
        if gotoTab = True, display representation Tab
        """

        if ds_name is None and not dataset:
            ds_name = self.mcData.datasets.currentDatasetName

        if dataset:
            ds = dataset

        else:
            ds = self.mcData.datasets.getDataset(ds_name)

        rps = ds["representations"]

        # si la famille n'existe pas, on la cree

        if family not in rps: rps[family] = dict()

        rps[family][repr_name] = {"image": image, "lut_range": [], "color_map": ""}

        print('"%s" representation added to "%s" family' % (repr_name, family))

    def removeRepresentationFamilyFromDatasetDict(self, family):
        """
        remove a dataset representation familyfrom ds["representations"] dict()
        """
        ds = self.mcData.datasets.getDataset()

        ds["representations"].pop(family, None)

        print("'%s' representations family removed" % (family))



class MCBusinessLogicTest_representations(unittest.TestCase):

    def test_simple(self):
        pass
    # def test_representation_creation_from_values(self):
    #     v = ["My value1", "My value2", "My value3"]
    #
    #     self.bl = MCBusinessLogic_representations("rien")
    #     self.bl.createRepresentationFromValues(v)
    #
    #     self.assertEqual(self.bl.result, "OK")


if __name__ == "__main__":
    unittest.main()
