from xml.dom.minidom import Document

from builders.skeleton_builder import SkeletonBuilder
from builders.template_builder import TemplateBuilder
from builders.example_builder import ExampleBuilder
from factory import Factory
from languages.python.python_documenter import PythonDocumenter
from languages.python.python_example_builder import PythonExampleBuilder
from languages.python.python_skeleton_builder import PythonSkeletonBuilder
from languages.python.python_template_builder import PythonTemplateBuilder
from languages.__init__ import python
from tree_sitter import Parser
from tree_sitter_language_pack import get_parser as ts_get_parser


class PythonFactory(Factory):

    @classmethod
    def get_example_builder(cls) -> ExampleBuilder:
        return PythonExampleBuilder()

    @classmethod
    def get_skeleton_builder(cls) -> SkeletonBuilder:
        return PythonSkeletonBuilder()

    @classmethod
    def get_template_builder(cls) -> TemplateBuilder:
        return PythonTemplateBuilder()

    @classmethod
    def get_parser(cls) -> Parser:
        return ts_get_parser(python)

    @classmethod
    def getDocumenter(cls, model_name: str) -> Document:
        return PythonDocumenter(model_name)