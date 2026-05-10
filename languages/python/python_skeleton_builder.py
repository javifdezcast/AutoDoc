"""
Python code can be one of two types: object-oriented or functional.
The first type has the following structure that should be documented:
    - Classes: only public elements should be documented.
        + Fields
        + Instance Methods <--> functions
        - Static variables <--> variables
        - Class methods <--> functions
Functional code has the following structure:
    - Module
        + Variables
        + Functions

We must then define the skeletons for each of the elements that we want
to document.

This module accesses the files containing the skeletons and returns them as
Template objects.
"""
from typing import override
from tree_sitter import Node
from builders.skeleton_builder import SkeletonBuilder

class PythonSkeletonBuilder (SkeletonBuilder):


    # ------------------------------------------------------------------ #
    #  Public dispatcher                                                   #
    # ------------------------------------------------------------------ #

    @override
    def build_skeleton(cls, node: Node) -> dict | None:
        """
        Dispatch to the right skeleton builder based on the node type.

        Parameters
        ----------
        node : Node
            A Tree-sitter node of type 'module', 'function_definition',
            or 'class_definition'.

        Returns
        -------
        dict or None
            A dictionary skeleton ready to be filled by the LLM, or None
            if the node type is not handled.
        """
        if node.type == "class_definition":
            return cls._build_class_skeleton(node)
        elif node.type == "function_definition":
            return cls._build_function_skeleton(node)
        elif node.type == "module":
            return cls._build_module_skeleton(node)
        return None

    # ------------------------------------------------------------------ #
    #  Skeleton builders                                                   #
    # ------------------------------------------------------------------ #

    def _build_module_skeleton(self, node: Node) -> dict:
        """
        Build the documentation skeleton for a module node.

        Collects every module-level assignment (plain or type-annotated)
        that is not an import.

        Parameters
        ----------
        node : Node
            A Tree-sitter node of type 'module'.

        Returns
        -------
        dict
            Skeleton with a 'description' key and, when present, a
            'variables' key containing one entry per module-level variable.
        """
        skeleton: dict = {"description": "<placeholder>"}

        # Module-level variables live inside expression_statement nodes
        # whose single named child is an 'assignment' node.
        variable_nodes = [
            child.named_children[0]          # the assignment node
            for child in node.named_children
            if child.type == "expression_statement"
            and len(child.named_children) == 1
            and child.named_children[0].type == "assignment"
        ]

        if variable_nodes:
            self._add_attribute_elements(variable_nodes, skeleton)

        return skeleton

    def _build_class_skeleton(self, node: Node) -> dict:
        """
        Build the documentation skeleton for a class node.

        Only public fields (those whose name does not start with '_')
        are included.

        Parameters
        ----------
        node : Node
            A Tree-sitter node of type 'class_definition'.

        Returns
        -------
        dict
            Skeleton with 'description' and, optionally, a 'fields' key.
        """
        skeleton: dict = {"description": "<placeholder>"}

        body = node.child_by_field_name("body")
        if body is not None:
            field_nodes: list[Node] = []

            for item in body.named_children:
                if (
                        item.type == "expression_statement"
                        and len(item.named_children) == 1
                        and item.named_children[0].type == "assignment"
                ):
                    assignment = item.named_children[0]
                    name_node = assignment.child_by_field_name("left")
                    if name_node and not name_node.text.decode().startswith("_"):
                        field_nodes.append(assignment)

            if field_nodes:
                self._add_attribute_elements(field_nodes, skeleton, key="fields")

        return skeleton

    def _build_function_skeleton(self, node: Node) -> dict:
        """
        Build the skeleton for a single function node.

        Parameters
        ----------
        node : Node
            A Tree-sitter node of type 'function_definition'.
        kind : str
            One of 'function', 'instance_method', 'static_method', or
            'class_method'. Used as metadata in the skeleton.

        Returns
        -------
        dict
            Dictionary with 'name', 'kind', 'description', and optionally
            'parameters' and 'returns'.
        """
        name_node = node.child_by_field_name("name")
        return_type_node = node.child_by_field_name("return_type")
        params_node = node.child_by_field_name("parameters")

        skeleton: dict = {
            "name":        name_node.text.decode() if name_node else "<placeholder>",
            "kind":        "function",
            "description": "<placeholder>",
        }

        # ── parameters ───────────────────────────────────────────────────
        params = self._extract_parameters(params_node, "function")
        if params:
            skeleton["parameters"] = params

        # ── return type ──────────────────────────────────────────────────
        skeleton["returns"] = {
            "type":        return_type_node.text.decode() if return_type_node else "<placeholder>",
            "description": "<placeholder>",
        }
        skeleton["example"] = "<placeholder>"
        return skeleton

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #


    def _extract_parameters(self, params_node: Node | None, kind: str) -> list[dict]:
        """
        Extract parameters from a 'parameters' node.

        'self' and 'cls' are automatically skipped for instance and class
        methods respectively.

        Parameters
        ----------
        params_node : Node or None
            The Tree-sitter 'parameters' node of the function, or None.
        kind : str
            Function kind used to skip implicit first parameters.

        Returns
        -------
        list of dict
            Each entry has 'name', 'type', and 'description' keys.
        """
        IMPLICIT_PARAMS = {"self", "cls"}
        params: list[dict] = []
        if params_node is not None:

            skip_first = kind in ("instance_method", "class_method")

            for i, param in enumerate(params_node.named_children):

                # Skip 'self' / 'cls'
                if param.type == "identifier" and param.text.decode() in {"self", "cls"}:
                    continue

                # *args / **kwargs — store the splat name without the stars
                if param.type in ("list_splat_pattern", "dictionary_splat_pattern"):
                    raw_text = param.text.decode().lstrip("*")
                    params.append({
                        "name":        raw_text,
                        "type":        "<placeholder>",
                        "description": "<placeholder>",
                    })

                # identifier  →  plain untyped parameter  (e.g. x)
                elif param.type == "identifier":
                    params.append({
                        "name":        param.text.decode(),
                        "type":        "<placeholder>",
                        "description": "<placeholder>",
                    })

                # typed_parameter  →  name: type  (e.g. a: int)
                elif param.type == "typed_parameter":
                    name_node = param.named_children[0]        # identifier is first
                    type_node = param.child_by_field_name("type")
                    params.append({
                        "name":        name_node.text.decode() if name_node else "<placeholder>",
                        "type":        type_node.text.decode() if type_node else "<placeholder>",
                        "description": "<placeholder>",
                    })

                # typed_default_parameter  →  name: type = default  (e.g. b: str = "x")
                elif param.type == "typed_default_parameter":
                    name_node = param.child_by_field_name("name")
                    type_node = param.child_by_field_name("type")
                    params.append({
                        "name":        name_node.text.decode() if name_node else "<placeholder>",
                        "type":        type_node.text.decode() if type_node else "<placeholder>",
                        "description": "<placeholder>",
                    })

                # default_parameter  →  name = default  (e.g. b = "x")
                elif param.type == "default_parameter":
                    name_node = param.child_by_field_name("name")
                    params.append({
                        "name":        name_node.text.decode() if name_node else "<placeholder>",
                        "type":        "<placeholder>",
                        "description": "<placeholder>",
                    })

        return params

    def _add_attribute_elements(
        self,
        nodes: list[Node],
        skeleton: dict,
        key: str = "variables",
    ) -> None:
        """
        Append variable/field entries to *skeleton* under *key*.

        Each *node* must be a Tree-sitter 'assignment' node so that the
        'left' (name) and optional 'type' fields can be read directly.

        Parameters
        ----------
        nodes : list of Node
            Tree-sitter 'assignment' nodes to process.
        skeleton : dict
            The skeleton dictionary to mutate in place.
        key : str
            The key under which the list will be stored ('variables' for
            modules, 'fields' for classes).
        """
        entries: list[dict] = []
        for assignment in nodes:
            name_node = assignment.child_by_field_name("left")
            type_node = assignment.child_by_field_name("type")  # present only for annotated assignments
            entries.append(
                {
                    "name":        name_node.text.decode() if name_node else "<placeholder>",
                    "type":        type_node.text.decode() if type_node else "<placeholder>",
                    "description": "<placeholder>",
                }
            )
        skeleton[key] = entries
