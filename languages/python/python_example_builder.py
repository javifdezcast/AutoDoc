from example_builder import ExampleBuilder

TEMPLATE_MAP = {
    "function_definition": "function",
    "class_definition": "class",
    "module": "module",
}

class PythonExampleBuilder(ExampleBuilder):
    def __init__(self):
        super().__init__(
            example_dir="languages/python",
            example_map=TEMPLATE_MAP,
        )