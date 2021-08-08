import base64
import random
import itertools

from datetime import datetime
from pathlib import Path
from sqlalchemy import Column, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy import and_
from string import Template

from utils.database import Base, session
from utils.logger import logger
from utils.tools import minify_json, fisher_yates_shuffle
from model.image import Images
from model.disease import Diseases


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
        return "<Question (id: '{}', type: '{}', created at: '{}', in regular survey {}, in control survey {})>".format(
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
                "imfname": self.image.filename,
                "questions": QuestionType1._get_questions()
            })
            self.json = minify_json(question_json)
        else:
            logger.error(f"Cannot generate question {self.id} because it does not have associated image.")
            raise ValueError(f"Cannot generate question {self.id} because it does not have associated image.")

    @staticmethod
    def _get_questions():
        diseases = Diseases.get_all()
        questions_json = ""
        for i, disease in enumerate(diseases):
            template = Template("""
            {
                value: "$token",
                text: "Smatram da ova slika predstavlja pacijenta sa oboljenjem $name."
            },
            """).substitute({"token": disease.token, "name": disease.name})
            questions_json += template
        questions_json += Template("""
            
            {
                value: "none",
                text: "Smatram da ova slika ne prikazuje ni jedno od navedenih oboljenja."
            }, {
                value: "not_applicable",
                text: "Slika nije dovoljno dobra za postavljanje dijagnoze." 
            }
            """).substitute({})
        return questions_json

    @staticmethod
    def _get_question_template():
        # $quid - id pitanja
        # $imid - id slike vezane za pitanje
        # $imname - ime slike koja se prikazuje, mora da se nalazi u images direktorijumu
        # $imfname - puno ime slike sa ekstenzijom
        # $questions - izgenerisani json za bolesti na slici
        template = Template("""
        elements: [
            {
                type: "html",
                name: "s^_^-q$quid-img",
                html: "<div class='img-zoom-container'><div style='width: 500px; float: left'><img onload=\\"imageZoom('$imname', '$imname-zoom')\\" id='$imname' src='images/$imfname' style='width: 100%'/></div>
                       <div id='$imname-zoom' class='img-zoom-result'></div></div>"
            },
            {
                type: "radiogroup",
                name: "s^_^-q$quid-choice",
                isRequired: true,
                state: "expanded",
                title: "Data Vam je slika očnog dna. Od ponuđenih tvrdnji selektujte onu sa kojom se slažete.",
                requiredErrorText: "Molimo Vas da odgovorite na ovo pitanje.",
                choices: [
                    $questions
                ]
            },
            {
                type: "rating",
                name: "s^_^-q$quid-certainty",
                state: "expanded",
                title: "Koliko ste sigurni u odgovor koji ste dali u prethodnom pitanju?",
                requiredErrorText: "Molimo Vas da odgovorite na ovo pitanje.",
                isRequired: true,
                rateMin: 1,
                rateMax: 5,
                minRateDescription: "Veoma nesiguran/na",
                maxRateDescription: "Veoma siguran/na "
            }
        ]
        """)
        return template


class QuestionType2(Question):
    __tablename__ = "qtype2"
    __mapper_args__ = {'polymorphic_identity': 2}

    id      = Column(Integer, ForeignKey("question.id"), primary_key=True)
    group   = Column(Integer)
    images  = relationship("Image", secondary="image_qtype2", back_populates="questions_t2")

    def __init__(self, gid):
        super(QuestionType2, self).__init__()
        self.group = gid

    def __repr__(self):
        return super().__repr__() + \
            "\n<QuestionType2 (image1_id: '{}', image2_id: '{}')>".format(
                "None" if self.images[0] is None else str(self.images[0].id),
                "None" if self.images[1] is None else str(self.images[1].id)
            )

    def generate(self):
        """
        Generate JSON for a single survey question.
        :return:
        """
        if len(self.images) == 3 and self.images[0] is not None and self.images[1] is not None:
            im1, im2, im0 = self.images[0], self.images[1], self.images[2]
            im1path = str(Path(im1.root) / im1.dataset.upper() / im1.filename)
            im2path = str(Path(im2.root) / im2.dataset.upper() / im2.filename)
            im0path = str(Path(im0.root) / im0.dataset / im0.filename)
            with open(im1path, "rb") as im1f:
                im1hash = "data:image/png;base64," + base64.b64encode(im1f.read()).decode('utf-8')
            with open(im2path, "rb") as im2f:
                im2hash = "data:image/png;base64," + base64.b64encode(im2f.read()).decode('utf-8')
            with open(im0path, "rb") as im0f:
                im0hash = "data:image/png;base64," + base64.b64encode(im0f.read()).decode('utf-8')
            image_width, image_height = Images.get_dataset_image_dims(self.images[0].dataset)
            question_json = QuestionType2._get_question_template().substitute({
                "quid": self.id,
                "im1id": self.images[0].id,
                "im2id": self.images[1].id,
                "im0hash": im0hash,
                "im1hash": im1hash,
                "im2hash": im2hash,
                "imwidth": image_width,
                "imheight": image_height
            })
            self.json = minify_json(question_json)
        else:
            logger.error(f"Cannot generate question {self.id} because it has {len(self.images)} associated images "
                         f"instead of two.")
            raise ValueError(f"Cannot generate question {self.id} because it has {len(self.images)} associated images"
                             f" instead of two.")

    @staticmethod
    def _get_questions():
        raise NotImplementedError

    @staticmethod
    def _get_question_template():
        # $quid         - id pitanja
        # $im1id        - id prve slike
        # $im2id        - id druge slike
        # $im0hash      - base64 hash originalne slike (slike 0)
        # $im1hash      - base64 hash prve segmentacione mape (slike 1)
        # $im2hash      - base64 hash druge segmentacione mape (slike 2)
        # $imwidth      - sirina slike koja se prikazuje
        # $imheight     - visina slike koja se prikazuje
        template = Template("""
            elements: [
                {
                    type: "imagepicker",
                    name: "s^_^-q$quid-im$im1id-im$im2id-img",
                    title: "Originalna slika",
                    hideNumber: true,
                    choices: [
                    {
                        value: "original",
                        imageLink: "$im0hash"
                    }
                 ],
                 startWithNewLine: true,
                 readOnly: true,
                 imageTag: "original"
                },
                {
                    type: "imagepicker",
                    name: "s^_^-q$quid-im$im1id-im$im2id-impicker",
                    title: "Segmentacione mape",
                    hideNumber: true,
                    choices: [
                    {
                        value: "im$im1id",
                        imageLink: "$im1hash"
                    },
                    {
                        value: "im$im2id",
                        imageLink: "$im2hash"
                    }
                    ],
                    isRequired: true,
                    requiredErrorText: "Molimo Vas da odaberete jednu od dve ponuđene segmentacione mape.",
                    startWithNewLine: false,
                    imageTag: "segmaps"
                }
            ]
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
    def get_in_regular_survey(types=None):
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
    def get_by_image_group(gid, unassigned=True):
        if unassigned:
            # return all questions of the same group that are not already attached to some of the surveys
            questions = session.query(QuestionType2).where(QuestionType2.group == gid).all()
            return [q for q in questions if q.regular_survey is None]
        else:
            # return all questions of the same group
            return session.query(QuestionType2).where(QuestionType2.group == gid).all()

    @staticmethod
    def generate_questions_t2(gid, image_group, n_repeat, redundancy=50, n_redundancy=1, flip_images=True):
        """

        :param gid:
        :param image_group:
        :param n_repeat:
        :param redundancy: Should be in percentages. How many questions will be repeated to create redundancy. It should
            be between 0 and 100.
        :return:
        """

        # generate all combinations of images in a group
        # it will be total of 28 image pairs for a group of 8 images
        image_group = [i for i in itertools.combinations(iterable=image_group, r=2)]

        # repeat some pairs to create redundancy, number of pairs is determined according to the redundancy parameter
        # which represents a percent of pairs to be repeated
        assert 0 <= redundancy <= 100
        dupes = list()

        # sample different question indices to duplicate them
        iindices = random.sample(range(0, len(image_group)), (redundancy * len(image_group)) // 100)
        for idx in iindices:
            dupes.append(image_group[idx])
            print(f"Added duplicate image pair ({image_group[idx][0].id}, {image_group[idx][1].id}).")

        # replicate duplicates n_redundancy times
        dupes = dupes * n_redundancy
        image_group.extend(dupes)

        # shuffle images before creating the questions
        image_group = fisher_yates_shuffle(image_group)

        # get original image for a segmentation mask group
        # the original should be the last image in an array
        original = Images.get_original_for_segmap(image_group[0][0])

        # create questions and assign them to the images
        questions = list()
        for i, (im1, im2) in enumerate(image_group):
            q = QuestionType2(gid=gid)
            q.images.extend([im1, im2, original])
            questions.append(q)
            print(f"Question {i} is associated with images {im1.id} and {im2.id}.")

        return questions

        # generate enough empty questions
        # questions = [QuestionType2(gid=gid) for _ in range(0, (n_repeat * len(image_group)) // 2)]
        #
        # # make all images in a group repeat n times and shuffle them
        # image_group = image_group * n_repeat
        # image_group = fisher_yates_shuffle(image_group)
        # assert len(image_group) % 2 == 0
        #
        # # get original, color image for the corresponding group of segmentation masks
        # original = Images.get_original_for_segmap(image_group[0])
        #
        # # This loop sometimes does not finish if the id of the last image to be assigned is same as the id the image
        # # in the last question with one assigned image. If this happens, quick fix for now is to finish program
        # # execution and run it again until the loop completes.
        # inum = 0
        # while True:
        #     # stop when all images from the list are assigned to the questions
        #     if inum == len(image_group):
        #         break
        #
        #     image = image_group[inum]
        #     # choose one of the questions with randomly with equal probability
        #     qnum = random.randint(0, len(questions)-1)
        #
        #     # repick the question if already picked question has two assigned images or an id of the only assigned
        #     # image is same as the id of the image to be assigned to the question
        #     if len(questions[qnum].images) == 2:
        #         print(f"\n1. picked={qnum}")
        #         Questions._debug(questions)
        #         continue
        #     if len(questions[qnum].images) == 1 and questions[qnum].images[0].id == image.id:
        #         print(f"\n2. picked={qnum}")
        #         Questions._debug(questions)
        #         continue
        #
        #     # assign the image to the question and go to the next image
        #     questions[qnum].images.append(image)
        #     inum = inum + 1
        #
        # for i, question in enumerate(questions):
        #     logger.info(f"{i}. Question {question.id} associated with images {question.images[0].id} "
        #                 f"and {question.images[1].id}.")
        #     assert len(question.images) == 2
        #     assert question.images[0].id != question.images[1].id
        #
        #     question.images.append(original)
        #
        # return questions

    @staticmethod
    def _debug(questions):
        for i, question in enumerate(questions):
            print("---------------------------------------")
            if len(question.images) == 0:
                print(f"q{i}. imgs={len(question.images)}")
            elif len(question.images) == 1:
                print(f"q{i}. imgs={len(question.images)}, img1_id: {question.images[0].id}")
            elif len(question.images) == 2:
                print(f"q{i}. imgs={len(question.images)}, img1_id: {question.images[0].id}, "
                      f"img2_id: {question.images[1].id}")

    @staticmethod
    def generate(question_types, n_repeat, image_names=None):
        """
        Generate questions of a given type for a given set of images. If set of images
        is specified, it must be provided as a list of image filenames. If not specified
        the method will generate questions for all images present in a database.

        :param question_types: An integer list of question types. Currently supported type
            values are:
                1 - question type for an experiment 1
                2 - question type for an experiment 2
                3 - question type for an experiment 3
        :param n_repeat: An integer that specifies how many times will each image from the image group be
            repeated when generating questions.
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

        questions = list()
        for qtype in question_types:
            qtype = int(qtype)
            if qtype == 1:
                if image_names is None:
                    images = Images.get_all()
                else:
                    images = Images.get_by_name(image_names)
                logger.info(f"Loaded {len(images)} images for question generation.")

                for image in images:
                    qt = QuestionType1()
                    qt.image = image
                    questions.append(qt)
            elif qtype == 2:
                min_group_id = Images.get_min_image_group()
                if min_group_id is None:
                    logger.error(f"Skipping question generation because there are no groups associated with the "
                                 f"images.")
                    raise ValueError(logger.error(f"Skipping question generation because there are no groups associated"
                                                  f" with the images."))

                max_group_id = Images.get_max_image_group()
                for gid in range(min_group_id, max_group_id+1):
                    image_group = Images.get_whole_group(gid)
                    if image_group is None:
                        logger.error(f"There are no images associated with a group {gid}. Aborting.")
                        raise ValueError(f"There are no images associated with a group {gid}. Aborting.")
                    qt = Questions.generate_questions_t2(gid, image_group, n_repeat)
                    questions.extend(qt)
            elif qtype == 3:
                raise NotImplementedError

        logger.info(f"Generated {len(questions)} questions.")
        Questions.bulk_insert(questions)
        logger.debug(f"Inserted {len(questions)} questions to the database.")

        # this step must come after the questions are inserted into the database because generation required question id
        [question.generate() for question in questions]

        # update the database to reflect changes in json field
        session.commit()

        return questions



