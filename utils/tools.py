import json
import re


def minify_json(json_str):
    """
    A simple method to minify json string by removing whitespaces from each line
    and deleting empty lines.
    :param json_str:
    :return:
    """
    striped_json = [line.strip() for line in json_str.split('\n') if line != ""]
    return "".join(striped_json)
