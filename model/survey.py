import json
import regex as re

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Date
from sqlalchemy.orm import relationship
from string import Template
from datetime import datetime
from pathlib import Path

from utils.database import Base, session
from utils.tools import minify_json
from utils.logger import logger
from model.user import Users
from model.answer import AnswerType1


class Survey(Base):
    __tablename__ = 'survey'

    id          = Column(Integer, primary_key=True, autoincrement=True)
    type        = Column(String)
    json        = Column(Text)
    created_at  = Column(DateTime, nullable=False)

    survey_results = relationship("SurveyResult", back_populates="survey")
    valid_types = ["regular", "control"]

    __mapper_args__ = {
        "polymorphic_on": type,
        "polymorphic_identity": "base"
    }

    def __init__(self, auth_page=True):
        self.created_at = datetime.now()
        self.auth_page = auth_page

    def __repr__(self):
        return "<Survey (\n\tid: '{}',\n\ttype: '{}',\n\tcreated_at: '{}')>".format(
            str(self.id),
            self.type,
            str(self.created_at)
        )

    @staticmethod
    def load_results(survey_json_filepath):
        """
        Loads survey results from surveyjs json file format for the Experiment 1 survey type.

        Expected format of a survey result:
        ...
        "Data": [{
            "sXY-qZW-choice": <some-disease-token string or "none">,
            "sXY-qZW-certainty: <some-numerical-value>",
            <... the above sequence can be repeated multiple times ...>
            "HappendAt": "<some-date-value>"
        }]

        A file can contain multiple results for the same survey. Each result is parsed separately and for each parsed
        result an instance of SurveyResult is created. The instance consist of array of AnswerType1 objects, where each
        object is associated with a corresponding QuestionType1, a User that has filled the survey, a Disease that the
        user has selected and certainty

        :param survey_json_filepath: A path to the survey result json file.
        :return: None
        """
        # does survey result json file exist?
        if not Path(survey_json_filepath).exists():
            logger.error(f"File {survey_json_filepath} does not exist.")
            raise FileNotFoundError(f"File {survey_json_filepath} does not exist.")
        if Path(survey_json_filepath).is_dir():
            logger.error(f"Expecting a file, but {survey_json_filepath} is a directory.")
            raise IsADirectoryError(f"Expecting a file, but {survey_json_filepath} is a directory.")
        logger.info(f"Importing survey results from file {survey_json_filepath}.")

        with open(survey_json_filepath, "r") as f:
            survey_json = json.load(f)

        # matches for strings like s<digits>-q<digits>-choice and s<digits>-q<digits>-certainty
        question_re = re.compile("s\d+-q\d+-(choice|certainty)", re.ASCII)

        # results are stored inside "Data" json array
        survey_results = survey_json["Data"]
        for result in survey_results:
            user = Users.get_user_by_access_token(result["q-token"])
            if user is None:
                logger.error("User with token '{}' does not exist.".format(result["q-token"]))
                raise ValueError("User with token '{}' does not exist.".format(result["q-token"]))

            # generate AnswerType1 objects for each pair of question-choice and question-certainty pairs in response
            # json
            first_question = False
            answers = dict()
            for question_str, answer_str in result.items():
                # if question identifier is not like sXY-qZW-choice or sXY-qZW-certainty skip
                if not question_re.match(question_str):
                    continue
                question_id = int(question_str.split('-')[1][1:])
                if first_question is False:
                    survey_id = int(question_str.split('-')[0][1:])
                    survey = Surveys.get_by_id(survey_id)
                    assert survey is not None
                    first_question = True
                if "-choice" in question_str:
                    if question_id not in answers.keys():
                        answers[question_id] = AnswerType1(user, question_id=question_id, disease_token=answer_str)
                    else:
                        answers[question_id].set_disease(disease_token=answer_str)
                if "-certainty" in question_str:
                    certainty = int(answer_str)
                    if question_id not in answers.keys():
                        answers[question_id] = AnswerType1(user, question_id=question_id, certainty=certainty)
                    else:
                        answers[question_id].set_certainty(certainty=certainty)

            # create list of Answer objects from the dictionary
            answers = [answer for _, answer in answers.items()]

            # create a survey result object and insert it to the database
            survey_result = SurveyResult(user=user, survey=survey, answers=answers)
            survey_result.insert()

    @staticmethod
    def _generate_auth_page():
        return """
        {
            name: "page-auth",
            elements: [
            {
             type: "text",
             name: "q-name",
             title: "Unesite ime",
             isRequired: true
            },
            {
             type: "text",
             name: "q-surname",
             title: "Unesite prezime",
             isRequired: true
            },
            {
             type: "text",
             name: "q-token",
             title: "Unesite lični ključ koji ste dobili putem mejla",
             isRequired: true
            }
            ],
            title: "Unos podataka o učesniku ankete"
        },
        """

    def _generate(self, survey_type=None):
        survey_json = "{ pages: ["

        # generate authorization page
        if self.auth_page:
            survey_json += Survey._generate_auth_page()

        # generate pages for survey questions
        for i, question in enumerate(self.questions):
            question_json = self._generate_page(question)
            if i != len(self.questions) - 1:  # put comma after all but the last generated page
                question_json += ","
            survey_json += question_json
        if survey_type is not None:
            # add survey type metadata object
            pass
        survey_json += "]"

        # survey localization - serbian
        survey_json += ",pagePrevText:\"Prethodna\",pageNextText:\"Naredna\"," \
                       "completeText:\"Završi\",completedHtml: \"Uspešno ste popunili anketu. Hvala!<br>" \
                       "<a href=\"./anketa.php\">Pređite na sledeću anketu</a>\"}"

        return survey_json

    def _generate_page(self, question):
        template = self._get_page_template()
        return template.substitute({"pid": question.id, "questions": question.json})

    def _get_page_template(self):
        # $pid - survey page id
        # $questions - questions json
        return Template("""
        {
            name: "page-$pid",
            $questions,
            title: "Pitanje $pid"
        }
        """)


class RegularSurvey(Survey):
    __tablename__ = "regular_survey"
    __mapper_args__ = {"polymorphic_identity": "regular"}

    id = Column(Integer, ForeignKey("survey.id"), primary_key=True)

    questions = relationship("Question", back_populates="regular_survey")

    def __init__(self, auth_page=True):
        super().__init__(auth_page=auth_page)

    def __repr__(self):
        return super().__repr__() + \
            "\nRegularSurvey (questions: '{}')".format(
            "0" if self.questions is None else str(len(self.questions))
        )

    def load_results(self):
        super().load_results()

    def generate(self):
        # remove all unnecessary whitespace characters to reduce memory consumption
        self.json = minify_json(
            super(RegularSurvey, self)._generate()
        )

    def _get_page_template(self):
        return super(RegularSurvey, self)._get_page_template()


class ControlSurvey(Survey):
    __tablename__ = "control_survey"
    __mapper_args__ = {"polymorphic_identity": "control"}

    id = Column(Integer, ForeignKey("survey.id"), primary_key=True)

    questions = relationship("Question", back_populates="control_survey")

    def __init__(self, auth_page=True):
        super().__init__(auth_page=auth_page)

    def __repr__(self):
        return super().__repr__() + \
            "ControlSurvey (questions: '{}')".format(
            "0" if self.questions is None else str(len(self.questions))
        )

    def generate(self):
        # remove all unnecessary whitespace characters to reduce memory consumption
        self.json = minify_json(
            super(ControlSurvey, self)._generate()
        )

    def _get_page_template(self):
        return super(ControlSurvey, self)._get_page_template()


class Surveys:

    @staticmethod
    def get_by_id(id):
        return session.query(Survey).where(Survey.id == id).one()


class SurveyResult(Base):
    __tablename__ = 'survey_result'

    id          = Column(Integer, primary_key=True, autoincrement=True)
    date        = Column(Date)
    survey_id   = Column(Integer, ForeignKey("survey.id"))
    user_id     = Column(Integer, ForeignKey("user.id"))

    survey      = relationship("Survey", back_populates='survey_results')
    user        = relationship("User",   back_populates='survey_results')
    answers     = relationship("Answer", back_populates="survey_result")

    def __init__(self, survey=None, user=None, answers=None):
        self.survey = survey
        self.user = user
        self.answers = answers

    def insert(self):
        try:
            session.add(self)
        except:
            session.rollback()
        finally:
            session.commit()

