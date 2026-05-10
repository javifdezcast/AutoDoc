# This is a sample Python script.
import json
from pathlib import Path

from pip._internal.resolution.resolvelib import factory

from factory import Factory, FactoryFactory
from languages.python.python_documenter import PythonDocumenter
from git import Git


def main():
    config = json.load(open('config.json'))
    files_to_document = Git.find_different_files()
    factory = FactoryFactory.getFactory(config['language'])
    documenter = factory.getDocumenter(config['model'])
    for file in files_to_document:
        documenter.document_file(Path(file))






# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
