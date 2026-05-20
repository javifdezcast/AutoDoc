import json
from pathlib import Path

import requests
from tree_sitter import Node, Parser, Query, QueryCursor, Language

from builders.example_builder import ExampleBuilder
from builders.skeleton_builder import SkeletonBuilder
from builders.template_builder import TemplateBuilder


class Documenter:
    URL = "http://localhost:11434"
    DOCUMENTABLE_ELEMENTS: list[str] = []

    _language_name: str = None
    _language: Language = None
    _parser: Parser = None
    _template_builder: TemplateBuilder = None
    _skeleton_builder: SkeletonBuilder = None
    _example_builder: ExampleBuilder = None

    # Getters and setters
    @property
    def language(self):
        raise AttributeError("language is not readable")

    @language.setter
    def language(self, value: Language) -> None:
        self._language = value

    @property
    def parser(self):
        raise AttributeError("parser is not readable")

    @parser.setter
    def parser(self, value: Parser) -> None:
        self._parser = value

    @property
    def template_builder(self):
        raise AttributeError("template_builder is not readable")

    @template_builder.setter
    def template_builder(self, value: TemplateBuilder) -> None:
        self._template_builder = value

    @property
    def skeleton_builder(self):
        raise AttributeError("skeleton_builder is not readable")

    @skeleton_builder.setter
    def skeleton_builder(self, value: SkeletonBuilder) -> None:
        self._skeleton_builder = value

    @property
    def example_builder(self):
        raise AttributeError("example_builder is not readable")

    @example_builder.setter
    def example_builder(self, value: ExampleBuilder) -> None:
        self._example_builder = value

    def create_docstring_queries(self):
        pass

    # Constructor
    def __init__(self, model_name):
        self.model_name = model_name
        self._collected_docs = []
        self.config = json.loads(Path("config.json").read_text())

    # Public document file method
    def document_file(self, path: Path) -> None:
        self.path = path
        source = path.read_bytes()
        tree = self._parser.parse(source)
        stripped_file = self._strip_docstrings(source, tree.root_node)
        with open('results/stripped_' + path.name , "wb") as f:
            f.write(stripped_file)
        tree = self._parser.parse(stripped_file)
        self._collected_docs = []
        self._document(tree.root_node)
        self.docstring_queries: list[Query] = []

    # Private documentation methods
    def _strip_docstrings(self, file: bytes, node: Node):
        docstrings = self._collect_docstrings(node)
        docstrings.sort(key=lambda n: n.start_byte, reverse=True)
        result = bytearray(file)
        for ds_node in docstrings:
            del result[ds_node.start_byte:ds_node.end_byte]
        return bytes(result)

    def _collect_docstrings(self, n: Node) -> list[Node]:
        collected_docstrings = []
        for i, query in enumerate(self.docstring_queries):
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
        template = self._template_builder.build_template(node)
        skeleton = self._skeleton_builder.build_skeleton(node)
        with open('results/skeleton/' + self.path.name + node_name + '.skeleton.txt', "w") as f:
            f.write(json.dumps(skeleton))
        example = self._example_builder.build_example(node)
        prompt = self._build_prompt(node, skeleton, example)
        response = self._query_model(prompt)
        docstring = template.render(json.loads(response))
        with open('results/docs/' + self.path.name + node_name + '.docstring.txt', "w") as f:
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
            self.config['llm']['base_url'].rstrip("/") + "/api/generate",
            json={
                "model": self.config['llm']['model'],
                "prompt": prompt,
                "think": False,
                "stream": False,
                "format": "json",
                "options": {"temperature": self.config['llm']['temperature']}},
            timeout=600,
        )
        resp.raise_for_status()
        return resp.json()["response"]

    def _build_prompt(self, node: Node, skeleton: dict, example: str) -> str:
        return (
            f"You are an expert software engineer writing API documentation (docstrings) "
            f"for {self._language.name} code.\n\n"
            f"Your task is to complete the provided dictionary skeleton by replacing each "
            f"'<placeholder>' with an accurate, concise description based solely on the "
            f"code snippet provided.\n\n"
            f"# Rules:\n"
            f"- # Rules"
            f"1. ALWAYS write a description for the function itself, every parameter, "
            f"   and the return value if one exists. These fields must NEVER be null "
            f"   when the code contains them.\n"
            f"2. Use null ONLY for these specific cases:\n"
            f"   - 'returns' is null if the function has no return statement or returns None implicitly\n"
            f"   - 'example' is null if no usage example is obvious from the code\n"
            f"   - A 'raises' entry is null only if no exception propagates to the caller\n"
            f"3. Base descriptions strictly on the code — do not invent behavior.\n"
            f"4. Output ONLY the completed dictionary as valid JSON. No prose, no fences.\n"
            f"# Examples:\n{example}\n\n"
            f"# Code to document:\n"
            f"```{self._language.name}\n{node.text.decode("utf-8")}\n```\n\n"
            f"# Dictionary skeleton to complete:\n"
            f"{skeleton}"
        )
