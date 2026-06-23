from tree_sitter import Node

class Builder:

    @classmethod
    def build(cls, directory: str, node_map: dict, node: Node) -> str:
        element_type = node_map.get(node.type)
        if element_type is None:
            raise ValueError(f"Unsupported node type: '{node.type}'")

        example_path = f"{directory}/{element_type}"
        with open(example_path, "r", encoding="utf-8") as f:
            source = f.read()

        return source