from utils.database import Base, session
from utils.logger import logger

from sqlalchemy import Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import relationship


association_table = Table('image_disease', Base.metadata,
                          Column("image_id", Integer, ForeignKey("image.id")),
                          Column("disease_id", Integer, ForeignKey("disease.id")))


class Disease(Base):
    __tablename__ = "disease"

    id     = Column(Integer, primary_key=True, autoincrement=True)
    name   = Column(String, nullable=False, unique=True)

    images = relationship("Image", secondary=association_table, back_populates="diseases")

    def __init__(self, name):
        self.name = name


class Diseases:

    @staticmethod
    def insert(disease):
        results = session.query(Disease).where(Disease.name == disease).all()
        if results is None or len(results) == 0:
            d = Disease(disease)
            try:
                session.add(d)
            except:
                session.rollback()
            finally:
                session.commit()
                return d
        else:
            logger.warning(f"Disease with a name {disease} already exists in a database. A duplicate will not be "
                           f"inserted.")
            return results[0]

