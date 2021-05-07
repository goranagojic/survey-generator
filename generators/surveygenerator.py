import json

from random import randint
from pathlib import Path
from string import Template

from model.survey import *
from model.question import *
from utils.database import session
from utils.logger import logger


class SurveyGenerator:

    supported_export_types = ["html", "json"]

    def __init__(self, question_types, questions_per_survey, survey_type):
        self.questions_per_survey = questions_per_survey

        if survey_type not in Survey.valid_types:
            logger.error(f"Survey type can be in {Survey.valid_types} but you require {survey_type}.")
            raise ValueError(f"Survey type can be in {Survey.valid_types} but you require {survey_type}.")
        self.survey_type = survey_type

        for question_type in question_types:
            if int(question_type) not in Question.valid_types:
                logger.error(f"Question type can be in {Question.valid_types} but you require {question_type}.")
                raise ValueError(f"Question type can be in {Question.valid_types} but you require {question_type}.")
        self.question_types = question_types

    def generate_all(self, n_surveys=None):
        """
        Generates surveys and saves them to the database.

        Surveys are generated by selecting `questions_per_survey` questions from database using Fisher-Yates shuffling
        algorithm. If `survey_type` is set to `regular` candidate questions are those unassigned to any previously
        generated survey. Otherwise, if `survey_type` is set to `control`, candidate questions are picked from those
        questions already assigned to existing regular surveys.

        :param n_surveys: Maximum number of survey that should be generated. If the requested number is larger then
            a possible number of surveys that can be generated, the method generate as many surveys as it can.
        :return:
        """
        while True:     # iterate while there are more questions to include in some of the surveys
            if self.survey_type == "regular":
                questions = Questions.get_unassigned()
                survey = RegularSurvey()
            else:
                questions = Questions.get_in_regular_survey()
                survey = ControlSurvey()

            if len(questions) == 0:     # all questions are already added to the survey
                logger.info(f"There are no more unassigned questions satisfying the criteria for '{self.survey_type}' "
                            f"in the database. Finishing.")
                break

            # save a survey to database so that it is assigned valid id
            session.add(survey)
            session.commit()
            shuffled_questions = SurveyGenerator.fisher_yates_shuffle(questions)

            for i in range(0, min(self.questions_per_survey, len(shuffled_questions))):
                question = shuffled_questions[i]
                survey.questions.append(question)
                logger.info(f"Added question {question.id} to survey {survey.id}.")

            # warn if the survey is assigned less questions then requested
            if len(survey.questions) != self.questions_per_survey:
                logger.warning(f"Survey {survey.id} have {len(survey.questions)} questions instead of "
                               f"{self.questions_per_survey}.")

            # generate survey json and update the survey in the database
            survey.generate()
            session.commit()

            # stop survey generation if required number of surveys is reached
            if n_surveys is not None:
                n_surveys -= 1
                if n_surveys == 0:
                    break

    @staticmethod
    def export_surveys(where, export_type="json", survey_type="regular"):
        """

        :param where:
        :param export_type:
        :param survey_type:
        :return:
        """
        # check if directory to export to is ok
        if where is not None:
            if not Path(where).is_dir():
                logger.error(f"Cannot export surveys to {where} because it is not a directory.")
                raise NotADirectoryError(f"Cannot export surveys to {where} because it is not a directory.")
            else:
                logger.info(f"Survey export is enabled. You can find exported surveys in directory '{where}'.")

        # check if export type is valid
        export_type = export_type.lower()
        if export_type not in SurveyGenerator.supported_export_types:
            logger.error(f"Cannot export survey to '{export_type}'. Supported types are "
                         f"{SurveyGenerator.supported_export_types}")
            raise ValueError(f"Cannot export survey to '{export_type}'. Supported types are "
                             f"{SurveyGenerator.supported_export_types}")

        # export content
        surveys = session.query(Survey).where(Survey.type == survey_type).all()
        for survey in surveys:
            if export_type == "json":
                survey_filename = f"survey-{survey.id}.json"
                target_path = Path(where) / survey_filename
                with open(target_path, "w") as fout:
                    fout.write(survey.json)
                    logger.info(f"Survey {survey_filename} saved!")
            else:  # html
                # $head - html head section
                # $body - html body section
                html = Template("""
<html>
                    $head
                    $body
</html>
                """).substitute({
                    "head": SurveyGenerator._generate_html_head_template(),
                    "body": SurveyGenerator._genenerate_html_body_template().substitute({
                        "survey_json": survey.json,
                        "jqueryselector": "$"
                    })
                })
                survey_filename = f"survey-{survey.id}.html"
                target_path = Path(where) / survey_filename
                with open(target_path, "w") as fout:
                    fout.write(html)
                    logger.info(f"Survey {survey_filename} saved!")

    @staticmethod
    def fisher_yates_shuffle(arr):
        n = len(arr)
        for i in range(n-1, 0, -1):
            j = randint(0, i)
            arr[i], arr[j] = arr[j], arr[i]
        return arr

    @staticmethod
    def _generate_html_head_template():
        return """ 
  <head> 
    <meta charset="UTF-8">

    <!-- favicon settings --> 
    <link rel="apple-touch-icon" sizes="180x180" href="apple-touch-icon.png">
    <link rel="icon" type="image/png" sizes="32x32" href="favicon-32x32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="favicon-16x16.png">
    <link rel="manifest" href="site.webmanifest">
    <link rel="mask-icon" href="safari-pinned-tab.svg" color="#5bbad5">
    <meta name="msapplication-TileColor" content="#da532c">
    <meta name="theme-color" content="#ffffff">
    
    <!-- zoom styles -->
    <!-- see: https://www.w3schools.com/howto/tryit.asp?filename=tryhow_js_image_zoom -->
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <style>
      * {box-sizing: border-box;}

      .img-zoom-container {
        position: relative;
        width: 100%;
        overflow: hidden;
      }

      .img-zoom-lens {
        position: absolute;
        border: 1px solid #d4d4d4;
        /*set the size of the lens:*/
        width: 40px;
        height: 40px;
      }

      .img-zoom-result {
        border: 1px solid #d4d4d4;
        /*set the size of the result div:*/
        width: 400px;
        height: 400px;
        margin-left: 520px;
      }
    </style>
    
    <!-- jquery and survey.jquery -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.1.1/jquery.min.js"></script>
    <link href="https://unpkg.com/survey-jquery@1.8.41/modern.css" type="text/css" rel="stylesheet" />
    <script src="https://unpkg.com/survey-jquery@1.8.41/survey.jquery.min.js"></script>
    
    <!-- zoom script -->
    <!-- see: https://www.w3schools.com/howto/tryit.asp?filename=tryhow_js_image_zoom -->
    <script>
      function imageZoom(imgID, resultID) {
        var img, lens, result, cx, cy;
        img = document.getElementById(imgID);
        result = document.getElementById(resultID);
        /*create lens:*/
        lens = document.createElement("DIV");
        lens.setAttribute("class", "img-zoom-lens");
        /*insert lens:*/
        img.parentElement.insertBefore(lens, img);
        /*calculate the ratio between result DIV and lens:*/
        cx = result.offsetWidth / lens.offsetWidth;
        cy = result.offsetHeight / lens.offsetHeight;
        /*set background properties for the result DIV:*/
        result.style.backgroundImage = "url('" + img.src + "')";
        result.style.backgroundSize = (img.width * cx) + "px " + (img.height * cy) + "px";
        /*execute a function when someone moves the cursor over the image, or the lens:*/
        lens.addEventListener("mousemove", moveLens);
        img.addEventListener("mousemove", moveLens);
        /*and also for touch screens:*/
        lens.addEventListener("touchmove", moveLens);
        img.addEventListener("touchmove", moveLens);
        function moveLens(e) {
          var pos, x, y;
          /*prevent any other actions that may occur when moving over the image:*/
          e.preventDefault();
          /*get the cursor's x and y positions:*/
          pos = getCursorPos(e);
          /*calculate the position of the lens:*/
          x = pos.x - (lens.offsetWidth / 2);
          y = pos.y - (lens.offsetHeight / 2);
          /*prevent the lens from being positioned outside the image:*/
          if (x > img.width - lens.offsetWidth) {x = img.width - lens.offsetWidth;}
          if (x < 0) {x = 0;}
          if (y > img.height - lens.offsetHeight) {y = img.height - lens.offsetHeight;}
          if (y < 0) {y = 0;}
          /*set the position of the lens:*/
          lens.style.left = x + "px";
          lens.style.top = y + "px";
          /*display what the lens "sees":*/
          result.style.backgroundPosition = "-" + (x * cx) + "px -" + (y * cy) + "px";
        }
        function getCursorPos(e) {
          var a, x = 0, y = 0;
          e = e || window.event;
          /*get the x and y positions of the image:*/
          a = img.getBoundingClientRect();
          /*calculate the cursor's x and y coordinates, relative to the image:*/
          x = e.pageX - a.left;
          y = e.pageY - a.top;
          /*consider any page scrolling:*/
          x = x - window.pageXOffset;
          y = y - window.pageYOffset;
          return {x : x, y : y};
        }
      }
     </script>
  </head>
"""

    @staticmethod
    def _genenerate_html_body_template():
        # $survey_json - survey json string saved in a database
        # $jqueryselector - is to be substitutes with "$" as a workaround
        return Template("""
  <body>
    <div id="surveyContainer"></div>
    
    <!-- Init survey -->
    <script>
      Survey.StylesManager.applyTheme("modern");
      var surveyJSON = $survey_json
      function sendDataToServer(survey) {
          survey.sendResult('<TODO fill this with data from SurveyJS>');
      }
      var survey = new Survey.Model(surveyJSON);
      $jqueryselector("#surveyContainer").Survey({
          model: survey,
          onComplete: sendDataToServer
      });
    </script>
  </body>
""")


