from tree_sitter import Parser
from tree_sitter_language_pack import get_language
from builders.documenter import Documenter
from builders.example_builder import ExampleBuilder
from builders.template_builder import TemplateBuilder
from languages import languages

class Factory:

    @classmethod
    def get_documenter(cls, language_name: str, model_name: str) -> Documenter:
        try:
            # Get parameters
            language_config = languages[language_name]
            classes = language_config['classes']
            template_dir = f'languages/{language_config['name']}/templates'
            example_dir = f'languages/{language_config['name']}/examples'
            node_type = language_config['node_types']
            # Initialise language
            language = get_language(language_name)
            # Create documenters and set attributes
            documenter: Documenter = classes['documenter'](model_name)
            documenter.language = language
            documenter.parser = Parser(language)
            documenter.skeleton_builder = classes['skeleton_builder']()
            documenter.template_builder = TemplateBuilder(template_dir, node_type)
            documenter.example_builder = ExampleBuilder(example_dir, node_type)
            documenter.create_docstring_queries()
        except KeyError as e:
            raise Exception(f'Language {language_name} not supported')
        return documenter
