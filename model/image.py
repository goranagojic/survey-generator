import json

from sqlalchemy import Column, Integer, String, Table, Enum, select, func, and_
from sqlalchemy.orm import relationship
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.hybrid import hybrid_property
from pathlib import Path

from utils.database import Base, session
from model.disease import Disease, Diseases, association_table, ForeignKey
from utils.logger import logger


image_qtype2 = Table('image_qtype2', Base.metadata,
                          Column("image_id", Integer, ForeignKey("image.id")),
                          Column("question_id", Integer, ForeignKey("qtype2.id")))


class Image(Base):
    __tablename__ = "image"
    id        = Column(Integer, primary_key=True, autoincrement=True)
    root      = Column(String, nullable=False)
    filename  = Column(String(50), nullable=False, unique=True)
    dataset   = Column(String, nullable=False)
    group_id  = Column(Integer, nullable=True)
    type      = Column(String, nullable=True)

    questions    = relationship("QuestionType1", back_populates="image")
    questions_t2 = relationship("QuestionType2", secondary=image_qtype2, back_populates="images")
    diseases     = relationship("Disease", secondary=association_table, back_populates="images")

    @hybrid_property
    def name(self):
        """
        Name of the file without a file extension.
        """
        return self.filename[:self.filename.rfind('.')]

    def __init__(self, filepath, gid=None):
        # filepath treba da izgleda:
        #     /neka/putanja/do/npr/DRIVE/000123.png ili
        #     /neka/putanja/do/npr/STARE/000123.png
        filepath = Path(filepath)
        self.filename = filepath.name
        self.dataset = filepath.parent.name
        self.root = str(filepath.parent.parent)
        self.image_group_id = gid

    def __repr__(self):
        return "<Image (\n\tid: '{}',\n\troot: '{}',\n\tdataset: '{}',\n\tfilename: '{}',\n\tquestions: '{}'\n)>".format(
            str(self.id),
            self.root,
            self.dataset,
            self.filename,
            str(len(self.questions))
        )


class Images:

    @staticmethod
    def get_dataset_image_dims(dataset):
        """
        Returns tuple (width, height) for
        :param dataset:
        :return:
        """
        if dataset.lower() == "drive":
            # return 395, 414
            return 415, 434
            # return 565, 584
        elif dataset.lower() == "stare":
            return 400, 305
            # return 700, 605
        elif dataset.lower() == "chase":
            # return 999, 960
            return 399, 368
        else:
            logger.error(f"Cannot find dimensions for the images in dataset. Unknown dataset {dataset}.")
            raise ValueError(f"Cannot find dimension for the images in dataset. Unknown dataset {dataset}.")

    @staticmethod
    def insert(image):
        try:
            session.add(image)
        except:
            session.rollback()
            raise
        else:
            session.commit()

    @staticmethod
    def bulk_insert(images):
        try:
            [session.add(image) for image in images]
        except:
            session.rollback()
            raise
        else:
            session.commit()

    @staticmethod
    def update(image):
        try:
            session.merge(image)
        except:
            session.rollback()
            raise
        else:
            session.commit()

    @staticmethod
    def delete(image):
        raise NotImplementedError

    @staticmethod
    def get_all():
        return session.query(Image).all()

    @staticmethod
    def get_max_image_group():
        """
        Get maximum group ID based on images already in a database. If none of the images
        have an associated ID, zero is returned.

        :return: Maximal image group ID associated with images inserted into the database.
        """
        max_group_id = session.query(func.max(Image.group_id)).scalar()
        if max_group_id is None:
            max_group_id = 0
        return max_group_id

    @staticmethod
    def get_min_image_group():
        """
        Get minimum group ID based on images already in a database. If none of the images have an
        associated ID, None is returned.

        :return: Minimal image group ID associated with images inserted into the database.
        """
        return session.query(func.min(Image.group_id)).scalar()

    @staticmethod
    def load_images(directory, extensions):
        """
        Loads images with specific file extensions from a given directory. For each image
        an object of Image class is created and added to the `images` collection. If the
        collection is not empty, newly created Image objects are appended to the collection.

        :param directory: Path of str object pointing to the directory containing images.
        :param extensions: A list of valid image extensions with dot, e.g. [".png", ".jpg"].
            Extension list is case insensitive.
        :return:
        """
        if type(directory) is not Path:
            directory = Path(directory)

        if not directory.exists():
            logger.error(f"Cannot load images because directory {directory} does not exist.")
            raise NotADirectoryError(f"Cannot load images because directory {directory} does not exist.")

        # all extensions to lowercase
        extensions = [ext.lower() for ext in extensions]
        extensions = extensions[0]
        logger.info(f"Image extensions to be loaded {extensions}.")
        logger.info(f"Loading images from {directory}...")

        img_paths = Path(directory).glob("*")
        if extensions is not None or len(extensions) != 0:
            images = [Image(img_path) for img_path in img_paths if img_path.suffix.lower() in extensions]
        else:
            images = [Image(img_path) for img_path in img_paths]
        logger.info(f"Loaded {len(images)} images.")

        if len(images) != 0:
            metadata_file = Path(directory).resolve() / (images[0].dataset.lower() + ".json")
            logger.info(f"Trying to load image metadata from a file {metadata_file}.")
            if not (metadata_file.exists() and metadata_file.is_file()):
                logger.warning(f"Metadata file {metadata_file} not found or is not a file! Skipping image metadata "
                               f"loading.")
            else:
                Images._load_image_metadata(images=images, metadata_filepath=metadata_file)
                logger.info(f"Successfully loaded image metadata.")

        Images.bulk_insert(images)      # add new images to database
        logger.info(f"Inserted {len(images)} images into the database.")

    @staticmethod
    def _load_image_metadata(images, metadata_filepath):
        """
        Load image metadata from a metadata file.

        File stores metadata per image per line. Each line starts with full or partial image name that is followed with
        metadata separated by commas.

        E.g.
            000000,diabetic_retinopathy,vein_occlusion
        where 000000 is part of the image filename, and `diabetic_retinopathy` and `vein_occlusion` are two metadata
        strings for the image.

        :param images: Images for which to load metadata.
        :param metadata_filepath: Relative or absolute path to the metadata file.
        :return: None
        """

        with open(metadata_filepath, "r") as metf:
            metadata = json.load(metf)

        for image_metadata in metadata:
            for image in images:
                image_diseases = list()
                if image_metadata["image_name"] in image.name:
                    # process disease data
                    try:
                        diseases = image_metadata["diseases"]
                        if diseases is not None and len(diseases) != 0:
                            for disease in diseases:
                                d = Diseases.insert(name=disease["name"], token=disease["token"])
                                image_diseases.append(d)
                            image.diseases = image_diseases
                    except KeyError:
                        image.diseases = None

                    # process image group data if it exist
                    try:
                        group_id = int(image_metadata["group"])
                        if group_id is not None:   # image doesn't necessarily belong to any group
                            image.group_id = group_id + Images.get_max_image_group()
                    except KeyError:
                        image.group_id = None

                    # get image type if exists for the image
                    try:
                        type = image_metadata["type"]
                        if type is not None:        # image type can be unknown
                            image.type = type
                    except KeyError:
                        image.type = None

    @staticmethod
    def get_whole_group(gid):
        """

        :param gid:
        :return:
        """
        images = session.query(Image).where(Image.group_id == gid).all()
        if len(images) == 0:
            return None
        return images

    @staticmethod
    def get_by_name(image_filenames):
        """

        :param image_filenames:
        :return:
        """
        logger.info(f"Load from database images with names {image_filenames}.")
        filters = []
        for filename in image_filenames:
            filters.append(Image.filename == filename)
        return session.query(Image).filter(*filters).all()

    @staticmethod
    def get_original_for_segmap(segmap):
        """
        Searches for the original color image in a database for a corresponding segmentation mask. It is assumed that
        the segmentaion mask is named similar to the pattern: <number>-<network>-<dataset>.<extension> and that the
        original is named like <number>.<extension>

        :param segmap: An instance of Image class representing a segmentation map with filename similar to
            <number>-<network>-<dataset>.
        :return:
        """
        assert segmap is not None
        filename = segmap.filename.split('-')[0]    # for segmentation mask filename like <number>-<network>-<dataset>
                                                    # extracts <number> and uses it to query for the original image of
                                                    # that name

        try:
            return session.query(Image).where(and_(Image.type == "original", Image.filename.contains(filename))).one()
        except NoResultFound:
            print(f"I cannot find an original for a segmentation map {segmap.filename}.")
