from builders.documenter import Documenter
from builders.skeleton_builder import SkeletonBuilder
from builders.template_builder import TemplateBuilder
from builders.example_builder import ExampleBuilder
from tree_sitter import Parser

from languages import python
from languages.python.PythonFactory import PythonFactory


class Factory:

    @classmethod
    def get_example_builder(cls) -> ExampleBuilder:
        pass

    @classmethod
    def get_skeleton_builder(cls) -> SkeletonBuilder:
        pass

    @classmethod
    def get_template_builder(cls) -> TemplateBuilder:
        pass

    @classmethod
    def get_parser(cls) -> Parser:
        pass

    @classmethod
    def getDocumenter(cls) -> Documenter:
        pass

class FactoryFactory:
    SUPPORTED_LANGUAGES = {"python", "typescript"}

    @classmethod
    def getFactory(cls, language: str) -> Factory:
        factory: Factory = None
        if language.lower() in cls.SUPPORTED_LANGUAGES:
            if language.lower() == python:
                factory = PythonFactory()
        else:
            raise Exception(f'Language {language} is not supported')
        return factory
