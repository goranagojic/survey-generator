from sqlalchemy import Column, Integer, String, Enum, select
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from pathlib import Path

from utils.database import Base, session
from utils.logger import logger


class Image(Base):
    __tablename__ = "image"
    id       = Column(Integer, primary_key=True, autoincrement=True)
    root     = Column(String, nullable=False)
    filename = Column(String(50), nullable=False, unique=True)
    dataset  = Column(String, nullable=False)

    questions = relationship("QuestionType1", back_populates="image")

    @hybrid_property
    def name(self):
        """
        Name of the file without a file extension.
        """
        return self.filename[:self.filename.rfind('.')]

    def __init__(self, filepath):
        # filepath treba da izgleda:
        #     /neka/putanja/do/npr/DRIVE/000123.png ili
        #     /neka/putanja/do/npr/STARE/000123.png
        filepath = Path(filepath)
        self.filename = filepath.name
        self.dataset = filepath.parent.name
        self.root = str(filepath.parent.parent)

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
        logger.info(f"Image extensions to be loaded {extensions}.")
        logger.info(f"Loading images from {directory}...")

        img_paths = Path(directory).glob("*")
        if extensions is not None or len(extensions) != 0:
            images = [Image(img_path) for img_path in img_paths if img_path.suffix.lower() in extensions]
        else:
            images = [Image(img_path) for img_path in img_paths]
        logger.info(f"Loaded {len(images)} images.")

        Images.bulk_insert(images)      # add new images to database
        logger.info(f"Inserted {len(images)} into the database.")

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
