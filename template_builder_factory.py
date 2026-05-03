from languages.python.python_template_builder import PythonTemplateBuilder
from template_builder import TemplateBuilder


class TemplateBuilderFactory:
    python = 'python'
    type_script = 'TypeScript'

    @classmethod
    def get_template_builder(cls, language: str) -> TemplateBuilder:
        if language == cls.python:
            return PythonTemplateBuilder()
        elif language == cls.type_script:
            return None