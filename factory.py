from tree_sitter_language_pack import get_language

from builders.documenter import Documenter

from languages.python.PythonFactory import python_objects




class AbstractFactory:

    _language_objects = {
        'python': python_objects
    }

    def __init__(self, language: str):
        self._language_name = language


    def get_documenter(self, language, model_name: str) -> Documenter:
        documenter: Documenter = self._language_objects[self._language_name]['documenter'](model_name)
        documenter.language(get_language(language))
        documenter.set_parser(self._language_objects[self._language_name]['parser']())
        documenter.set_templ(self._language_objects[self._language_name]['template_builder']())
        documenter.set_language(self._language_objects[self._language_name]['skeleton_builder']())
        documenter.set_language(self._language_objects[self._language_name]['example_builder']())
        return documenter
