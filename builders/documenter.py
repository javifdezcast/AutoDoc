import json
from pathlib import Path

import requests
from tree_sitter import Node, Parser, Query, QueryCursor

from builders.example_builder import ExampleBuilder
from builders.skeleton_builder import SkeletonBuilder
from builders.template_builder import TemplateBuilder


class Documenter:
    URL = "http://localhost:11434"
    DOCUMENTABLE_ELEMENTS: list[str] = []

    def __init__(self, model_name: str):
        self.path = None
        self.model_name = model_name
        self.parser: Parser = None
        self.template_builder: TemplateBuilder = None
        self.skeleton_builder: SkeletonBuilder = None
        self.example_builder: ExampleBuilder = None
        self.docstring_queries: list[Query] = None
        self._collected_docs = []

    def document_file(self, path: Path) -> None:
        self.path = path
        source = path.read_bytes()
        tree = self.parser.parse(source)
        stripped_file = self._strip_docstrings(source, tree.root_node)
        with open('results/stripped_' + path.name , "wb") as f:
            f.write(stripped_file)
        tree = self.parser.parse(stripped_file)
        self._collected_docs = []
        self._document(tree.root_node)
        output = self._insert_docs(source)
        with open('results/' + path.name , "wb") as f:
            f.write(output)

    def _strip_docstrings(self, file: bytes, node: Node):
        docstrings = self._collect_docstrings(node)
        docstrings.sort(key=lambda n: n.start_byte, reverse=True)
        result = bytearray(file)
        for ds_node in docstrings:
            del result[ds_node.start_byte:ds_node.end_byte]
        return bytes(result)

    def _collect_docstrings(self, n: Node) -> list[Node]:
        collected_docstrings = []
        for query in self.docstring_queries:
            cursor = QueryCursor(query)
            captures = cursor.captures(n)
            for nodes in captures.values():
                collected_docstrings.extend(nodes)
        return collected_docstrings

    def _document(self, node: Node) -> None:
        """Recurse into named children first, then document the current node."""
        for child in node.named_children:  # skip anonymous tokens
            self._document(child)
        if node.type in self.DOCUMENTABLE_ELEMENTS:
            self._generate_and_collect(node)

    def _generate_and_collect(self, node: Node) -> None:
        node_name = ''
        if node.child_by_field_name('name'):
            node_name = node.child_by_field_name('name').text.decode('utf-8')
        template = self.template_builder.build_template(node)
        skeleton = self.skeleton_builder.build_skeleton(node)
        with open('results/' + self.path.name + node_name + '.skeleton.txt', "w") as f:
            f.write(json.dumps(skeleton))
        example = self.example_builder.build_example(node)
        with open('results/' + self.path.name + node_name + '.example.txt', "w") as f:
            f.write(example)
        prompt = self._build_prompt(node, skeleton, example)
        with open('results/' + self.path.name + node_name + '.prompt.txt', "w") as f:
            f.write(prompt)
        """
        response = self._query_model(prompt)
        filled   = json.loads(response)
        """
        docstring = template.render(skeleton)
        with open('results/' + self.path.name + node_name + '.docstring.txt', "w") as f:
            f.write(docstring)
        self._collected_docs.append((node.start_byte, docstring))

        # ------------------------------------------------------------------
        # Source insertion — done in reverse order to preserve byte offsets
        # ------------------------------------------------------------------

    def _insert_docs(self, source: bytes) -> bytes:
        # Sort descending by position so earlier insertions don't shift offsets
        for start_byte, docstring in sorted(self._collected_docs, reverse=True):
            insertion = docstring.encode("utf-8")
            source = source[:start_byte] + insertion + source[start_byte:]
        return source

    def _query_model(self, prompt: str) -> str:
        resp = requests.post(
            self.URL.rstrip("/") + "/api/generate",
            json={"model": self.model_name, "prompt": prompt, "stream": False,
                  "options": {"temperature": 0.3}},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["response"]

    def _build_prompt(self, node: Node, skeleton: dict, example: str) -> str:
        return (
            f"You are an expert software engineer writing API documentation (docstrings) "
            f"for {self.language} code.\n\n"
            f"Your task is to complete the provided dictionary skeleton by replacing each "
            f"'<placeholder>' with an accurate, concise description based solely on the "
            f"code snippet provided.\n\n"
            f"# Rules:\n"
            f"- Only document what is explicitly present in the code.\n"
            f"- For 'raises' or 'exceptions': only include exceptions that propagate to the "
            f"caller. Do NOT include exceptions that are caught and handled within the code.\n"
            f"- If a property has no corresponding content in the code (e.g., no parameters, "
            f"no return value), set its value to null.\n"
            f"- Output ONLY the completed dictionary. No explanations, no markdown fences, "
            f"no extra text.\n\n"
            f"# Examples:\n{example}\n\n"
            f"# Code to document:\n"
            f"```{self.language}\n{node.text.decode("utf-8")}\n```\n\n"
            f"# Dictionary skeleton to complete:\n"
            f"{skeleton}"
        )