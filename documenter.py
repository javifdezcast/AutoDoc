import json
import requests
import tree_sitter
from tree_sitter import Node
from pathlib import Path
from factories.factory import Factory


class FileDocumenter:
    URL = "http://localhost:11434"
    DOCUMENTABLE_ELEMENTS: list[str] = []

    def __init__(self, language: str, model_name: str):
        self.language = language
        self.model_name = model_name
        self.parser = Factory().get_parser(language)
        self.template_builder = Factory.get_template_builder(language)
        self.skeleton_builder = Factory.get_skeleton_builder(language)
        self.example_builder = Factory.get_example_builder(language)
        self.collected_docs = []

    def document_file(self, path: Path) -> None:
        source = path.read_bytes()
        tree_sitter.Parser().parse(source)
        tree = self.parser.parse(source)
        stripped_file = self._strip_docstrings(source, tree)
        self._collected_docs = []
        self._document(tree.root_node)
        output = self._insert_docs(source)
        path.write_bytes(output)

    def _strip_docstrings(self, file: bytes, node: Node):
        return None

    def _document(self, node: Node) -> None:
        """Recurse into named children first, then document the current node."""
        for child in node.named_children:       # skip anonymous tokens
            self._document(child)
        if node.type in self.DOCUMENTABLE_ELEMENTS:
            already_documented = self._has_docstring(node)
            if not already_documented:
                self._generate_and_collect(node)

    def _generate_and_collect(self, node: Node) -> None:
        template = self.template_builder.build_template(node)
        skeleton = self.skeleton_builder.build_skeleton(node)
        example  = self.example_builder.build_example(node)
        prompt   = self._build_prompt(node, skeleton, example)
        response = self._query_model(prompt)
        filled   = json.loads(response)
        docstring = template.render(filled)
        self._collected_docs.append((node.start_byte, docstring))

    def _has_docstring(self, node: Node) -> bool:
        """
        Check whether the node already has a leading doc comment.
        Implementation depends on language; override in subclasses.
        """
        raise NotImplementedError

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