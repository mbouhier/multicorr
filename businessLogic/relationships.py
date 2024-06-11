from businessLogic.representations import MCBusinessLogic_representations

class MCBusinessLogic_relationships(object):

    def __init__(self, mcData):
        #super(MCBusinessLogic_relationships, self).__init__()
        print(type(self).__name__ + " initialized")
        self.mcData = mcData

    def prepareDsMatcherDatas(self, progress_callback = None):

        """
        Mise en forme des informations sur les datasets.py chargés pour être
        envoyées à DatasetMatcher
        """
        datasets      = self.mcData.datasets
        relationships = self.mcData.relationships.relationships_dict
        bl_representations = MCBusinessLogic_representations(self.mcData)

        ds_infos = dict()

        # ==================================================================
        #      Nombre de representations totales à preparer
        # ==================================================================
        if progress_callback:
            progress_callback(0)

            total_repr_count = 0
            repr_counter     = 0

            for ds_name in datasets.names():
                total_repr_count += bl_representations.count(ds_name)

            print("total representations number:", total_repr_count)

        for i, ds_name in enumerate(datasets.names()):
            # ==================================================================
            #      On compile quelques infos sur le jdd
            # ==================================================================
            ds = datasets.getDataset(ds_name)

            ds_infos[ds_name] = dict()

            # TODO: creer un vrais uid, a partir du nom de fichier et de sa taille

            # pendant le chargement du jdd par exemple??
            ds_infos[ds_name]["uid"] = ds["uid"]

            #print(("for '%s', xdata sent to matcher:" % (ds_name), ds["x_range"]))
            #print(("for '%s', ydata sent to matcher:" % (ds_name), ds["y_range"]))

            ds_infos[ds_name]["xdata"] = ds["x_range"]
            ds_infos[ds_name]["ydata"] = ds["y_range"]

            # ==================================================================
            #      On charge les representations existantes du jdd
            # ==================================================================
            representations = dict()

            for family_name, repr_name in bl_representations.getAvailableRepresentations(ds_name):

                if progress_callback:
                    repr_counter += 1
                    progress_callback(100.*repr_counter/total_repr_count)

                explicit_name = "%s - %s" % (family_name, repr_name)

                image = bl_representations.getRepresentationImage(ds_name,
                                                                  family_name,
                                                                  repr_name,
                                                                  version = "rgb")

                #print("image.shape for", repr_name, image.shape)

                #                pl.figure(explicit_name)
                #                pl.imshow(image)
                #                pl.show()

                representations[explicit_name] = {'image': image}

            ds_infos[ds_name]["representations"] = representations

            # ==================================================================
            #
            # ==================================================================

        if progress_callback: progress_callback(-1)

        return ds_infos, relationships

    def getAvailableRelationships(self):
        """
        Return datasets.py relationships
        """
        ds_names = []

        # print "inside getAvailableRelationships:",self.mcData.relationships.keys()

        for k in list(self.mcData.relationships.relationships_dict.keys()):

            a, b = k.split(",")

            if a not in ds_names: ds_names.append(a)
            if b not in ds_names: ds_names.append(b)

        return ds_names

    def getReconstructedDataset(self, ds1_name, ds2_name, overlap_ratio_threshold):
        # return a syntetic dataset based on overlap of ds2 on ds1, result has the same size and coordinate as ds1
        # points with an overlap_ratio < overlap_ratio_threshold are not taken into account

        reconstructed_ds = dict()

        ds1 = self.mcData.datasets.getDataset(ds1_name)
        ds2 = self.mcData.datasets.getDataset(ds2_name)

        reconstructed_ds["W"]   = ds1["W"]
        reconstructed_ds["xys"] = ds1["xys"]
        reconstructed_ds["X"]   = ds1["W"]

        return reconstructed_ds
