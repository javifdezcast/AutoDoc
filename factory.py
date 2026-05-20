from tree_sitter import Parser
from tree_sitter_language_pack import get_language
from builders.documenter import Documenter
from languages import languages

class Factory:

    @classmethod
    def get_documenter(cls, language_name: str, model_name: str) -> Documenter:
        try:
            classes = languages[language_name]['classes']
            language = get_language(language_name)
            documenter: Documenter = classes['documenter'](model_name)
            documenter.language = language
            documenter.parser = Parser(language)
            documenter.template_builder = classes['template_builder']()
            documenter.skeleton_builder = classes['skeleton_builder']()
            documenter.example_builder = classes['example_builder']()
            documenter.create_docstring_queries()
        except KeyError as e:
            raise Exception(f'Language {language_name} not supported')
        return documenter