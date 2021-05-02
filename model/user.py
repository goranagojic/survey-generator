from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from secrets import token_urlsafe

from utils.database import Base


class User(Base):
    __tablename__ = "user"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    name         = Column(String, nullable=False)
    access_token = Column(String, nullable=False)
    created_at   = Column(DateTime, nullable=False)

    def __init__(self, name):
        self.name = name
        self.access_token = token_urlsafe(nbytes=16)
        self.created_at = datetime.now()


class Users:
    users = list()

    @staticmethod
    def insert(user):
        raise NotImplementedError

    @staticmethod
    def update(user):
        raise NotImplementedError

    @staticmethod
    def delete(user):
        raise NotImplementedError

    @staticmethod
    def get_users():
        return Users.users