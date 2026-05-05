from tree_sitter import Node

class ExampleBuilder:
    def __init__(self, example_dir: str, example_map: dict[str, str]):
        self.example_dir = example_dir
        self.example_map = example_map

    def build_example(self, node: Node) -> str:
        element_type = self.example_map.get(node.type)
        if element_type is None:
            raise ValueError(f"Unsupported node type: '{node.type}'")

        example_path = f"{self.example_dir}/{element_type}"
        with open(example_path, "r", encoding="utf-8") as f:
            source = f.read()

        return source