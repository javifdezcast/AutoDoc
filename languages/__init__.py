from languages.python.python_documenter import PythonDocumenter
from languages.python.python_skeleton_builder import PythonSkeletonBuilder

languages = {
    'python': {
        'name': 'python',
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
        }
    },
    'typescript': {
        'name': 'typescript',
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
        }
    }
}
python = 'python'