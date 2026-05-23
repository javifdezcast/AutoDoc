from tree_sitter import Query
from builders.documenter import Documenter

class PythonDocumenter(Documenter):
    DOCUMENTABLE_ELEMENTS: list[str] = ['class_definition', 'module', 'function_definition']

    MODULE_DOCSTRING_QUERY = """
    (module
      .
      [
        (expression_statement (string) @module.docstring)
        (string) @module.docstring
      ])
    """

    CLASS_DOCSTRING_QUERY = """
    (class_definition
      body: (block
        .
        [
          (expression_statement (string) @class.docstring)
          (string) @class.docstring
        ]))
    """

    FUNCTION_DOCSTRING_QUERY = """
    (function_definition
      body: (block
        .
        [
          (expression_statement (string) @function.docstring)
          (string) @function.docstring
        ]))
    """

    def __init__(self, model_name: str):
        super().__init__(model_name)

    def create_docstring_queries(self):
        self.docstring_queries = []
        self.docstring_queries.append(Query(self._language, self.MODULE_DOCSTRING_QUERY))
        self.docstring_queries.append(Query(self._language, self.FUNCTION_DOCSTRING_QUERY))
        self.docstring_queries.append(Query(self._language, self.CLASS_DOCSTRING_QUERY))