import click

from utils.database import Base, engine, session
from model.image import Images
from model.question import *
from model.survey import Survey, RegularSurvey, ControlSurvey
from model.user import User
from generators.surveygenerator import SurveyGenerator

Base.metadata.create_all(engine)


@click.group()
def tool():
    pass


@tool.command()
@click.argument('what', type=str, required=True)
@click.option('--directory', type=str, required=True)
@click.option('--extension', '-e', multiple=True, required=True)
def load(what, directory, extension):
    print(f"load {what} from {directory}.")
    if what == "images":
        Images.load_images(directory, extensions=list(extension))


@tool.command()
@click.argument('what', type=str, required=True)
@click.option('--directory', type=str, required=True)
def save(what, directory):
    print(f"save {what} to {directory}.")
    # TODO Implement


@tool.command()
@click.argument('what', type=str, required=True)
@click.option("--qtypes", multiple=True, required=True)
@click.option("--stype", type=click.Choice(['regular', 'control'], case_sensitive=False))
@click.option("--n_questions", '-n', type=int)
def generate(what, qtypes, stype, n_questions):
    if what == "questions":
        print(f"generate {what}.")
        Questions.generate(question_types=list(qtypes))
    elif what == "surveys":
        logger.info("Starting survey generation...")
        qtypes = list(qtypes)
        survey_gen = SurveyGenerator(question_types=qtypes, survey_type=stype, questions_per_survey=n_questions)
        survey_gen.generate_all()


@tool.command()
@click.argument('what', type=str, required=True)
@click.option("--where", type=str, required=True)
@click.option("--export_type", type=click.Choice(["json", "html"]), default="json")
@click.option("--survey_type", type=click.Choice(["regular", "control"]), default="regular")
def export(what, where, export_type, survey_type):
    if what == "surveys":
        logger.info("Starting survey export...")
        SurveyGenerator.export_surveys(where, export_type=export_type, survey_type=survey_type)


@tool.command()
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


