from typing import override
from xml.dom.minidom import Document
from tree_sitter import Parser, Language
from tree_sitter_language_pack import get_parser as ts_get_parser, get_language
from builders.skeleton_builder import SkeletonBuilder
from builders.template_builder import TemplateBuilder
from builders.example_builder import ExampleBuilder
from abstract_factory import AbstractFactory
from languages.python.python_documenter import PythonDocumenter
from languages.python.python_example_builder import PythonExampleBuilder
from languages.python.python_skeleton_builder import PythonSkeletonBuilder
from languages.python.python_template_builder import PythonTemplateBuilder


class PythonFactory(AbstractFactory):
    
    def __init__(self):
        self._language = get_language("python")

    def get_language(self) -> Language:
        return self._language

    @override
    def get_parser(self) -> Parser:
        parser = Parser()
        parser.language = self.get_language()  # bind to the same Language
        return parser

    @override
    def get_documenter(self, model_name: str) -> Document:
        return PythonDocumenter(self, model_name)

    @override
    def get_example_builder(self) -> ExampleBuilder:
        return PythonExampleBuilder()

    @override
    def get_skeleton_builder(self) -> SkeletonBuilder:
        return PythonSkeletonBuilder()

    @override
    def get_template_builder(self) -> TemplateBuilder:
        return PythonTemplateBuilder()