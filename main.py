# This is a sample Python script.
import json
from pathlib import Path
from factory import Factory
from file_finder import FileFinder


def main():
    config = json.load(open('config.json'))
    files_to_document = FileFinder.find_different_files(config)
    documenter = Factory.get_documenter(config['language'], config['llm']['model'])
    for i, file in enumerate(files_to_document, start=1):
        print(f"Documenting file {i}/{len(files_to_document)}: {file}")
        documenter.document_file(Path(file))

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
