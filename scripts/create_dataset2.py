#######################################################
# Pseudo-algorithm for to collect images for a dataset
#######################################################
# minMCCs = []
# medMCCs = []
# maxMCCs = []
# for (img, gnd, msk) in all_non_transformed_images:
#     mccs = []
#     i = 0
#     for net in networks:
#         rez = getMapForImage(img, msk, net)
#         m = mcc(rez, gnd)
#         mccs.append((i,m))
#     mini = getMinimal(mccs)
#     medi = getMedian(mccs)
#     maxi = getMaximal(mccs)
#     minMCCs.append(all_non_transformed_images[mini])
#     medMCCs.append(all_non_transformed_images[medi])
#     maxMCCs.append(all_non_transformed_images[maxi])
#
# candidates = miniMCCs + mediMCCs + maxMCCs
# zaAnketu = []
# for net in networks:
#     for (img,gnd,msk) in candiadates:
#         rez = getMapForImage(img, msk, net)
#         zaAnketu.append(rez)

import imageio
import numpy as np
import statistics

from glob import glob
from pathlib import Path
from sklearn.metrics import matthews_corrcoef


def get_data(source, dtype=np.uint8):
    """
    Ucitava sadrzaj datoteke cija je putanja zadata putem <source> parametra i vraca ucitani sadrzaj kao numpy niz.

    :param source: Putanja do datoteke koja se cita. Moze biti str ili Path objekat.
    :param dtype:  Tip podatka koji ce se koristiti za elemente numpy niza. Ako se nista ne zada, tip ce biti np.uint8.

    :return: numpy niz koji predstavlja sadrzaj datoteke na <source> putanji.
    """
    if type(source) is not Path:
        source = Path(source)
    if not source.exists():
        raise ValueError(f"Datoteka na putanji {source} ne postoji.")
    if source.is_dir():
        raise ValueError(f"Na putanji {source} se nalazi direktorijum, ne datoteka.")
    return np.array(imageio.imread(source), dtype=dtype)


def get_label_path(dataset, image_name):
    """
    Vraca putanju do labele za zadati set podataka i putanju do slike. Trenutno funkcija samo menja ekstenziju
    stringa prosledjenog za parametar <image_name>.

    :param dataset:     Set podataka, ocekivano drive, stare ili chase. case insensitive.
    :param image_path:  Putanja do slike za koju se trazi labela, tj. groundtruth slika.

    :return: Vraca Path objekat koji predstavlja ocekivani naziv labele.
    """
    if type(image_name) is not Path:
        image_name = Path(image_name)

    if dataset.lower() == "drive":
        return image_name.with_suffix(".png")
    elif dataset.lower() == "stare":
        return image_name.with_suffix(".ppm")
    else:
        return image_name.with_suffix(".png")


def get_mask_path(dataset, image_name):
    """
    Vraca putanju do maske za zadati set podataka i putanju do slike. Trenutno funkcija samo menja ekstenziju
    stringa prosledjenog za parametar <image_name>.

    :param dataset:     Naziv seta podataka. Ocekivano drive, stare ili chase, case insensitive.
    :param image_name:  Naziv slike - naziv datoteke sa ekstenzijom.

    :return: Vraca Path objekat koji predstavlja ocekivani naziv maske.
    """
    if type(image_name) is not Path:
        image_name = Path(image_name)

    if dataset.lower() == "drive":
        return image_name.with_suffix(".png")
    elif dataset.lower() == "stare":
        return image_name.with_suffix(".png")
    else:
        return image_name.with_suffix(".png")


def calculate_mcc(segmentation_mask, groundtruth):
    """
    Calculates MCC value for a segmentation mask and a groundtruth image.

    Both mask an image must be numpy arrays of same dimensionality. Arrays are then flattened to 1D
    numpy array and sklearn matthews_corrcoef function is used to calculate MCC value.

    :param segmentation_mask:
    :param groundtruth:
    :return:
    """
    assert segmentation_mask.shape == groundtruth.shape
    segmentation_mask = segmentation_mask.flatten()
    groundtruth = groundtruth.flatten()

    return matthews_corrcoef(segmentation_mask, groundtruth)


def get_median(values):
    """
    Sortira vrednosti u nizu i racuna median. U slucaju da niz ima neparan broj elemenata, medijan je element
    na indeksu len(values) // 2 + 1. U slucaju parnog broja elemenata, kao medijan vraca element na indeksu
    len(values) // 2 (veci od dva len(values) // 2 i len(values) // 2 - 1 sto je ciji je prosek standardna
    definicija medijana).

    :param values: Niz razlomljenih vrednosti.
    :return: Medijan vrednost.
    """
    sorted(values)
    if len(values) % 2 == 0:
        index = len(values) // 2 + 1
    else:
        index = len(values) // 2
    return values[index]


if __name__ == '__main__':

    DRIVE_IMAGE_PATH = "/home/gorana/PycharmProjects/SurveyGenerator/survey-generator/images/dataset2/drive/images"
    STARE_IMAGE_PATH = "/home/gorana/PycharmProjects/SurveyGenerator/survey-generator/images/dataset2/stare/images"
    CHASE_IMAGE_PATH = "/home/gorana/PycharmProjects/SurveyGenerator/survey-generator/images/dataset2/chase/images"
    DRIVE_LABEL_PATH = "/home/gorana/PycharmProjects/SurveyGenerator/survey-generator/images/dataset2/drive/labels"
    STARE_LABEL_PATH = "/home/gorana/PycharmProjects/SurveyGenerator/survey-generator/images/dataset2/stare/labels"
    CHASE_LABEL_PATH = "/home/gorana/PycharmProjects/SurveyGenerator/survey-generator/images/dataset2/chase/labels"
    DRIVE_MASK_PATH  = "/home/gorana/PycharmProjects/SurveyGenerator/survey-generator/images/dataset2/drive/masks"
    STARE_MASK_PATH  = "/home/gorana/PycharmProjects/SurveyGenerator/survey-generator/images/dataset2/stare/masks"
    CHASE_MASK_PATH  = "/home/gorana/PycharmProjects/SurveyGenerator/survey-generator/images/dataset2/chase/masks"
    SEG_MASKS_PATH   = "/home/gorana/PycharmProjects/SurveyGenerator/survey-generator/images/dataset2/segmentation_masks"

    NETWORKS = ["eswanet", "iternet", "iternet-uni", "laddernet", "saunet", "unet", "vesselunet", "vgan"]

    # KORAK 1 - ucitavanje groundtruth podataka i maski
    labels, masks, segmentation_masks = list(), list(), list()
    min_mccs, median_mccs, max_mccs = list(), list(), list()
    for dataset, image_dir in [("drive", DRIVE_IMAGE_PATH), ("stare", STARE_IMAGE_PATH), ("chase", CHASE_IMAGE_PATH)]:
        # dobavi putanje do svih fajlova u direktorijumu images za odgovarajuci set podataka
        files = glob(f"{image_dir}/*")
        assert len(files) != 0, f"Na putanji {image_dir} nema nikakvih datoteka."

        # za svaku datoteku (pretpostavljeno sliku)
        #   - dobavi labelu
        #   - dobavi masku
        #   - za svaku mrezu od 8 dobavi segmentacione mape za zadatu sliku
        #   - pronadji 3 segmentacione mape - sa min, median i max mcc
        for file in files:
            print(f"Ucitavam vezane podatke za sliku {file}.")
            label_name = get_label_path(dataset, Path(file).name)
            mask_name = get_mask_path(dataset, Path(file).name)

            if dataset.lower() == "drive":
                label_path = Path(DRIVE_LABEL_PATH) / label_name
                mask_path = Path(DRIVE_MASK_PATH) / mask_name
            elif dataset.lower() == "stare":
                label_path = Path(STARE_LABEL_PATH) / label_name
                mask_path = Path(STARE_MASK_PATH) / mask_name
            else:
                label_path = Path(CHASE_LABEL_PATH) / label_name
                mask_path = Path(CHASE_MASK_PATH) / mask_name

            label = get_data(source=label_path, dtype=np.uint8)
            labels.append(label)
            masks.append(get_data(source=mask_path, dtype=np.uint8))

            print(f"Ucitao labelu sa putanje {label_path}.")
            print(f"Ucitao masku sa putanje {mask_path}.")

            segmentation_masks, segmentation_mask_paths = list(), list()
            for counter, network in enumerate(NETWORKS):
                segmask_path = Path(SEG_MASKS_PATH) / dataset.upper() / network / label_name.with_suffix(".png")
                segmentation_mask_paths.append(segmask_path)
                seg_mask = get_data(segmask_path, dtype=np.uint8)
                segmentation_masks.append(seg_mask)
                print(f"{counter}. Ucitao segmentacionu mapu sa putanje {segmask_path}.")

            mccs = list()
            for seg_mask in segmentation_masks:
                mccs.append(calculate_mcc(seg_mask, label))

            min_mcc_idx = mccs.index(min(mccs))
            median_mcc_idx = mccs.index(get_median(mccs))
            max_mcc_idx = mccs.index(max(mccs))

            assert len(segmentation_masks) == len(mccs)

            min_mccs.append((segmentation_mask_paths[min_mcc_idx], segmentation_masks[min_mcc_idx]))
            median_mccs.append((segmentation_mask_paths[median_mcc_idx], segmentation_masks[median_mcc_idx]))
            max_mccs.append((segmentation_mask_paths[max_mcc_idx], segmentation_masks[max_mcc_idx]))

    candidates = min_mccs[len(min_mccs):] + median_mccs[len(median_mccs):] + max_mccs
    with open("zaAnketu.txt", "w") as f:
        for candidate in candidates:
            f.write(str(candidate[0]))
            f.write("\n")




















