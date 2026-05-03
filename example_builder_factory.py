from languages.python.python_example_builder import PythonExampleBuilder
from example_builder import ExampleBuilder


class ExampleBuilderFactory:
    python = 'python'
    type_script = 'TypeScript'

    @classmethod
    def get_example_builder(cls, language: str) -> ExampleBuilder:
        if language == cls.python:
            return PythonExampleBuilder()
        elif language == cls.type_script:
            return None
