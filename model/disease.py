from utils.database import Base, session

from sqlalchemy import Column, Integer, String, ForeignKey


class Disease(Base):
    __tablename__  = "disease"

    id       = Column(Integer, primary_key=True, autoincrement=True)
    name     = Column(String, nullable=False)
    image_id = Column(Integer, ForeignKey("image.id"))

    def __init__(self, name):
        self.name = name

