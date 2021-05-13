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
    name   = Column(String, nullable=False)
    token  = Column(String, nullable=False, unique=True)

    images = relationship("Image", secondary=association_table, back_populates="diseases")

    def __init__(self, name, token):
        self.name = name
        self.token = token

    def __repr__(self):
        return "<Disease (\n\tid: '{}',\n\tname: '{}',\n\ttoken: '{}'\n\t)>".format(
            str(self.id),
            self.name,
            self.token
        )

    def __str__(self):
        return self.token


class Diseases:

    @staticmethod
    def insert(name, token):
        results = session.query(Disease).where(Disease.token == token).all()
        if results is None or len(results) == 0:
            d = Disease(token=token, name=name)
            try:
                session.add(d)
            except:
                session.rollback()
            finally:
                session.commit()
                return d
        else:
            logger.warning(f"Disease with a name {token} already exists in a database. A duplicate will not be "
                           f"inserted.")
            return results[0]

    @staticmethod
    def get_by_token(token):
        return session.query(Disease).where(Disease.token == token).one()

    @staticmethod
    def get_all():
        return session.query(Disease).all()

