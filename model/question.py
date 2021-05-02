from sqlalchemy import Column, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy import and_
from string import Template
from datetime import datetime

from utils.database import Base, session
from utils.logger import logger
from utils.tools import minify_json
from model.image import Images


class Question(Base):
    __tablename__ = "question"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    type        = Column(Integer)
    json        = Column(Text)
    created_at  = Column(DateTime, nullable=False)

    valid_types = [1, 2, 3]

    __mapper_args__ = {
        'polymorphic_identity': 0,
        'polymorphic_on': type,
    }

    regular_survey_id = Column(Integer, ForeignKey("regular_survey.id"))
    control_survey_id = Column(Integer, ForeignKey("control_survey.id"))

    regular_survey = relationship("RegularSurvey", back_populates="questions")
    control_survey = relationship("ControlSurvey", back_populates="questions")

    def __init__(self):
        self.created_at = datetime.now()

    def __repr__(self):
        return "<Question id: ('{}', type: '{}', created at: '{}', in regular survey {}, in control survey {})>".format(
            str(self.id),
            str(self.type),
            str(self.created_at),
            "no" if self.regular_survey is None else "yes",
            "no" if self.control_survey is None else "yes"
        )


class QuestionType1(Question):
    __tablename__   = "qtype1"
    __mapper_args__ = {'polymorphic_identity': 1}

    id       = Column(Integer, ForeignKey("question.id"), primary_key=True)
    image_id = Column(Integer, ForeignKey("image.id"))

    image = relationship("Image", back_populates="questions")

    def __repr__(self):
        return super().__repr__() + \
            "\n<QuestionType1 (image id: '{}', image name: '{}')>".format(
            "None" if self.image is None else str(self.image.id),
            "None" if self.image is None else self.image.filename
        )

    def generate(self):
        if self.image is not None:
            question_json = QuestionType1._get_question_template().substitute({
                "quid": self.id,
                "imid": self.image.id,
                "imname": self.image.name,
                "imfname": self.image.filename
            })
            self.json = minify_json(question_json)
        else:
            logger.error(f"Cannot generate question {self.id} because it does not have associated image.")
            raise ValueError(f"Cannot generate question {self.id} because it does not have associated image.")

    @staticmethod
    def _get_question_template():
        # $quid - id pitanja
        # $imid - id slike vezane za pitanje
        # $imname - ime slike koja se prikazuje, mora da se nalazi u images direktorijumu
        # $imfname - puno ime slike sa ekstenzijom
        template = Template("""
        elements: [
            {
                type: "html",
                name: "q$quid-img",
                html: "<div class=\\"img-zoom-container\\"><img id=\\"$imname\\" src=\\"images/$imfname\\"/>
                       <div id=\\"$imname-zoom\\" class=\\"img-zoom-result\\"></div></div>"
            },
            {
                type: "radiogroup",
                name: "q$quid-choice",
                isRequired: true,
                state: "expanded",
                title: "Data Vam je slika ocnog dna. Od ponudjenih tvrdnji selektujte onu sa kojom se slazete.",
                choices: [
                {
                    value: "diabetic_retinopathy",
                    text: "Smatram da ova slika predstavlja pacijenta sa oboljenjem Diabetic Retinopathy."
                },
                {
                    value: "choroidal_neovascularization",
                    text: "Smatram da ova slika predstavlja pacijenta sa oboljenjem Choroidal Neovascularization."
                },
                {
                    value: "arteriosclerotic_retinopathy",
                    text: "Smatram da ova slika predstavlja pacijenta sa oboljenjem Arteriosclerotic Retinopathy."
                },
                {
                    value: "geographic_atrophy_rpe",
                    text: "Smatram da ova slika predstavlja pacijenta sa oboljenjem Geographic Atrophy RPE."
                },
                {
                    value: "cillio_retinal_artery_occlusion",
                    text: "Smatram da ova slika predstavlja pacijenta sa oboljenjem Cillio-Retinal Artery Occlusion."
                }
                ],
                choicesOrder: "random",
                hasNone: true,
                noneText: "Smatram da ova slika ne prikazuje ni jedno od navedenih oboljenja."
            },
            {
                type: "rating",
                name: "q$quid-certanity",
                state: "expanded",
                title: "Koliko ste pouzdani u odgovor koji ste dali u prethodnom pitanju?",
                isRequired: true,
                rateMin: 0,
                rateMax: 7,
                minRateDescription: "Nimalo",
                maxRateDescription: "Sasvim"
            },
            {
                type: "html",
                name: "q$quid-metadata",
                visible: false,
                html: "<div id=\\"question_id\\">$quid</div><div id=\\"image_id\\">$imid</div>
                       <div id=\\"image_filename\\">$imfname</div>"
            }
        ]
        """)
        return template


class QuestionType2(Question):
    __tablename__ = "qtype2"
    __mapper_args__ = {'polymorphic_identity': 2}

    id = Column(Integer, ForeignKey("question.id"), primary_key=True)

    def __repr__(self):
        return super().__repr__() + "\n<QuestionType2 ()>"

    def generate(self):
        raise NotImplementedError

    def _get_json(self):
        template = Template("""
            formatirani ispis za pitanje {}
        """)
        return template


class QuestionType3(Question):
    __tablename__ = "qtype3"
    __mapper_args__ = {'polymorphic_identity': 3}

    id = Column(Integer, ForeignKey("question.id"), primary_key=True)

    def __repr__(self):
        return super().__repr__() + "\n<QuestionType3 ()>"

    def generate(self):
        raise NotImplementedError

    def _get_json(self):
        template = Template("""
            formatirani ispis za pitanje {}
        """)
        return template


class Questions:

    @staticmethod
    def insert(question):
        raise NotImplementedError

    @staticmethod
    def bulk_insert(questions):
        try:
            [session.add(q) for q in questions]
        except:
            session.rollback()
            raise
        else:
            session.commit()

    @staticmethod
    def update(question):
        raise NotImplementedError

    @staticmethod
    def delete(question):
        raise NotImplementedError

    @staticmethod
    def get_all():
        return session.query(Question).all()

    @staticmethod
    def get_by_type(type):
        """
        Query a database for all questions of specific type.

        :param type: An integer in interval [0-3].
        :return: A list of Question objects.
        """
        if type not in [0, 1, 2, 3]:
            raise ValueError("Question type must be one of [0, 1, 2, 3]. Given type is {0}".format(type))
        return session.query(Question).where(Question.type == type).all()

    @staticmethod
    def get_by_id(qid):
        return session.query(Question).get(qid)

    @staticmethod
    def get_by_image(image):
        raise NotImplementedError

    @staticmethod
    def get_by_network(network):
        raise NotImplementedError

    @staticmethod
    def get_unassigned(types=None):
        """
        Returns all questions of specific types that are not assigned to any regular or control survey.

        :param types: Valid question types.
        :return: List of questions not assigned to any survey
        """
        if types is not None:
            filters = [Question.type == type for type in types]
        else:
            filters = []
        return session.query(Question)\
                     .where(and_(Question.regular_survey == None, Question.control_survey == None))\
                     .filter(*filters)\
                     .all()

    @staticmethod
    def get_in_regular_survey(types):
        """
        Returns all questions of specific types that are assigned to any of regular surveys and are not assigned to any of control surveys.

        :param types: Valid question types.
        :return: List of questions assigned only to regular surveys.
        """
        if types is not None:
            filters = [Question.type == type for type in types]
        else:
            filters = []
        return session.query(Question)\
                      .where(and_(Question.regular_survey != None, Question.control_survey == None))\
                      .filter(*filters)\
                      .all()

    @staticmethod
    def generate(question_types, image_names=None):
        """
        Generate questions of a given type for a given set of images. If set of images
        is specified, it must be provided as a list of image filenames. If not specified
        the method will generate questions for all images present in a database.

        :param question_types: An integer list of question types. Currently supported type
            values are:
                1 - question type for an experiment 1
                2 - question type for an experiment 2
                3 - question type for an experiment 3
        :param image_names: A list of string representing image filenames with extension. Filenames
            are case sensitive.
        :return: A list of generated questions.
        """
        logger.info(f"Generating questions of types {question_types}.")
        for qtype in question_types:
            qtype = int(qtype)
            if qtype not in [1, 2, 3]:
                logger.error(f"Cannot generate question of type {qtype}. Valid question types are 1, 2, 3.")
                raise ValueError(f"Cannot generate question of type {qtype}. Valid question types are 1, 2, 3.")

        if image_names is None:
            images = Images.get_all()
        else:
            images = Images.get_by_name(image_names)
        logger.info(f"Loaded {len(images)} images for question generation.")

        questions = list()
        for qtype in question_types:
            qtype = int(qtype)
            for image in images:
                if qtype == 1:
                    qt = QuestionType1()
                    qt.image = image
                    questions.append(qt)
                elif qtype == 2:
                    qt = QuestionType2()
                    qt.image = image
                    questions.append(qt)
                elif qtype == 3:
                    qt = QuestionType3()
                    qt.image = image
                    questions.append(qt)

        logger.info(f"Generated {len(questions)} questions.")
        Questions.bulk_insert(questions)
        logger.debug(f"Inserted {len(questions)} questions to the database.")

        # this step must come after the questions are inserted into the database because generation required question id
        [question.generate() for question in questions]

        # update the database to reflect changes in json field
        session.commit()

        return questions



