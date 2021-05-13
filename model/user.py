from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from secrets import token_urlsafe

from utils.database import Base, session
from utils.logger import logger


class User(Base):
    __tablename__ = "user"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    name         = Column(String, nullable=False)
    access_token = Column(String, nullable=False)
    created_at   = Column(DateTime, nullable=False)

    survey_results = relationship("SurveyResult", back_populates="user")

    def __init__(self, name, access_token=None):
        self.name = name
        if access_token is None:
            self.access_token = token_urlsafe(nbytes=16)
        self.created_at = datetime.now()


class Users:
    users = list()

    @staticmethod
    def insert(name, access_token=None):
        """
        Inserts new user to the database if the user with a same access token does not already exist. If the user
        already exists in a database, the entry from the database is returned and new user is not created.

        :param name: User name.
        :param access_token: User access token. Must be different from
        :return:
        """
        if access_token is None:
            results = None
        else:
            results = Users.get_user_by_access_token(access_token=access_token)

        if results is None or len(results) == 0:
            new_user = User(name=name)
            try:
                session.add(new_user)
            except:
                session.rollback()
            finally:
                session.commit()
                return new_user
        else:
            logger.warning(f"Disease with access_token {access_token} already exists in a database. "
                           f"A duplicate will not be inserted.")
            return results[0]

    @staticmethod
    def update(user):
        raise NotImplementedError

    @staticmethod
    def delete(user):
        raise NotImplementedError

    @staticmethod
    def get_users():
        """
        Returns all users.

        :return:
        """
        return session.query(User).all()

    @staticmethod
    def get_user_by_access_token(access_token):
        return session.query(User).where(User.access_token == access_token).all()
