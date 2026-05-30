from languages.python.python_documenter import PythonDocumenter
from languages.python.python_skeleton_builder import PythonSkeletonBuilder
from languages.typescript.typescript_documenter import TypeScriptDocumenter
from languages.typescript.typescript_skeleton_builder import TypeScriptSkeletonBuilder

languages = {
    'python': {
        'name': 'python',
        'extensions': [
            '.py'
        ],
        'classes': {
            'documenter' : PythonDocumenter,
            'skeleton_builder' : PythonSkeletonBuilder
        },
        'template_directory':'languages/python/templates',
        'example_directory': 'languages/python/example',
        'node_types':{
            "function_definition": "function",
            "class_definition": "class",
            "module": "module",
        },
        "insertion": "inside"
    },
    'typescript': {
        'name': 'typescript',
        'extensions': [
            '.ts'
        ],
        'classes': {
            'documenter' : TypeScriptDocumenter,
            'skeleton_builder' : TypeScriptSkeletonBuilder
        },
        'template_directory':'languages/typescript/templates',
        'example_directory': 'languages/typescript/example',
        'node_types':{
            "program":"module",
            "function_declaration": "function",
            "method_definition": "function",
            "class_declaration": "class",
            "interface_declaration": "interface"
        },
        "insertion": "before"
    }
}