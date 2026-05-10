from tree_sitter import Query
from tree_sitter_language_pack import get_language
from builders.documenter import Documenter
from factory_factory import AbstractFactory


class PythonDocumenter(Documenter):
    LANGUAGE_NAME = 'python'
    DOCUMENTABLE_ELEMENTS: list[str] = ['class_definition', 'module', 'function_definition']

    MODULE_DOCSTRING_QUERY = """
    (module
      .
      (expression_statement
        (string) @module.docstring))
    """
    CLASS_DOCSTRING_QUERY = """
    (class_definition
      body: (block
        .
        (expression_statement
          (string) @class.docstring)))
    """
    FUNCTION_DOCSTRING_QUERY = """
    (function_definition
      body: (block
        .
        (expression_statement
          (string) @function.docstring)))
    """

    def __init__(self,factory: AbstractFactory, model_name: str):
        super().__init__(model_name)
        self.path = None
        self.language = factory.get_language()
        self.model_name = model_name
        self.parser = factory.get_parser()
        self.template_builder = factory.get_template_builder()
        self.skeleton_builder = factory.get_skeleton_builder()
        self.example_builder = factory.get_example_builder()
        self.create_docstring_queries()

    def create_docstring_queries(self):
        self.docstring_queries = []
        self.docstring_queries.append(Query(self.language, self.MODULE_DOCSTRING_QUERY))
        self.docstring_queries.append(Query(self.language, self.FUNCTION_DOCSTRING_QUERY))
        self.docstring_queries.append(Query(self.language, self.CLASS_DOCSTRING_QUERY))