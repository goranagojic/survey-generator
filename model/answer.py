from sqlalchemy import Column, Integer, ForeignKey, PrimaryKeyConstraint, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.orm import relationship

from utils.database import Base, session
from utils.logger import logger
from model.question import *


class Answer(Base):
    __tablename__ = "answer"

    question_id     = Column(Integer, ForeignKey('question.id'))
    user_id         = Column(Integer, ForeignKey('user.id'))
    surveyresult_id = Column(Integer, ForeignKey('survey_result.id'))
    type            = Column(Integer)
    valid_types     = Question.valid_types

    __table_args__ = (
        PrimaryKeyConstraint('question_id', 'user_id'), {}
    )
    __mapper_args__ = {
        'polymorphic_identity': 0,
        'polymorphic_on': type,
    }

    question      = relationship("Question")
    user          = relationship("User")
    survey_result = relationship("SurveyResult", back_populates="answers")

    def __repr__(self):
        return "<Answer (question_id: '{}', answered by user: '{}' in survey: {})>".format(
            self.question_id,
            self.user.name,
            self.survey_result.id
        )


class AnswerType1(Answer):
    __tablename__ = "atype1"
    __mapper_args__ = {
        'polymorphic_identity': 1
    }

    question_id = Column(Integer)
    user_id     = Column(Integer)
    disease_id  = Column(Integer, ForeignKey('disease.id'))
    certainty   = Column(Integer, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint('question_id', 'user_id'),
        ForeignKeyConstraint(
            columns=("question_id", "user_id"),
            refcolumns=("answer.question_id", "answer.user_id")
        ), {}
    )

    question = relationship("Question")
    disease  = relationship("Disease")
    user     = relationship("User")

    def __init__(self, user, question_id, disease_token=None, certainty=None):
        # get question for question_id
        question = Questions.get_by_id(question_id)
        assert question is not None
        self.question_id = question.id
        self.question = question

        if disease_token is not None:
            self.set_disease(disease_token=disease_token)

        if certainty is not None:
            self.set_certainty(certainty=certainty)

        # attach the user
        self.user = user
        self.user_id = user.id

    def set_certainty(self, certainty):
        self.certainty = certainty

    def set_disease(self, disease_token):
        # get disease for a selected token
        if disease_token.lower() != "none":
            disease = Diseases.get_by_token(disease_token)
            self.disease_id = disease.id
        else:
            disease = None
        self.disease = disease

    def __repr__(self):
        return "<Answer (question_id: '{}', answered by user: '{}' in survey '{}', type: '{}', " \
               "disease selected: '{}', certainty: '{}')>".format(
                self.question_id,
                self.user.name,
                self.survey_result.id,
                self.type,
                self.disease.name,
                self.certainty
        )


class Answers:

    @staticmethod
    def insert(answer):
        try:
            session.add(answer)
        except:
            session.rollback()
            raise
        finally:
            session.commit()

    @staticmethod
    def get_answers_for_question(question):
        raise NotImplementedError

    @staticmethod
    def get_answers_for_user(user):
        raise NotImplementedError

    @staticmethod
    def get_answers_for_image(image):
        raise NotImplementedError

    @staticmethod
    def get_answer(user, question):
        raise NotImplementedError
