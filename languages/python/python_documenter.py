from tree_sitter import Language, Query
from tree_sitter_language_pack import get_language
from builders.documenter import Documenter
from factory import Factory
from languages import python
from languages.python.PythonFactory import PythonFactory


class PythonDocumenter(Documenter):
    LANGUAGE_NAME = python
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

    def __init__(self, model_name: str):
        super().__init__(model_name)
        self.path = None
        self.language = Language(get_language(self.LANGUAGE_NAME))
        self.model_name = model_name
        self.parser = PythonFactory.get_parser()
        self.template_builder = Factory.get_template_builder()
        self.skeleton_builder = Factory.get_skeleton_builder()
        self.example_builder = Factory.get_example_builder()
        self.create_docstring_queries()

    def create_docstring_queries(self):
        self.docstring_queries = []
        self.docstring_queries.append(Query(self.MODULE_DOCSTRING_QUERY))
        self.docstring_queries.append(Query(self.FUNCTION_DOCSTRING_QUERY))
        self.docstring_queries.append(Query(self.CLASS_DOCSTRING_QUERY))