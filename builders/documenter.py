import json
from logging import config
from pathlib import Path

import requests
from tree_sitter import Node, Parser, Query, QueryCursor, Language

from builders.example_builder import ExampleBuilder
from builders.skeleton_builder import SkeletonBuilder
from builders.template_builder import TemplateBuilder


class Documenter:
    URL = "http://localhost:11434"
    DOCUMENTABLE_ELEMENTS: list[str] = []

    _language: Language = None
    _parser: Parser = None
    _template_builder: TemplateBuilder = None
    _skeleton_builder: SkeletonBuilder = None
    _example_builder: ExampleBuilder = None
    _insertion: str = None

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

    @property
    def insertion(self):
        raise AttributeError("insertion is not readable")

    @insertion.setter
    def insertion(self, value: str) -> None:
        self._insertion = value

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
        self._document(tree.root_node, stripped_file)
        documented_file = self._insert_docs(stripped_file)
        self._save_file(documented_file, path)

    def _save_file(self, documented_file: bytes, path: Path):
        if self.config['mode'] == 'clone':
            documented_path = self._results_path(path, "documented")
        else:
            documented_path = path
        documented_path.write_bytes(documented_file)

    def _results_path(self, path: Path, prefix: str = "") -> Path:
        """
        Build a results path preserving the original repo structure.

        Example:
            root_dir = "/repo"
            path = "/repo/pkg/file.py"

            -> results/documented/pkg/file.py
        """
        relative_path = path.relative_to(Path(self.config['root_dir']))
        output_path = Path("results") / prefix / relative_path

        output_path.parent.mkdir(parents=True, exist_ok=True)

        return output_path

    # Private documentation methods
    def _strip_docstrings(self, file: bytes, node: Node)-> bytes:
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

    def _document(self, node: Node, file: bytes) -> None:
        """Recurse into named children first, then document the current node."""
        for child in node.named_children:  # skip anonymous tokens
            self._document(child, file)
        if node.type in self.DOCUMENTABLE_ELEMENTS:
            self._generate_and_collect(node, file)

    def _generate_and_collect(self, node: Node, file: bytes) -> None:
        node_name = ''
        if node.child_by_field_name('name'):
            node_name = node.child_by_field_name('name').text.decode('utf-8')
        insertion_point = self._find_insertion_point(node, self._insertion)
        tabulation = self._find_indentation(insertion_point, self._insertion, file)
        template = self._template_builder.build_template(node)
        skeleton = self._skeleton_builder.build_skeleton(node)
        with open('results/skeleton/' + self.path.name + "_" + node_name + '.skeleton.txt', "w") as f:
            f.write(json.dumps(skeleton))
        example = self._example_builder.build_example(node)
        prompt = self._build_prompt(node, skeleton, example)
        with open('results/prompts/' + self.path.name + "_" + node_name + '.docstring.txt', "w") as f:
            f.write(prompt)
        response = self._query_model(prompt)
        docstring = template.render(json.loads(response)) + "\n"
        with open('results/docs/' + self.path.name + "_" + node_name + '.docstring.txt', "w") as f:
            f.write(docstring)
        self._collected_docs.append((insertion_point, docstring, tabulation))

        # ------------------------------------------------------------------
        # Source insertion — done in reverse order to preserve byte offsets
        # ------------------------------------------------------------------

    def _insert_docs(self, source: bytes) -> bytes:
        """
        Splice every collected docstring into `source` at its recorded position.

        Insertions are applied in *descending* byte-offset order so that each
        splice does not shift the offsets that still need to be processed.

        For each entry the docstring is re-indented so that every line after the
        first receives the stored indentation prefix.
        """
        for start_byte, docstring, indentation in sorted(
                self._collected_docs, key=lambda t: t[0], reverse=True
        ):
            lines = docstring.splitlines()

            if lines:
                indented_doc = lines[0]

                if len(lines) > 1:
                    indented_doc += '\n' + '\n'.join(
                        indentation + line if line.strip() else line
                        for line in lines[1:]
                    )
            else:
                indented_doc = ''

            # Ensure the inserted block ends with an indented newline.
            if not indented_doc.endswith('\n'):
                indented_doc += '\n'

            indented_doc = indented_doc[:-1] + '\n' + indentation

            payload = indented_doc.encode('utf-8')
            source = source[:start_byte] + payload + source[start_byte:]

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
            f"for {self.config['language']} code.\n\n"
            f"Your task is to complete the provided dictionary skeleton by replacing each "
            f"'<placeholder>' with an accurate, concise description based solely on the "
            f"code snippet provided.\n\n"
            f"# Rules:\n"
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
            f"```{self.config['language']}\n{node.text.decode("utf-8")}\n```\n\n"
            f"# Dictionary skeleton to complete:\n"
            f"{skeleton}"
        )

    def _find_insertion_point(self, node: Node, placement: str) -> int:
        if placement == 'inside':
            # Python-style: insertion goes as the first statement inside the body.
            body = node.child_by_field_name('body')
            if body is None:
                # Fallback: some grammars expose the body differently; look for
                # a 'block', 'statement_block', or similar child.
                for child in node.children:
                    if child.type in ('block', 'statement_block', 'class_body'):
                        body = child
                        break
            if body is None or body.child_count == 0:
                # Empty body (e.g. a stub with just `pass` missing): fall back
                # to the node's own start so the caller can decide.
                return node.start_byte
            return body.children[0].start_byte

        if placement == 'before':
            # Walk backwards through preceding siblings while they are
            # decorators/annotations attached to this declaration.
            decorator_types = {
                'decorator',  # Python, TypeScript
                'annotation',  # Java
                'marker_annotation',  # Java
                'attribute',  # C#-like grammars
            }
            target = node
            sibling = node.prev_sibling
            while sibling is not None and sibling.type in decorator_types:
                target = sibling
                sibling = sibling.prev_sibling
            return target.start_byte

        raise ValueError(f"Unknown placement: {placement!r}")

    def _find_indentation(self, start_byte: int, placement: str, source: bytes) -> str:
        """Return the indentation (run of spaces/tabs) of the line the
        insertion point lives on.

        For 'before', start_byte sits at the declaration and the indentation
        precedes it on the same line ("...\\n\\t\\t|public").
        For 'inside', start_byte sits at the start of the body line and the
        indentation follows it ("...def f():\\n|\\t\\t\\tstmt").
        """
        SPACE, TAB = 0x20, 0x09

        i = start_byte - 1
        indent = bytearray()
        while i >= 0 and source[i] in (SPACE, TAB):
            indent.append(source[i])
            i -= 1
        indent.reverse()
        return bytes(indent).decode('utf-8')

    def _indent_docstring(self, docstring: str, indentation: str, placement: str) -> str:
        """Apply `indentation` to a freshly rendered (un-indented) docstring
        according to the insertion strategy."""
        body = docstring[:-1] if docstring.endswith('\n') else docstring
        tail = '\n' if docstring.endswith('\n') else ''
        return indentation + body.replace('\n', '\n' + indentation) + tail
