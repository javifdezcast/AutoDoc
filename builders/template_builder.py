from jinja2 import Template
from tree_sitter import Node

class TemplateBuilder:
    def __init__(self, template_dir: str, template_map: dict[str, str]):
        self.template_dir = template_dir
        self.template_map = template_map

    def build_template(self, node: Node) -> Template:
        element_type = self.template_map.get(node.type)
        if element_type is None:
            raise ValueError(f"Unsupported node type: '{node.type}'")

        template_path = f"{self.template_dir}/{element_type}"
        with open(template_path, "r", encoding="utf-8") as f:
            source = f.read()

        return Template(source)