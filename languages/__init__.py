from languages.language_config import LanguageConfig
from languages.python import PythonSkeletoniser
from languages.typescript import TypeScriptSkeletoniser

languages = {
    'python': LanguageConfig({
        'name': 'python',
        'extensions': [
            '.py'
        ],
        'skeletoniser' : PythonSkeletoniser,
        'template_directory':'languages/python/templates',
        'example_directory': 'languages/python/examples',
        'node_types':{
            "function_definition": "function",
            "class_definition": "class",
            "module": "module",
        },
        "insertion": "inside",
        "queries": [
            "(module . [(expression_statement (string) @module.docstring) (string) @module.docstring])",
            "(class_definition body: (block . [(expression_statement (string) @class.docstring) (string) @class.docstring]))",
            "(function_definition body: (block . [(expression_statement (string) @function.docstring) (string) @function.docstring]))"
        ]
    }),
    'typescript': LanguageConfig({
        'name': 'typescript',
        'extensions': [
            '.ts'
        ],
        'skeletoniser' : TypeScriptSkeletoniser,
        'template_directory':'languages/typescript/templates',
        'example_directory': 'languages/typescript/examples',
        'node_types':{
            "program":"module",
            "function_declaration": "function",
            "method_definition": "function",
            "class_declaration": "class",
            "interface_declaration": "interface"
        },
        "insertion": "before",
        "queries":[
            r'(program . (comment) @module.docstring (#match? @module.docstring "^/\\*\\*"))',
            r'((comment) @class.docstring . (class_declaration) (#match? @class.docstring "^/\\*\\*"))',
            r'((comment) @interface.docstring . (interface_declaration) (#match? @interface.docstring "^/\\*\\*"))',
            r'((comment) @function.docstring . (function_declaration) (#match? @function.docstring "^/\\*\\*"))',
            r'((comment) @method.docstring . (method_definition) (#match? @method.docstring "^/\\*\\*"))',
        ]
    })
}