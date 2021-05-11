import json

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from string import Template
from datetime import datetime

from utils.database import Base
from utils.tools import minify_json


class Survey(Base):
    __tablename__ = 'survey'

    id          = Column(Integer, primary_key=True, autoincrement=True)
    type        = Column(String)
    json        = Column(Text)
    created_at  = Column(DateTime, nullable=False)

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
                       "completeText:\"Završi\",completedHtml: \"Uspešno ste popunili anketu. Hvala!\"}"

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

    def __repr__(self):
        return super().__repr__() + \
            "\nRegularSurvey (questions: '{}')".format(
            "0" if self.questions is None else str(len(self.questions))
        )

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


