import h5py
import numpy as np

import helpers
from businessLogic.coordinates     import MCBusinessLogic_coordinates
from businessLogic.representations import MCBusinessLogic_representations
from helpers import mc_logging
from helpers.bigDataTools import fillByChunk, getChunkSize, normalizeHDF5, meanHDF5


class MCBusinessLogic_io(object):
    def __init__(self, mcData):
        #super(MCBusinessLogic_io, self).__init__()
        print(type(self).__name__ + "initialized")

        self.mcData = mcData
        self.representations = MCBusinessLogic_representations(mcData)
        self.coordinates     = MCBusinessLogic_coordinates(mcData)



    @property
    def workFile(self):
        return self.mcData.workFile

    def deleteWorkFile(self):
        self.mcData.workFile.delete()

    @property
    def projectFile(self):
        return self.mcData.projectFile

    def deleteProjectFile(self):
        self.mcData.projectFile.delete()

    def isProjectFile(self, path):

        """
        Return true if slicy project file type
        pour l'instant, la façon de tester et de voir si il y a une clef "relationship"
        TODO, faire plus robuste?
        """

        ext = path.split(".")[-1]

        print("extension is ", ext)

        if ext == "h5":

            with h5py.File(path, 'r') as f:

                keys = list(f.keys())

                if "relationships" in keys:
                    return True

                else:
                    return False

        else:

            return False

    def getDatasetsAndRelationshipsFromFile(self, filename, progress_callback = None):
        """
        return two dictionnaries containing datasets.py and relationships retrieved from file
        """

        # Containers
        relationshipsContainer = dict()
        datasetsContainer      = dict()

        if progress_callback: progress_callback(0)

        mc_logging.info("Loading project file '%s'" % (filename.split('/')[-1]))

        with h5py.File(filename, 'r') as f:

            keys = list(f.keys())

            # ====clefs relatives aux datasets.py et aux relations entre ds============

            relationship_keys = ["relationships"]

            datasets_keys = [k for k in keys if k != "relationships"]

            print(("datasets_keys:", datasets_keys))
            mc_logging.debug("loading dataset_keys...")

            self.__hdf5_to_dict_recursive(f, datasetsContainer, datasets_keys, progress_callback)

            if "relationships" in keys:
                mc_logging.debug("loading relationships...")
                self.__hdf5_to_dict_recursive(f, relationshipsContainer, relationship_keys, progress_callback)

        mc_logging.info("project opening done!")

        if progress_callback: progress_callback(70)

        # ======================================================================
        # Au chargement d'un projet, les xys des groupes sont sous forme de
        # numpyarray, donc non modifiable par append/pop, on converti donc en list
        # ======================================================================

        for _, dataset in datasetsContainer.items():
            for _, group in dataset["groups"].items():
                group["xys"] = group["xys"].tolist()

        if "relationships" in relationshipsContainer:
            relationships = relationshipsContainer["relationships"]

        else:
            relationships = dict()

        if progress_callback: progress_callback(-1)

        return datasetsContainer, relationships

    def convertDictToHdf5(self, dictionary, hdf5filename, progress_callback = None):

        """
        Simplement un alias, pour pouvoir changer de technique d'enregistrement si besoin
        """

        mc_logging.info("converting dict to hdf5, please wait...")
        mc_logging.debug("save in", hdf5filename)

        try:
            hdf5file = h5py.File(hdf5filename, 'a')

        except Exception as e:
            mc_logging.error("Can't create HDF5 file:")
            mc_logging.error(e)
            return False

        wf = self.mcData.workFile.getFile()

        wf.flush()

        workFile_id = wf.id

        outputFile_id = hdf5file.id

        self.__dict_to_hdf5_recursive(hdf5file, dictionary, list(dictionary.keys()), workFile_id, outputFile_id, progress_callback)

        hdf5file.close()

        mc_logging.debug("hdf5 conversion done")

        if progress_callback: progress_callback(-1)



    def __dict_to_hdf5_recursive(self, hdf5_formated, dict_formated, keys, input_id, output_id, progress_callback):

        keys_to_skip = ["pca"]  # les clefs à ne pas enregistrer

        # print "entering recursive,keys:",keys

        for k in keys:

            if k in keys_to_skip: continue

            # print "data type for '%s':" % (k,) , type(dict_formated[k]) , type(k)



            try:

                # Si cette valeur de dictionnaire n'est pas elle meme un dictionnaire

                if(isinstance(dict_formated[k], h5py.Dataset)):
                    # si type dataset hdf5

                    mc_logging.debug("dataset type detected for", k)

                    input_HDF5dataset = dict_formated[k]

                    hdf5_formated.create_dataset(k, shape = input_HDF5dataset.shape, dtype = input_HDF5dataset.dtype)

                    # enregistrement block par block
                    fillByChunk(input_HDF5dataset, hdf5_formated[k], progress_callback)

                    print("h5.h5o.copy done")

                
                if not isinstance(dict_formated[k], dict) and not isinstance(dict_formated[k], h5py.Dataset):

                    try:

                        # enregistrement "direct"
                        # print("type(k):",type(k))
                        # print("k:",k)
                        # print("type dict_formated[k]1:", type(dict_formated[k]))
                        #print [a.encode('utf8') for a in mylist])

                        #===============================================================
                        #Correction en cas de liste unicode, erreur de type
                        #"No conversion path for dtype: dtype('<U277')"

                        #print("type(dict_formated[%s]" % (k,), type(dict_formated[k]))

                        if type(dict_formated[k]) is np.ndarray:
                            #print("dtype:",dict_formated[k].dtype)
                            if dict_formated[k].dtype.char == "U":
                                #print("converting to list")
                                dict_formated[k] = dict_formated[k].tolist()
                            #dict_formated[k] = dict_formated[k].astype("utf8")

                        if type(dict_formated[k]) is list:
                            #print("conversion2'")
                            list_contain_str = any([type(e) is str for e in dict_formated[k]])

                            if list_contain_str:
                                #print("conversion3'")
                                dict_formated[k] = [a.encode('utf8') for a in dict_formated[k]]
                                # print("type dict_formated[k]2:", type(dict_formated[k]))


                        # print("conversion4before'")
                        hdf5_formated[k] = dict_formated[k]
                        # print("conversion4after'")
                        # print("type hdf5_formated[k]:", type(hdf5_formated[k]))

                    except RuntimeError as e:

                        # si type dataset hdf5
                        print ("inside RuntimeError:",e)


                    except TypeError as e:
                        mc_logging.error("typeError!")
                        mc_logging.error(e)

                    except Exception as e:

                        mc_logging.error("Exception, can't directly record '%s' key:" % (k,))
                        mc_logging.error("type of data:", type(dict_formated[k]))
                        mc_logging.error("exception message:", e)

                        hdf5_formated[k] = ''

                        mc_logging.error("blank value recorded")


                # Dans le cas contraire, on creer un groupe (dict python = groupe hdf5)

                else:
                    mc_logging.debug("creating a group for key '{}'".format(k))

                    group = hdf5_formated.create_group(k)

                    output_id = group.id

                    self.__dict_to_hdf5_recursive(hdf5_formated[k],
                                                  dict_formated[k],
                                                  list(dict_formated[k].keys()),
                                                  input_id,
                                                  output_id,
                                                  progress_callback)



            except Exception as e:
                mc_logging.error("exception for key '{}'".format(k))
                mc_logging.error(e)

    def __hdf5_to_dict_recursive(self, hdf5_formated, dict_formated, keys, progress_callback = None):

        # Dans le hdf5, tous est converti en array mais notre programme utilise beaucoup de liste
        # en attendant d'uniformiser, les clefs suivantes sont reconvertis en list au chargement
        keys_to_convert_to_list = ["indexes", "vectors_names"]
        keys_to_copy_as_hdf5_dataset = ["X", "X_normalized"]
        keys_to_skip = ["pca"]  # les clefs à ne pas lire


        keys_nb = len(keys)

        for i, k in enumerate(keys):

            # print "key:", k
            print(".", end = ' ')
            k = helpers.data.convertBytesToStr(k)

            if progress_callback: progress_callback(100.*i/keys_nb)

            try:
                # Si cette valeur de dictionnaire n'est pas elle meme un dictionnaire
                if isinstance(hdf5_formated[k], h5py.Group):

                    dict_formated[k] = dict()
                    self.__hdf5_to_dict_recursive(hdf5_formated[k], dict_formated[k], list(hdf5_formated[k].keys()))

                elif isinstance(hdf5_formated[k], h5py.Dataset):

                    #print("key:",k,"is a dataset")
                    # if hdf5_formated[k].shape == ():

                    if k in keys_to_convert_to_list:
                        # mc_logging.debug("converting '%s' to list" % (k,))
                        # print hdf5_formated[k].value depreciated
                        #print hdf5_formated[k][()] new syntax
                        try:
                            v = hdf5_formated[k][()].tolist()
                            # print("=================")
                            # print(v)
                            # print(type(v))
                            v = helpers.data.convertBytesToStr(v)
                            dict_formated[k] = v

                        except AttributeError as e:
                            mc_logging.error("exception:" + e)

                            v = hdf5_formated[k][()]
                            v = helpers.data.convertBytesToStr(v)
                            dict_formated[k] = hdf5_formated[k][()]



                    elif k not in keys_to_skip:

                        if k not in keys_to_copy_as_hdf5_dataset:

                            v = hdf5_formated[k][()]
                            v = helpers.data.convertBytesToStr(v)
                            dict_formated[k] = v

                        else:

                            print("")
                            print(("copying '%s' as hdf5 dataset" % (k,)))

                            d = self.mcData.workFile.getTempHolder(hdf5_formated[k].shape)

                            dict_formated[k] = d

                            try:
                                v = hdf5_formated[k][()]
                                v = helpers.data.convertBytesToStr(v)
                                dict_formated[k][:] = v

                            except MemoryError as e:
                                print("Memory error during '%s' filling")
                                print("Processing by chunk")
                                fillByChunk(hdf5_formated[k], dict_formated[k])



            except TypeError as e:
                print(("TypeError exception for key '%s'" % (k,)))
                print(e)

            except MemoryError as e:
                print(("MemoryError exception for key '%s'" % (k,)))
                print(e)

        if progress_callback: progress_callback(-1)


    def saveProject(self, filename, progress_callback = None):
        # copy du fichier projet, renomage puis suppression
        #        shutil.copyfile(self._projectFilePath,filename)
        #        self.delProjectFile()
        #        self._projectFilePath = filename

        self.convertDictToHdf5(self.mcData.datasets.datasets_dict, filename, progress_callback)

        # TODO, ca serait mieux de tout faire d'un coup avec un groupe "datasets.py"

        # et un group relationships
        self.convertDictToHdf5({"relationships": self.mcData.relationships.relationships_dict}, filename, progress_callback)

    def loadProject(self, filename, progress_callback = None):

        ds = self.mcData.datasets
        rs = self.mcData.relationships

        ds.datasets_dict, rs.relationship_dict = self.getDatasetsAndRelationshipsFromFile(filename, progress_callback)



    # ===========================================================================
    #        Operations sur Dataset
    # ===========================================================================

    def saveDataset(self, ds_name, filename):
        ds = self.getDataset(ds_name)
        keys_to_export = ("W", "X", "xys", "idx_to_img_coo", "image_width", "image_height")

        mc_logging.info("saving '{}' to '{}'".format(ds_name, filename))
        try:
            #on creer un dictionnaire temporaire comprenant les clefs qui nous interessent pour l'export
            temp_dict = {"dataset":dict()}
            for k in keys_to_export:
                temp_dict["dataset"][k] = ds[k]

            self.convertDictToHdf5(temp_dict, filename)

        except Exception as e:
            mc_logging.error("Can't create HDF5 file:")
            mc_logging.error(e)
            raise(e)
            return False

        mc_logging.info("saving done")

    def removeDataset(self, ds_name):
        self.mcData.datasets.remove(ds_name)
        self.mcData.relationships.removeByDatasetName(ds_name)

    def pushDataset(self, dataset, name):
        self.mcData.datasets.pushDataset(dataset, name)

    def addDatasetToDict(self, name, W, datas, xys, normalize_method, base_dataset = None, args = dict(),
                         indices_in_base_dataset = None,
                         xys_base_dataset = None, color = None, callback_progress = None):
        """
        Cette methode creer tous les champs necessaires d'un objet dataset
        On creer d'abord l'objet dataset sous forme de dictionnaire car plus lisible
        On le converti ensuite en hdf5
        """
        mc_logging.info('adding "%s" dataset to datasets.py dictionary' % (name))

        # ================Passage en HDF5 si pas deja le cas====================

        datas_hdf5 = self.mcData.workFile.getTempHolder(datas.shape)

        print("datas.shape1:", datas.shape)
        print("datas_hdf5.shape1:", datas_hdf5.shape)

        if not type(datas) == h5py.Dataset:
            print("converting datas to hdf5 dataset...")

            # datas = datas.astype(np.float32, copy = False)
            fillByChunk(datas, datas_hdf5, callback_progress)
            datas = datas_hdf5

            print("hdf5 conversion done")

        print("input datas.dtype after", datas.dtype)

        # =====================================================================

        print("datas.shape2:", datas.shape)

        # =============on cree un nouvel entree================================

        dataset = dict()

        dataset["name"] = name
        dataset["uid"]  = name  # + "-" + str(random.randint(0, 1000000))
        dataset["X"]    = datas
        dataset["xys"]  = xys
        dataset["W"]    = W


        # ====on enregistre les parametres optionels contenus dans args=========
        # TODO: cette partie risque de poser probleme???? mise en commentaires
        #        if args:
        #            for key,value in args.iteritems():
        #                datasets.py[name][key] = value



        # TODO: incoherence terme xys, en fait yxs, a corriger au chargement

        # print('dataset["xys"]:', dataset["xys"])

        # ======================================================================
        # Recherche des x,y uniques pour calculer la taille spatiale du jdd
        # on s'affranchi de ces calculs si les width et height sont données
        # ce sera le cas d'un fichier image par exemple
        # ======================================================================

        try:
            xs_unique = np.unique(dataset["xys"][:, 1])
            ys_unique = np.unique(dataset["xys"][:, 0])

        except MemoryError:

            print("Memory error while evaluating dataset xys, trying to proceed by chunk")

            chunk = getChunkSize(dataset["xys"].shape)

            xs_unique = []
            ys_unique = []

            nb_sp = len(dataset["xys"])

            for i in range(0, len(dataset["xys"]), chunk):
                i_min = i
                i_max = min(nb_sp, i_min + chunk)

                xs_unique_chunk = np.unique(dataset["xys"][i_min:i_max, 1])
                ys_unique_chunk = np.unique(dataset["xys"][i_min:i_max, 0])

                xs_unique += list(xs_unique_chunk)
                ys_unique += list(ys_unique_chunk)

            # on enleve les valeurs en doubles
            xs_unique = np.unique(xs_unique)
            ys_unique = np.unique(ys_unique)


        extrema_xs = [min(xs_unique), max(xs_unique)]
        extrema_ys = [min(ys_unique), max(ys_unique)]

        # on gere les cas ou il n'y a qu'une ligne/colonne/spectre

        if len(xs_unique) > 1:
            dx = abs(xs_unique[1] - xs_unique[0])

        else:
            dx = 1.

        if len(ys_unique) > 1:
            dy = abs(ys_unique[1] - ys_unique[0])

        else:
            dy = 1.

        dataset["width"]  = len(xs_unique)
        dataset["height"] = len(ys_unique)

        print("ys_uniques:", ys_unique)

        # ======================================================================


        # si le dx != dy, permet d'avoir une image presentant le bon rapport de taille

        # TODO: voir le cas ou dx et dy ne sont pas constants.

        dataset["aspect_ratio"] = 1  # dy / dx
        dataset["mean_datas"] = meanHDF5(datas, axis=0)
        dataset["size"] = len(datas)

        # datasets.py[name]["pca"]          = dict()

        dataset["base_infos"] = dict()
        dataset["groups"] = dict()
        dataset["representations"] = dict()

        # si il y a dejas une representation par default (cas des images), on l'insert maintenant

        if "default_representations" in args:
            for r in args["default_representations"]:
                self.representations.insertRepresentationInDatasetDict("default",
                                                                       r["name"],
                                                                       r["image"],
                                                                       dataset=dataset)

        dataset["fits"] = dict()  # a mettre dans representations?
        dataset["metadatas"] = dict()
        dataset["projections"] = dict()
        dataset["display"] = dict()

        if color:
            dataset["display"]["color"] = color

        else:
            print("No color specified")

            # ================conteneur pour les eventuels fits=====================
            # TODO, non utilisé?

        #        dataset["metadatas"]["fit"] = dict()
        #        dataset["metadatas"]["fit"]["X"] = [None for i in range(len(datas))]
        #        dataset["metadatas"]["fit"]["X_residuals"] = [None for i in range(len(datas))]

        # ======================================================================
        #             Creation d'un dataset normalisé
        # ======================================================================

        # TODO: a mettre dans un object CONFIG
        preprocess_normalize = False

        if not preprocess_normalize:

            dataset["X_normalized"] = None
            dataset["mean_datas_normalized"] = None

        else:

            datas_normalized = normalizeHDF5(datas, self.mcData.workFile, normalize_method)

            # normalisation par default, effectué au chargement = normalisation par le max
            # elle sera recalculé si on change la combo_normalization_type


            # on creer un masque pour ne pas calculer le mean avec les np.nan
            # datas_normalized_without_nans = np.ma.masked_array(datas_normalized,np.isnan(datas_normalized))

            dataset["X_normalized"] = datas_normalized

            dataset["mean_datas_normalized"] = meanHDF5(datas_normalized, axis=0)

        # =============Données relatives à la probe============================
        # TODO: implementer ellipse
        # lire ça dans les arguments et dans la GUI, valeurs par defauft ici POUR TEST SEULEMENT
        # TODO: gerer le cas d'un base dataset

        dataset["probe"] = dict()
        dataset["probe"]["shape"] = "rectangle"

        # TODO: coordonnée xys correspondent au point top-left/right, bottom left/right, center

        # un seul cas gerer, à implementer pour le reste

        dataset["probe"]["origin"] = "top-left"
        dataset["probe"]["dx"] = dx
        dataset["probe"]["dy"] = dy

        # print "mean_datas_normalized", dataset["mean_datas_normalized"]

        # ===================== Original dataset infos ==========================

        # =======================================================================

        if base_dataset is None:

            dataset["image_width"] = dataset["width"]
            dataset["image_height"] = dataset["height"]

            dataset["dx"] = dx
            dataset["dy"] = dy

            dataset["x_unit"] = args.get("x_unit", 'u.a.')
            dataset["y_unit"] = args.get("y_unit", 'u.a.')
            dataset["spatial_unit"] = args.get("spatial_unit", 'u.a.')

            # ==================================================================

            try:
                dataset["base_infos"]["original_idxs"] = np.arange(len(xys))

            except MemoryError:

                print("memory error while assigning original_idxs")

                print("trying to proceed by chunks")

                o_idxs = self.mcData.workFile.getTempHolder((len(xys),), dtype=np.int64)

                chunk_size = getChunkSize(o_idxs.shape)

                nb_element = len(xys)

                for i in range(0, nb_element, chunk_size):
                    i_min, i_max = i, min(nb_element, i + chunk_size)
                    o_idxs[i_min:i_max] = np.arange(i_min, i_max)

                print("original_idxs done")

                dataset["base_infos"]["original_idxs"] = o_idxs

            # ==================================================================
            dataset["base_infos"]["original_xys"] = xys
            dataset["base_infos"]["name"] = None

            # dictionnaire de correspondance entre coordonnées images et indice du spectre
            # datasets.py[name]["img_coo_to_idx"] = dict()
            # matrice correspondance entre coordonnées images et indice du spectre, remply avec nan par defaut
            # datasets.py[name]["img_coo_to_idx"] = np.array(shape=(datasets.py[name]["height"],datasets.py[name]["width"]),dtype=np.int32)*np.nan

            indexes_layout = ""
            if args:
                if "indexes_layout" in args: indexes_layout = args.get("indexes_layout", "")

            dataset["img_coo_to_idx"], dataset["idx_to_img_coo"] = self.coordinates.getImageToDataIndexLUT(
                indexes_layout,
                xys=xys,
                imWidth=dataset["width"],
                imHeight=dataset["height"])

            # ==================================================================
            # ============== Calcul du data-range en x et y ====================
            # ==================================================================
            dataset["x_range"] = extrema_xs
            dataset["y_range"] = extrema_ys

            # si on veux tenir compte de la taille de la probe et pas seulement des coordonnées xy
            # TODO: ce calcul est valable pour une probe rectangulaire d'origine top-left
            dataset["x_range"][1] = dataset["x_range"][1] + dataset["probe"]["dx"]
            dataset["y_range"][1] = dataset["y_range"][1] + dataset["probe"]["dy"]

        else:  # if base_dataset not None

            # =========on remplit d'abord quelques champs========================

            dataset["base_infos"]["name"] = base_dataset["name"]

            # Pour dx,dy on ne calcule plus le dx avec unique(xys) car les pas ne sont plus forcement constants
            # si des spectres sont supprimés

            keys_to_copy = ["image_width", "image_height", "dx", "dy", "x_unit", "y_unit", "spatial_unit", "x_range",
                            "y_range"]
            for k in keys_to_copy: dataset[k] = base_dataset[k]

            # ============================ Lookup Table =========================
            # on garde en memoire la correspondance entre indices du nouveau jdd
            # et les indices dans le jdd qui lui a servi de base

            dataset["base_infos"]["idx_to_base_idx"] = indices_in_base_dataset
            dataset["base_infos"]["xys"] = xys_base_dataset[indices_in_base_dataset]

            base_infos = base_dataset["base_infos"]

            """datasets.py[name]["img_coo_to_idx"] = None
            on garde en memoire les indices des spectres dans le jdd original
            en se basant sur les xys correspondant
            """

            # == indexes des xys de la selection dans le repere du jdd de base ===

            dataset["base_infos"]["original_idxs"] = [base_infos["original_idxs"][i] for i in indices_in_base_dataset]
            dataset["base_infos"]["original_xys"] = [base_infos["original_xys"][i] for i in indices_in_base_dataset]

            # ==========coordonnées images vers indice spectres=================
            # on transforme les indices initiaux de img_coo_to_idx vers leurs nouvel valeur dans le new dataset
            # s'il ne sont pas present dans le nouveau jdd, ils seront egaux à NAN
            # prenant leur valeur dans la nouvelle base (si ils existent)


            # on initialiser pour avoir la bonne taille de liste et de matrice

            new_img_coo_to_idx = np.zeros(shape=base_dataset["img_coo_to_idx"].shape, dtype=np.int32) * np.nan
            new_idx_to_img_coo = [0 for __ in range(dataset["size"])]

            # on met sous forme de dictionnaire pour accelerer la recherche (.index() etant lent sur une liste)
            # voir l'utilisation d'un dataFrame panda

            new_idx_from_base_idx = dict()

            for i, base_idx in enumerate(dataset["base_infos"]["idx_to_base_idx"]):
                new_idx_from_base_idx[base_idx] = i

            # --------------------------------------------------------------------------------
            for row_colum, value in np.ndenumerate(base_dataset["img_coo_to_idx"]):

                try:
                    new_img_coo_to_idx[row_colum] = new_idx_from_base_idx[value]

                except KeyError:  # raised if not in the list, value remain np.nan in new_img_coo_to_idx
                    # print "original spectrum %d not in new dataset" % (value)
                    pass

            for i in range(dataset["size"]):
                i_in_base_dataset = indices_in_base_dataset[i]
                img_coo = base_dataset["idx_to_img_coo"][i_in_base_dataset]
                new_idx_to_img_coo[i] = img_coo

            dataset["img_coo_to_idx"] = new_img_coo_to_idx
            dataset["idx_to_img_coo"] = new_idx_to_img_coo

            # =================================================================

        self.pushDataset(dataset, name)

        # =======================================================================
        # On le fait ici car on utilise des outils utilisant l'objet datasets.py
        # TODO: un peus sale...
        # =======================================================================
        if not "default_representations" in args:
            self.representations.createDefaultRepresentationForDataset(name)


    def getIndicesToTakeFromBaseForNewDatasetCreation(self, ds_base_name, included_groups, excluded_groups, i_min,
                                                      i_max):
        """
        Return list of indexes to keep in ds_base based on included/excluded groups and i_min/i_max
        indices correspondants aux groupes selectionnes
        si la liste des groupes a inclure est vide, on prend tous les indices
        dans la limite de i_min, i_max
        """

        included_indexes = []
        excluded_indexes = []

        ds_base = self.mcData.datasets.getDataset(ds_base_name)

        # ================== indices inclus exclusivement ===================

        if not included_groups:
            included_indexes = list(range(i_min, i_max))

        else:
            for group_name in included_groups:

                group_idxs = ds_base["groups"][group_name]["indexes"]

                for g_idx in group_idxs:
                    included_indexes.append(g_idx)

        # on enleve les eventuels elements presents plusieurs fois
        included_indexes = np.unique(np.array(included_indexes))

        # ===================== indices exclus ==============================

        for group_name in excluded_groups:

            group_idxs = ds_base["groups"][group_name]["indexes"]

            for g_idx in group_idxs:
                excluded_indexes.append(g_idx)

        excluded_indexes = np.unique(np.array(excluded_indexes))

        # ============ Total des indices a selectionner =====================
        # On filtre ceux qui ne sont pas dans i_min_i_max et ceux etant dans
        # la liste excluded_indices

        print("included indexes count: ", len(included_indexes))
        print("excluded indexes count: ", len(excluded_indexes))

        #==============================================================================
        # Indices des points à garder
        #===============================================================================
        # version list_comprehension, plus clair mais moins rapide, et on ne peux pas suivre l'evolution
        # indices = [i for i in included_indexes if (i not in excluded_indexes) and i >= i_min and i <= i_max]

        included_indexes = np.array(included_indexes)
        excluded_indexes = np.array(excluded_indexes)

        #elements presents dans include ET absents de exclude
        in_include_and_not_in_exclude_mask = ~np.in1d(included_indexes, excluded_indexes)
        indices = included_indexes[in_include_and_not_in_exclude_mask]

        # elements >= i_min et <=i_max
        indices = indices[indices >= i_min]
        indices = indices[indices <= i_max]
        indices = indices.tolist()

        return indices

    def getDataset(self, ds_name = None):
        return self.mcData.datasets.getDataset(ds_name)

    def getSpatiallyBinnedDataset(self, dataset, x_bin, y_bin, progress_callback = None):
        """
        Bin dataset on x and y depending of x_bin y_bin
        ds is a slicy dataset dict
        indexes_layout is "left_to_right_line_by_line" by default

        :return X_binned, xys_binned
        """

        mc_logging.info("Creating spatially binned dataset (x_bin, y_bin) = (%d, %d)" % (x_bin, y_bin))

        ds = dataset

        w = ds["width"]
        h = ds["height"]

        W = ds["W"]
        X = ds["X"]
        xys = ds["xys"]

        width_binned  = w // x_bin
        height_binned = h // y_bin

        sp_number_binned = width_binned * height_binned

        # ======================================================================
        # Create containers
        # ======================================================================
        X_binned   = self.mcData.workFile.getTempHolder((sp_number_binned, len(W)))
        xys_binned = self.mcData.workFile.getTempHolder((sp_number_binned, 2))


        counter = 0

        for col in range(width_binned):

            for line in range(height_binned):

                if col % 30 == 0: print(".", end=' ')

                o_colmin = col * x_bin
                o_colmax = o_colmin + x_bin

                o_linemin = line * y_bin
                o_linemax = o_linemin + y_bin

                indices_to_sum  = ds["img_coo_to_idx"][o_linemin: o_linemax, o_colmin: o_colmax]
                indices_count   = np.count_nonzero(~np.isnan(indices_to_sum))

                binned_spectrum = np.zeros(shape = (len(W),), dtype = np.float16)

                for i in np.nditer(indices_to_sum):

                    if not np.isnan(i):
                        # TODO, i devrait deja etre un entier
                        binned_spectrum = binned_spectrum + X[int(i)]

                # Normalisation
                binned_spectrum = binned_spectrum / indices_count

                # La nouvelle façon de ranger est arbitraire, on choisi left_to_right_line_by_line
                indice_in_binned_dataset = col + line * width_binned

                X_binned[indice_in_binned_dataset] = binned_spectrum

                #TODO, probleme avec les données non completes et les Nan pour ces deux indices
                top_left_idx = int(ds["img_coo_to_idx"][o_linemin, o_colmin])
                top_left_idx = int(top_left_idx)

                xys_binned[indice_in_binned_dataset] = xys[top_left_idx]

                counter += 1

                if progress_callback: progress_callback(100. * counter / sp_number_binned)

        if progress_callback: progress_callback(-1)

        mc_logging.info("Binning done")

        return X_binned, xys_binned


    def createNewDatasetFromUserParameters(self, args):

        ds_name = args["ds_name"]
        ds_base_name = args["ds_base_name"]
        color = args["color"]
        x_min = args["x_min"]
        x_max = args["x_max"]
        i_min = args["i_min"]
        i_max = args["i_max"]
        spatial_xbin = args["spatial_xbin"]
        spatial_ybin = args["spatial_ybin"]
        spectral_xbin = args["spectral_xbin"]
        included_groups = args["included_groups"]
        excluded_groups = args["excluded_groups"]
        included_channels = np.array(args["included_channels"])
        excluded_channels = np.array(args["excluded_channels"])
        callback_progress = args["callback_progress"]
        callback_done = args["callback_done"]
        normalize_method = args["normalize_method"]

        # for k,v in args:
        #    locals()[k] = v

        ds_base = self.mcData.datasets.getDataset(ds_base_name)

        # ===================================================================
        #       indices correspondants aux groupes selectionnes
        # ===================================================================
        print("before getIndicesToTakeFromBaseForNewDatasetCreation")

        indices = self.getIndicesToTakeFromBaseForNewDatasetCreation(ds_base_name,
                                                                     included_groups,
                                                                     excluded_groups,
                                                                     i_min, i_max)
        print("after getIndicesToTakeFromBaseForNewDatasetCreation")
        # ===================================================================
        #  On affiche une erreur et on quitte le dialog si 0 spectres
        # ===================================================================
        if len(indices) == 0:
            error = "Current selection contains 0 spectrum, dataset creation aborted"
            return

        # ===================================================================
        # On crée le nouveau jdd
        # ===================================================================
        wb = ds_base["W"][:]
        wb_num = self.mcData.datasets.getNumericVersionOfW(ds_base_name)[:]


        # =================================================================
        # on filtre par canal si demandé
        # =================================================================
        complete_idxs_list = np.array(list(range(len(wb))))

        #On prend tout, sauf si des channels sont selectionnés dans la gui
        channels_idxs = complete_idxs_list

        if len(included_channels) > 0:
            # on prend les cannaux qui sont dans included et pas dans excluded
            in_include_and_not_in_exclude = ~np.in1d(included_channels, excluded_channels)
            channels_idxs = included_channels[in_include_and_not_in_exclude]


        elif len(excluded_channels) > 0:
            in_include_and_not_in_exclude = ~np.in1d(complete_idxs_list, excluded_channels)
            print("in_include_and_not_in_exclude2:", in_include_and_not_in_exclude)
            channels_idxs = complete_idxs_list[in_include_and_not_in_exclude]

        print("channels_idxs:", channels_idxs)

        #on en fait un mask
        channels_mask = np.array([False for _ in complete_idxs_list])
        channels_mask[channels_idxs] = True

        channels_range = np.all([wb_num >= x_min, wb_num <= x_max], axis = 0)

        print("channels_range:", channels_range)

        spectral_mask = np.logical_and(channels_mask, channels_range)

        #TODO: bloquer dans la GUI le masque spectral si on demande un binning
        if spectral_xbin > 1:
            new_W = wb[::spectral_xbin]
        else:
            new_W = wb[spectral_mask]

        print("spectral_mask:", spectral_mask)
        print("new_W", new_W)
        print("len(new_W)",len(new_W))
        print("wb:", wb)


        holderShape = (len(indices), len(new_W))

        print("holderShape:", holderShape)

        spectrums = self.mcData.workFile.getTempHolder(datasetShape = holderShape)
        print("after getTempHolder")

        print("filling array...")
        for i, sp_index in enumerate(indices):

            if spectral_xbin == 1:
                spectrums[i] = ds_base["X"][sp_index][spectral_mask]
            # =================================================================
            # Binning spectral
            # =================================================================
            else:
                spectrums[i] = np.sum([ds_base["X"][sp_index][k::spectral_xbin] for k in range(spectral_xbin)], 0)

            callback_progress(100 * i % len(indices))

        print("done filling array")

        xys = ds_base["xys"][indices]

        # =====================================================================
        # Si on veux un binning spatial, on passe par un dataset intermediaire
        # =====================================================================
        if (spatial_xbin > 1 or spatial_ybin > 1):
            temp_ds_name = ds_name + "_tmp(not binned)"
            spatial_binning = True
        else:
            temp_ds_name = ds_name
            spatial_binning = False

        print("debug spatial_binning:", spatial_binning)

        # =================================================================
        # on ajoute une entrée temporaire sur le dictionnaire des datasets.py
        # =================================================================
        self.addDatasetToDict(name = temp_ds_name,
                              W = new_W,
                              datas = spectrums,
                              xys = xys,
                              base_dataset = ds_base,
                              args = {},
                              indices_in_base_dataset = indices,
                              xys_base_dataset = ds_base["xys"],
                              color = color.getRgb(),
                              normalize_method = normalize_method,
                              callback_progress = callback_progress)

        # =================================================================
        # Binning Spatial
        # =================================================================
        if spatial_binning:
            ds_to_bin = self.mcData.datasets.getDataset(temp_ds_name)

            X_binned, xys_binned = self.getSpatiallyBinnedDataset(ds_to_bin,
                                                                  spatial_xbin,
                                                                  spatial_ybin,
                                                                  progress_callback = callback_progress)

            # ====================================================================
            # On supprime le dataset intermediaire
            # ====================================================================
            self.removeDataset(temp_ds_name)

            print("X_binned", X_binned)
            print("shape:", X_binned.shape)

            # ====================================================================
            # Et on cree le nouveau
            # ====================================================================
            self.addDatasetToDict(name = ds_name,
                                  W = new_W,
                                  datas = X_binned,
                                  xys = xys_binned,
                                  args = {"indexes_layout": "left_to_right_line_by_line", "color": color},
                                  color = color.getRgb(),
                                  normalize_method = normalize_method,
                                  callback_progress = callback_progress)


        # =================================================================
        # On enregistre la relation entre ces jdd derives
        # =================================================================
        self.coordinates.setTransformationMatrixToIdentity(ds_base_name, ds_name)

        # ==================================================================
        # On met à jour de l'affichage
        # ==================================================================
        callback_progress(-1)
        callback_done(ds_name)