from tree_sitter import Query
from builders.documenter import Documenter


class TypeScriptDocumenter(Documenter):
    LANGUAGE_NAME = 'typescript'

    DOCUMENTABLE_ELEMENTS: list[str] = [
        'program',
        'class_declaration',
        'interface_declaration',
        'function_declaration',
        'method_definition',
    ]

    MODULE_DOCSTRING_QUERY = r"""
    (program
      .
      (comment) @module.docstring
      (#match? @module.docstring "^/\\*\\*"))
    """

    CLASS_DOCSTRING_QUERY = r"""
    ((comment) @class.docstring
     .
     (class_declaration)
     (#match? @class.docstring "^/\\*\\*"))
    """

    INTERFACE_DOCSTRING_QUERY = r"""
    ((comment) @interface.docstring
     .
     (interface_declaration)
     (#match? @interface.docstring "^/\\*\\*"))
    """

    FUNCTION_DOCSTRING_QUERY = r"""
    ((comment) @function.docstring
     .
     (function_declaration)
     (#match? @function.docstring "^/\\*\\*"))
    """

    METHOD_DOCSTRING_QUERY = r"""
    ((comment) @method.docstring
     .
     (method_definition)
     (#match? @method.docstring "^/\\*\\*"))
    """

    def __init__(self, model_name: str):
        super().__init__(model_name)

    def create_docstring_queries(self):
        self.docstring_queries = []
        self.docstring_queries.append(Query(self._language, self.MODULE_DOCSTRING_QUERY))
        self.docstring_queries.append(Query(self._language, self.FUNCTION_DOCSTRING_QUERY))
        self.docstring_queries.append(Query(self._language, self.CLASS_DOCSTRING_QUERY))
        self.docstring_queries.append(Query(self._language, self.INTERFACE_DOCSTRING_QUERY))
        self.docstring_queries.append(Query(self._language, self.METHOD_DOCSTRING_QUERY))