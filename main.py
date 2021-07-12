import click

from utils.database import Base, engine, session
from model.disease import Disease
from model.image import Images
from model.question import *
from model.survey import Survey, RegularSurvey, ControlSurvey
from model.user import User

Base.metadata.create_all(engine)


@click.group()
def tool():
    pass


@tool.command(help="Initialize database with predefined contents.")
@click.argument('what', type=str, required=True)
def init(what):
    if what.lower() == 'users':
        from model.user import Users
        Users.insert(name="Ana Oros")
        Users.insert(name="Vladislav Dzinic")
        Users.insert(name="Zorka Grgic")


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
@click.option("--nrepeat", type=int, help="If type 2 questions are generated, this option is used to specify how many"
                                          " times will each image from the image group repeated when generating the"
                                          " questions.", default=5)
def generate(what, qtypes, stype, n_questions, n_surveys, nrepeat):
    if what == "questions":
        print(f"generate {what}.")
        Questions.generate(question_types=list(qtypes), n_repeat=nrepeat)
    elif what == "surveys":
        logger.info("Starting survey generation...")
        qtypes = list(qtypes)
        if "1" in qtypes:
            from generators.surveygeneratortype1 import SurveyGenerator
            survey_gen = SurveyGenerator(question_types=qtypes, survey_type=stype, questions_per_survey=n_questions)
            survey_gen.generate_all(n_surveys=n_surveys)
        if "2" in qtypes:
            from generators.surveygeneratortype2 import SurveyGenerator
            survey_gen = SurveyGenerator()
            survey_gen.generate_all(n_surveys=n_surveys)


@tool.command(help="Exports database content to the specified directory. Currently supports survey export in json and "
                   "html formats. At the moment, if requested, the tool exports all survey from the database.")
@click.argument('what', type=str, required=True)
@click.option("--where", type=str, required=True, help="A path to directory where to export data.")
@click.option("--export_type", type=click.Choice(["json", "html"]), default="json", help="In what format to export.")
@click.option("--survey_type", type=click.Choice(["regular", "control"]), default="regular",
              help="What type of survey you want to export if you are exporting surveys.")
@click.option("--survey_number", type=int, help="Survey type to be generated. Valid options are 1, 2, and 3.",
              default=1)
def export(what, where, export_type, survey_type, survey_number):
    if what == "surveys":
        logger.info("Starting survey export...")
        if survey_number == 1:
            from generators.surveygeneratortype1 import SurveyGenerator
            SurveyGenerator.export_surveys(where, export_type=export_type, survey_type=survey_type)
        elif survey_number == 2:
            # there are no type 2 control surveys
            from generators.surveygeneratortype2 import SurveyGenerator
            SurveyGenerator.export_surveys(where, export_type=export_type, survey_type="regular")


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

    elif what == "survey_result":
        from model.survey import Survey

        survey_result_path = "/home/gorana/PycharmProjects/SurveyGenerator/survey-generator/docs/regular survey 1.json"
        Survey.load_results(survey_json_filepath=survey_result_path)
    elif what == "users":
        from model.user import Users
        Users.insert(name="gorana gojic", access_token="a")
        Users.insert(name="veljko petrovic", access_token="abccdaaaafghaaaaaa")


if __name__ == '__main__':
    tool()


