from builders.documenter import Documenter
from builders.skeleton_builder import SkeletonBuilder
from builders.template_builder import TemplateBuilder
from builders.example_builder import ExampleBuilder
from tree_sitter import Parser, Language


class AbstractFactory:

    def get_example_builder(cls) -> ExampleBuilder:
        pass

    def get_skeleton_builder(cls) -> SkeletonBuilder:
        pass

    def get_template_builder(cls) -> TemplateBuilder:
        pass

    def get_parser(cls) -> Parser:
        pass

    def get_documenter(cls, model_name: str) -> Documenter:
        pass

    def get_language(cls) -> Language:
        pass