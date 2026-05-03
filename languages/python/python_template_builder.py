from template_builder import TemplateBuilder

TEMPLATE_MAP = {
    "function_definition": "function",
    "class_definition": "class",
    "module": "module",
}

class PythonTemplateBuilder(TemplateBuilder):
    def __init__(self):
        super().__init__(
            template_dir="languages/python",
            template_map=TEMPLATE_MAP,
        )