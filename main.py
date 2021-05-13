import click

from utils.database import Base, engine, session
from model.disease import Disease
from model.image import Images
from model.question import *
from model.survey import Survey, RegularSurvey, ControlSurvey
from model.user import User
from generators.surveygenerator import SurveyGenerator

Base.metadata.create_all(engine)


@click.group()
def tool():
    pass


@tool.command(help="Load content to the database. Parameter `what` specifies object type to be loaded and parameter "
                   "`directory` where to find the objects. Currently supports loading images to the database.")
@click.argument('what', type=str, required=True)
@click.option('--directory', type=str, required=True,
              help="A path to the directory containing images. Immediate parent directory will be considered as a "
                   "dataset name.")
@click.option('--extension', '-e', multiple=True, required=True,
              help="A list image extensions to be loaded from the directory. An extension is a string preceded by a dot"
                   " sign (e.g. '.png').")
def load(what, directory, extension):
    print(f"load {what} from {directory}.")
    if what == "images":
        Images.load_images(directory, extensions=list(extension))
    elif what == "surveyresult":
        pass


@tool.command(help="Generate questions or surveys depending of the `what` parameter value. "
                   ""
                   "If passed `questions`, the tool will generate a question of specified types for each image in the "
                   "database, even if the question for that image have already been generated."
                   ""
                   "If passed `surveys`, the tool will generate surveys of type `stype` from all database questions not"
                   " already assigned to the other, existing survey.")
@click.argument('what', type=str, required=True)
@click.option("--qtypes", multiple=True, required=True, help="Question type. Currently supported values are 1, 2 and "
                                                             "3.")
@click.option("--stype", type=click.Choice(['regular', 'control'], case_sensitive=False), required=True,
              help="Survey type. Currently  supported are `regular` and `control`.")
@click.option("--n_questions", '-n', type=int, default=20, help="How many questions there will be per survey.")
@click.option("--n_surveys", type=int, help="Number of surveys to be generated. If not specified, there will be "
                                            "generated as many surveys as there are unassigned questions in the "
                                            "database.")
def generate(what, qtypes, stype, n_questions, n_surveys):
    if what == "questions":
        print(f"generate {what}.")
        Questions.generate(question_types=list(qtypes))
    elif what == "surveys":
        logger.info("Starting survey generation...")
        qtypes = list(qtypes)
        survey_gen = SurveyGenerator(question_types=qtypes, survey_type=stype, questions_per_survey=n_questions)
        survey_gen.generate_all(n_surveys=n_surveys)


@tool.command(help="Exports database content to the directory specified. Currently supports survey export in json and "
                   "html formats. At the moment, if requested, the tool exports all survey from the database.")
@click.argument('what', type=str, required=True)
@click.option("--where", type=str, required=True, help="A path to directory where to export data.")
@click.option("--export_type", type=click.Choice(["json", "html"]), default="json", help="In what format to export.")
@click.option("--survey_type", type=click.Choice(["regular", "control"]), default="regular",
              help="What type of survey you want to export if you are exporting surveys.")
def export(what, where, export_type, survey_type):
    if what == "surveys":
        logger.info("Starting survey export...")
        SurveyGenerator.export_surveys(where, export_type=export_type, survey_type=survey_type)


@tool.command(help="[Depricated] Primitive development testing tool.")
@click.argument('what', type=str, required=True)
def test(what):
    if what == "images":
        from model.image import Image
        test_img = Image("/home/gorana/Desktop/tmp/survey-generator-tmp/DRIVE/im55555.png")
        print(test_img)
        session.add(test_img)
        session.commit()
        print(test_img)
    elif what == "question1":
        from model.image import Image
        from model.question import QuestionType1

        test_qt1 = QuestionType1()
        test_img = Image("/home/gorana/Desktop/tmp/survey-generator-tmp/DRIVE/im0044.png")
        test_qt1.image = test_img

        session.add(test_qt1)
        session.commit()

    elif what == "regular_survey":
        from model.survey import RegularSurvey
        from model.image import Image
        from model.question import QuestionType1

        test_qt1 = QuestionType1()
        test_img = Image("/home/gorana/Desktop/tmp/survey-generator-tmp/DRIVE/im0045.png")
        test_qt1.image = test_img
        test_regular_survey = RegularSurvey()
        test_regular_survey.questions = [test_qt1]
        session.add(test_qt1)
        session.commit()


if __name__ == '__main__':
    tool()


