from helpers.io.datasetsImporter import DatasetsImporter
from scipy.interpolate import interp1d
import matplotlib.pyplot as pl
import h5py
import numpy as np


def euclidian_distance(Q, C, precomputed_CE_Q=None, precomputed_CE_C=None):
    """
    Give similarity distance based on complexity invariance
    "A Complexity-Invariant Distance Measure for Time Series" Gustavo E.A.P.A. Batista
    """

    if precomputed_CE_Q is not None:
        CE_Q = precomputed_CE_Q

    else:
        CE_Q = np.sqrt(sum(np.diff(Q) ** 2))

    if precomputed_CE_C is not None:
        CE_C = precomputed_CE_C

    else:
        CE_C = np.sqrt(sum(np.diff(C) ** 2))

    return np.sqrt(sum((Q - C) ** 2)) * 1


def complexity_invariant_distance(Q, C, precomputed_CE_Q=None, precomputed_CE_C=None):
    """
    Give similarity distance based on complexity invariance
    "A Complexity-Invariant Distance Measure for Time Series" Gustavo E.A.P.A. Batista
    """

    if precomputed_CE_Q is not None:
        CE_Q = precomputed_CE_Q

    else:
        CE_Q = np.sqrt(sum(np.diff(Q) ** 2))

    if precomputed_CE_C is not None:
        CE_C = precomputed_CE_C

    else:
        CE_C = np.sqrt(sum(np.diff(C) ** 2))

    return np.sqrt(sum((Q - C) ** 2)) * (max(CE_Q, CE_C) / min(CE_Q, CE_C))








#=====================================================================
# Chargement du jdd
#=====================================================================

filename = "\\\\crabe\\communs\\LIDyL\\PCR\\Mickael Bouhier\\clustering_git_pyqt5_python3_latest\\4_cartos_robin_pour_analyse_mcr_sm_to_clean.h5"

ds_names = ["zone1_article_nf20_asls_sm",
            "zone2_article_nf20_asls_sm",
            "Gx400_nf20_asls_sm",
            "170405_amXIVE_nf20_asls_sr_sm",
            "Zone1_article_p5_50s_200900_nc_binning_128x96_sm_nf50_asls",
            "Zone1_article_p5_50s_200900_nc_binning_128x96_sm"
            ]
# ds_index = 5
# comp = h5py.File(filename, 'r')
# datasetname = ds_names[ds_index]

filename = "\\\\crabe\\communs\\LIDyL\\PCR\\Mickael Bouhier\\clustering_git_pyqt5_python3_latest\\mc_export_zone1_article_nf20_asls_sm_trunc.h5"
filename = "\\\\crabe\\communs\\LIDyL\\PCR\\Mickael Bouhier\\clustering_git_pyqt5_python3_latest\\fichiers mcr\\zone 2\\mc_export_Zone2_article_p5_50s_200900_nc_binning_128x96_sm.h5"
comp = h5py.File(filename, 'r')
datasetname = "dataset"


ds = {"W":   comp[datasetname]['W'],
      "X":   comp[datasetname]['X'],
      "xys": comp[datasetname]['xys']}

#=====================================================================
#   Spectres de references
#=====================================================================
refs_dir = "\\\\crabe\\communs\\LIDyL\\PCR\\Mickael Bouhier\\clustering_git_pyqt5_python3_latest\\bin\\ref_spectra\\"

# filenames = [refs_dir + "G3_ex_300s_Po5zap.wxd",
#              refs_dir + "G12_300s.wxd",
#              refs_dir + "Akaganeite_zap.wxd",
#              refs_dir + "Lepido_500s_zap.wxd",
#              #refs_dir + "Maghemite_300s.wxd",
#              refs_dir + "Magnetite_zap.wxd",
#              #refs_dir + "Hematite.wxd",
#              #refs_dir + "Wustite_300s.wxd",
#              refs_dir + "FH6R_2x300_zap.wxd",
#              ]

filenames = [refs_dir + "G3_ex_300s_Po5zap_AsLS_p0.001_50000.h5",
             refs_dir + "G12_300s.wxd_AsLS_p0.001_50000.h5",
             refs_dir + "Akaganeite_zap_AsLS_p0.001_50000.h5",
             refs_dir + "Lepido_500s_zap_AsLS_p0.001_50000.h5",
             #refs_dir + "Maghemite_300s.wxd",
             #refs_dir + "Magnetite_zap.wxd",
             #refs_dir + "Hematite.wxd",
             #refs_dir + "Wustite_300s.wxd",
             refs_dir + "FH2R_LL_2x300_zap_AsLS_p0.001_50000.h5",
             ]

importer = DatasetsImporter()

references = {}


for filename in filenames:
    try:
        spectrums, W, xys, args = importer.loadFile(filename, qt_mode = False)

    except IOError as e:
        print(("Error: Can't open", filename))
        print(e)
        continue

    if len(spectrums) != 1:
        print("Error: Reference data must have only one spectrum by file")
        continue

    try:
        f = interp1d(W, spectrums[0], kind='linear')
        interpolated_spectrum = f(ds["W"])

    except Exception as e:
        print("Error: Can't interpolate data")
        print("Can't interpolate data, reference spectral range [%.2f,%.2f] must contain [%.2f,%.2f]" % (W[0], W[-1], ds["W"][0], ds["W"][-1]))
        continue

    references[filename.split("\\")[-1]] = interpolated_spectrum


figure = pl.figure()

n_first = 3
col_nb = n_first + 1
row_nb = len(references)

print(references.keys())
print("col_nb:",col_nb)
print("row_nb:",row_nb)


#=====================================================================
#   Comparaisons
#=====================================================================

#normalisation des refs (sum)
references_normalized = {filename: spectrum/np.sum(spectrum) for filename, spectrum in references.items()}

for index,(ref_filename, ref_spectrum) in enumerate(references_normalized.items()):
    pl.subplot(row_nb, col_nb, 1 + index*col_nb)
    pl.plot(ds["W"], ref_spectrum, 'g')
    pl.title(ref_filename, size=8)
    # pour la lisibilité
    if index != len(references_normalized) - 1:
        pl.xticks([])

#normalisation des spectres du ds
spectrums_max = np.sum(ds["X"], axis = 1)

print("spectrums_max",spectrums_max)
ds["X_norm"] = ds["X"]/spectrums_max[:,None]


residuals = np.zeros((len(ds["X"]),len(references)))

for i,(filename, spectrum) in enumerate(references_normalized.items()):
    d1 = ds["X_norm"] - spectrum
    d2 = ds["X_norm"]
    #residuals[:,i] = np.sqrt(np.sum(d1**2, axis = 1)/np.sum(d2**2, axis = 1))
    residuals[:, i] = np.sum(d1**2, axis = 1)




print("closest spectrum indexes:")


for index,_ in enumerate(references_normalized):

    #closest_spectrum_index = np.argmin(residuals[:, index], axis=0)
    closest_spectrum_indexes = np.argsort(residuals[:, index], axis = 0)

    print("  - for ref {}: {}".format(index,closest_spectrum_indexes[0]))


    for smalest_id in range(n_first):

        spectrum_index = closest_spectrum_indexes[smalest_id]

        #print("closest_spectrum_index #{} for {}: {}".format(smalest_id, ref_filename, spectrum_index ))

        plot_id = 2 + smalest_id + index*col_nb

        pl.subplot(row_nb, col_nb, plot_id)

        pl.plot(ds["W"], ds["X_norm"][spectrum_index])

        pl.title("spectrum #{} r:{:.2f}".format(spectrum_index, residuals[spectrum_index, index]), size=8)

        #pour la lisibilité
        if index != len(references_normalized) - 1:
            pl.xticks([])


pl.show()