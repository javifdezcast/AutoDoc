from languages.python.python_skeleton_builder import PythonSkeletonBuilder
from skeleton_builder import SkeletonBuilder


class SkeletonBuilderFactory:
    python = 'python'
    type_script = 'TypeScript'

    @classmethod
    def get_skeleton_builder(cls, language: str) -> SkeletonBuilder:
        if language == cls.python:
            return PythonSkeletonBuilder()
        elif language == cls.type_script:
            return None