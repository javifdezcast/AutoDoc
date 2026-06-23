import datetime
import json
from pathlib import Path
import requests
from jinja2 import Template
from tree_sitter import Node, Parser, Query, QueryCursor, Language
from tree_sitter_language_pack import get_language

from builders import Builder
from builders import Skeletoniser
from languages import languages, LanguageConfig


class Documenter:

    _language: Language = None
    _language_config: LanguageConfig = None
    _parser: Parser = None
    _builder: Builder = None
    _skeletoniser: Skeletoniser = None
    _docstring_queries: Query = None
    _template_dir: str
    _example_dir: str
    _node_types: dict[str, str]
    _mode: str
    _root_dir: Path
    _url: str
    _model: str
    _temperature: float


    def __init__(self, general_config: dict):
        try:
            self._collected_docs = []
            self._builder = Builder()
            self._set_general_config_attributes(general_config)
            self._parser = Parser(self._language)
            self._set_language_config_attributes()
            self._set_mixed_config_attributes(general_config, languages[self._language_name])
        except KeyError:
            raise Exception(f'Language not supported')

    def _set_general_config_attributes(self, config: dict):
        self._language_name = config['language']
        self._language = get_language(self._language_name)
        self._url = config['llm']['base_url']
        self._model = config['llm']['model']
        self._temperature = config['llm']['temperature']
        self._mode = config['mode']
        self._root_dir = config['root_dir']


    def _set_language_config_attributes(self):
        language_config = languages[self._language_name]
        self._template_dir = language_config.template_directory
        self._example_dir = language_config.example_directory
        self._insertion = language_config.insertion
        self._skeletoniser = language_config.skeletoniser
        self.docstring_queries = [Query(self._language, query) for query in language_config.queries]

    def _set_mixed_config_attributes(self, general_config: dict, language_config: LanguageConfig):
        user_defined_node_types = general_config['elements_to_document']
        self._node_types = {k:v for k,v in language_config.node_types.items() if k in user_defined_node_types}


    def document_file(self, number, path: Path) -> None:
        self.file = number
        self.element_count = 0
        self.path = path
        source = path.read_bytes()
        tree = self._parser.parse(source)
        stripped_file = self._strip_docstrings(source, tree.root_node)
        tree = self._parser.parse(stripped_file)
        self._collected_docs = []
        self._document(tree.root_node, stripped_file, path)
        documented_file = self._insert_docs(stripped_file)
        self._save_file(documented_file, path)

    def _save_file(self, documented_file: bytes, path: Path):
        if self._mode == 'clone':
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
        relative_path = path.relative_to(Path(self._root_dir).parent)
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

    def _document(self, node: Node, file: bytes, path: Path) -> None:
        """Recurse into named children first, then document the current node."""
        for child in node.named_children:  # skip anonymous tokens
            self._document(child, file, path)
        if node.type in self._node_types:
            self._generate_and_collect(node, file, path)


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

    def _generate_and_collect(self, node: Node, file: bytes, path: Path) -> None:
        self.element_count += 1
        node_name = ''
        if node.child_by_field_name('name'):
            node_name = node.child_by_field_name('name').text.decode('utf-8')

        template = Template(Builder.build(self._template_dir, self._node_types , node))
        example = Builder.build(self._example_dir, self._node_types , node)

        insertion_point = self._find_insertion_point(node, self._insertion)
        tabulation = self._find_indentation(insertion_point, file)
        skeleton = self._skeletoniser.build_skeleton(node)
        prompt = self._build_prompt(node, skeleton, example)

        time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"{time}\t {self.file}.{self.element_count}: {node_name}. Prompt: {len(prompt)}")
        ini = datetime.datetime.now()

        response = self._query_model(prompt)

        time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"{time}\t {self.file}.{self.element_count}: {node_name}. Query time: {(datetime.datetime.now() - ini).total_seconds()}")

        docstring = template.render(json.loads(response)) + "\n"
        self.insert_to_results(docstring, path, node_name)
        self._collected_docs.append((insertion_point, docstring, tabulation))

    def _query_model(self, prompt: str) -> str:
        resp = requests.post(
            self._url.rstrip("/") + "/api/generate",
            json={
                "model": self._model,
                "prompt": prompt,
                "think": False,
                "stream": False,
                "format": "json",
                "options": {"temperature": self._temperature}},
            timeout=600,
        )
        resp.raise_for_status()
        return resp.json()["response"]

    def _build_prompt(self, node: Node, skeleton: dict, example: str) -> str:
        return (
            f"You are an expert software engineer writing API documentation (docstrings) "
            f"for {self._language_name} code.\n\n"
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
            f"```{self._language}\n{node.text.decode("utf-8")}\n```\n\n"
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

    def _find_indentation(self, start_byte: int, source: bytes) -> str:
        """Return the indentation (run of spaces/tabs) of the line the
        insertion point lives on.

        For 'before', start_byte sits at the declaration and the indentation
        precedes it on the same line ("...\\n\\t\\t|public").
        For 'inside', start_byte sits at the start of the body line and the
        indentation follows it ("...def f():\\n|\\t\\t\\tstmt").
        """
        space, tab = 0x20, 0x09

        i = start_byte - 1
        indent = bytearray()
        while i >= 0 and source[i] in (space, tab):
            indent.append(source[i])
            i -= 1
        indent.reverse()
        return bytes(indent).decode('utf-8')

    def _indent_docstring(self, docstring: str, indentation: str) -> str:
        """Apply `indentation` to a freshly rendered (un-indented) docstring
        according to the insertion strategy."""
        body = docstring[:-1] if docstring.endswith('\n') else docstring
        tail = '\n' if docstring.endswith('\n') else ''
        return indentation + body.replace('\n', '\n' + indentation) + tail

    def insert_to_results(self, docstring: str, path: Path, node: str):
        file = self._language_name + "_docstrings.json"
        with open(file, "a") as f:
            file = self._language_name + "_docstrings.json"

            entry_obj = {
                "path": f"{path.absolute()}.{node}",
                "docstring": docstring
            }

            with open(file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry_obj, ensure_ascii=False) + ",\n")
