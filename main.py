# This is a sample Python script.
import json
from datetime import datetime
from pathlib import Path
from builders import Documenter
from file_finder import FileFinder


def main():
    config = json.load(open('config.json'))
    files_to_document = find_files(config)
    document_files(config, files_to_document)


def document_files(config, files_to_document: list[str]):
    documenter = Documenter(config)
    for i, file in enumerate(files_to_document, start=1):
        time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"{time} Documenting file {i}/{len(files_to_document)}: {file}")
        documenter.document_file(i, Path(file))


def find_files(config: dict) -> list[str]:
    finder = FileFinder(config)
    return finder.find_different_files()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
