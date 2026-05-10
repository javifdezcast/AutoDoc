from abstract_factory import AbstractFactory
from languages import python
from languages.python.PythonFactory import PythonFactory


class FactoryFactory:
    SUPPORTED_LANGUAGES = {"python", "typescript"}

    @classmethod
    def getFactory(cls, language: str) -> AbstractFactory:
        factory: AbstractFactory = None
        if language.lower() in cls.SUPPORTED_LANGUAGES:
            if language.lower() == python:
                factory = PythonFactory()
        else:
            raise Exception(f'Language {language} is not supported')
        return factory
