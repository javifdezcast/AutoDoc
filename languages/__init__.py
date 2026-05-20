from languages.python.python_documenter import PythonDocumenter
from languages.python.python_example_builder import PythonExampleBuilder
from languages.python.python_skeleton_builder import PythonSkeletonBuilder
from languages.python.python_template_builder import PythonTemplateBuilder

languages = {
    'python': {
        'name': 'python',
        'classes': {
            'documenter' : PythonDocumenter,
            'example_builder' : PythonExampleBuilder,
            'skeleton_builder' : PythonSkeletonBuilder,
            'template_builder' : PythonTemplateBuilder,
        }
    }
}
python = 'python'