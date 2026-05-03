# This is a sample Python script.
import json
from pathlib import Path
from urllib.request import Request

from jinja2 import Template
from tree_sitter import Node

from skeleton_builder_factory import SkeletonBuilderFactory
# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
from template_builder_factory import TemplateBuilderFactory
from example_builder_factory import ExampleBuilderFactory



class FileDocumenter():
    LANGUAGE = ''
    DOCUMENTABLE_ELEMENTS = ['']
    URL = ''

    def __init__(self, language: str):
        self.language = FileDocumenter.LANGUAGE
        self.template_builder = TemplateBuilderFactory.get_template_builder()
        self.skeleton_builder = SkeletonBuilderFactory.get_skeleton_builder()
        self.example_builder = ExampleBuilderFactory.get_example_builder()

    def document_file(path: Path):
        tree = parse(read(path))
        document(element)
        file.write(element.unparse())

    def document(self, element):
        if element.hasChildren():
            self.document(element)
        else:
            if element.type in self.DOCUMENTABLE_ELEMENTS:
                template = self.template_builder.build_template(element)
                skeleton = self.skeleton_builder.build_skeleton(element)
                example = self.example_builder.build_example(element)
                prompt = self._build_prompt(element, template, skeleton, example)
                response = self._build_request(prompt)
                template.value = json(response.body())
                element.__doc__ = template.render()

    def _build_request(self, prompt, url) -> Request:
        return Request()

    def _build_prompt(self, node: Node, template: Template, skeleton: dict, example: str) -> str:
        return ''




# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print_hi('PyCharm')

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
