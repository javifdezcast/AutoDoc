# This is a sample Python script.
import json
from pathlib import Path
from urllib.request import Request

from jinja2 import Template
from tree_sitter import Node

from documenter import FileDocumenter
from git import Git


def main():
    config = json.load(open('config.json'))
    files_to_document = Git.find_different_files()
    documenter = FileDocumenter(config['language'], config['model'])
    for file in files_to_document:
        documenter.document_file(Path(file))






# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
