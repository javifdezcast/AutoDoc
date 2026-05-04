from builders.skeleton_builder import SkeletonBuilder
from builders.template_builder import TemplateBuilder
from builders.example_builder import ExampleBuilder
from languages.python.python_example_builder import PythonExampleBuilder
from languages.python.python_skeleton_builder import PythonSkeletonBuilder
from languages.python.python_template_builder import PythonTemplateBuilder
from tree_sitter import Parser
from tree_sitter_language_pack import get_parser as ts_get_parser


class Factory:
    python = 'python'
    type_script = 'TypeScript'

    SUPPORTED_LANGUAGES = {"python", "typescript"}

    @classmethod
    def get_example_builder(cls, language: str) -> ExampleBuilder:
        if language == cls.python:
            return PythonExampleBuilder()
        elif language == cls.type_script:
            return None
    @classmethod
    def get_skeleton_builder(cls, language: str) -> SkeletonBuilder:
        if language == cls.python:
            return PythonSkeletonBuilder()
        elif language == cls.type_script:
            return None

    @classmethod
    def get_template_builder(cls, language: str) -> TemplateBuilder:
        if language == cls.python:
            return PythonTemplateBuilder()
        elif language == cls.type_script:
            return None

    @classmethod
    def get_parser(cls, language: str) -> Parser:
        lang = language.lower()
        if lang not in cls.SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: '{language}'. "
                             f"Supported: {cls.SUPPORTED_LANGUAGES}")
        return ts_get_parser(lang)