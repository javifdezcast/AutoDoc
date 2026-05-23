"""
TypeScript code can be one of two types: object-oriented or functional.
The first type has the following structure that should be documented:
    - Classes: only public elements should be documented.
        + Fields (public_field_definition without 'private'/'protected'/'#')
        + Methods (method_definition) <--> functions
    - Interfaces (TypeScript-specific): only public by definition.
        + Property signatures
        + Method signatures
Functional / module-level code has the following structure:
    - Program (TS calls the root node 'program', not 'module')
        + Variables (lexical_declaration for const/let; variable_declaration for var)
        + Functions (function_declaration)

This module builds the skeletons for each element that we want to document.
The TSDoc format intentionally omits type information from @param/@returns
because TypeScript already encodes types in the source code itself, so we
only collect names and descriptions for parameters (unlike the Python builder
which carries a 'type' field).
"""
from typing import override
from tree_sitter import Node
from builders.skeleton_builder import SkeletonBuilder


class TypeScriptSkeletonBuilder(SkeletonBuilder):

    # ------------------------------------------------------------------ #
    #  Public dispatcher                                                 #
    # ------------------------------------------------------------------ #

    @override
    def build_skeleton(cls, node: Node) -> dict | None:
        """
        Dispatch to the right skeleton builder based on the node type.

        Parameters
        ----------
        node : Node
            A Tree-sitter node of type 'program', 'class_declaration',
            'interface_declaration', 'function_declaration', or
            'method_definition'.

        Returns
        -------
        dict or None
            A dictionary skeleton ready to be filled by the LLM, or None
            if the node type is not handled.
        """
        if node.type == "class_declaration":
            return cls._build_class_skeleton(node)
        elif node.type == "interface_declaration":
            return cls._build_interface_skeleton(node)
        elif node.type in ("function_declaration", "method_definition"):
            return cls._build_function_skeleton(node)
        elif node.type == "program":
            return cls._build_module_skeleton(node)
        return None

    # ------------------------------------------------------------------ #
    #  Skeleton builders                                                 #
    # ------------------------------------------------------------------ #

    def _build_module_skeleton(self, node: Node) -> dict:
        """
        Build the documentation skeleton for a TypeScript file (program node).

        Collects every top-level variable declaration that is not part of an
        import/export-from statement. Both `const`/`let` (lexical_declaration)
        and `var` (variable_declaration) are considered.

        Parameters
        ----------
        node : Node
            A Tree-sitter node of type 'program'.

        Returns
        -------
        dict
            Skeleton with a 'description' key and, when present, a
            'variables' key containing one entry per module-level variable.
        """
        skeleton: dict = {"description": "<placeholder>"}

        # Module-level variables live inside lexical_declaration (const/let)
        # or variable_declaration (var) nodes. They may be wrapped by
        # `export_statement`, so we unwrap one level if needed.
        variable_nodes: list[Node] = []
        for child in node.named_children:
            target = child
            if child.type == "export_statement":
                # export_statement has a 'declaration' field for re-exporting decls
                inner = child.child_by_field_name("declaration")
                if inner is None:
                    continue
                target = inner

            if target.type in ("lexical_declaration", "variable_declaration"):
                # A declaration can contain several variable_declarators
                for declarator in target.named_children:
                    if declarator.type == "variable_declarator":
                        variable_nodes.append(declarator)

        if variable_nodes:
            self._add_attribute_elements(variable_nodes, skeleton)

        return skeleton

    def _build_class_skeleton(self, node: Node) -> dict:
        """
        Build the documentation skeleton for a TypeScript class.

        Only public fields are included. A field is considered public when
        it has no accessibility modifier or an explicit `public` modifier,
        is not declared with a `#` private-name, and is not a `private_field_definition`.

        Parameters
        ----------
        node : Node
            A Tree-sitter node of type 'class_declaration'.

        Returns
        -------
        dict
            Skeleton with 'description' and, optionally, an 'attributes' key.
        """
        skeleton: dict = {"description": "<placeholder>"}

        body = node.child_by_field_name("body")
        if body is not None:
            field_nodes: list[Node] = []

            for item in body.named_children:
                # Members of class_body include:
                #   public_field_definition, method_definition,
                #   abstract_method_signature, etc.
                # Tree-sitter-typescript exposes public_field_definition
                # for every field; visibility modifiers (`private`,
                # `protected`) appear as anonymous children.
                if item.type == "public_field_definition":
                    if self._is_public_member(item):
                        field_nodes.append(item)

            if field_nodes:
                self._add_attribute_elements(field_nodes, skeleton, key="attributes")

        return skeleton

    def _build_interface_skeleton(self, node: Node) -> dict:
        """
        Build the documentation skeleton for a TypeScript interface.

        Interfaces only contain public members by definition, so every
        property signature is documented.

        Parameters
        ----------
        node : Node
            A Tree-sitter node of type 'interface_declaration'.

        Returns
        -------
        dict
            Skeleton with 'description' and, optionally, an 'attributes' key.
        """
        skeleton: dict = {"description": "<placeholder>"}

        body = node.child_by_field_name("body")
        if body is not None:
            field_nodes: list[Node] = [
                item for item in body.named_children
                if item.type == "property_signature"
            ]
            if field_nodes:
                self._add_attribute_elements(field_nodes, skeleton, key="attributes")

        return skeleton

    def _build_function_skeleton(self, node: Node) -> dict:
        """
        Build the skeleton for a single function or method node.

        TSDoc does not put type information in @param / @returns because the
        types are already in the source. We therefore only collect parameter
        names and descriptions; the 'returns' section is included whenever
        the declared return type is not `void` or `undefined`.

        Parameters
        ----------
        node : Node
            A Tree-sitter node of type 'function_declaration' or
            'method_definition'.

        Returns
        -------
        dict
            Dictionary with 'name', 'kind', 'description', and optionally
            'args', 'returns', and 'example'.
        """
        name_node = node.child_by_field_name("name")
        return_type_node = node.child_by_field_name("return_type")
        params_node = node.child_by_field_name("parameters")

        skeleton: dict = {
            "name":        name_node.text.decode() if name_node else "<placeholder>",
            "kind":        "method" if node.type == "method_definition" else "function",
            "description": "<placeholder>",
        }

        # ── parameters ───────────────────────────────────────────────────
        params = self._extract_parameters(params_node)
        if params:
            skeleton["args"] = params

        # ── return type ──────────────────────────────────────────────────
        # `return_type` is a 'type_annotation' node whose text starts with
        # ':' (e.g. ': number'). Skip void/undefined returns.
        if return_type_node is not None:
            raw = return_type_node.text.decode().lstrip(":").strip()
            if raw not in ("void", "undefined", "never"):
                skeleton["returns"] = {"description": "<placeholder>"}

        skeleton["example"] = "<placeholder>"
        return skeleton

    # ------------------------------------------------------------------ #
    #  Private helpers                                                   #
    # ------------------------------------------------------------------ #

    def _extract_parameters(self, params_node: Node | None) -> list[dict]:
        """
        Extract parameters from a 'formal_parameters' node.

        Tree-sitter-typescript wraps every parameter in either a
        'required_parameter' or an 'optional_parameter' node. We do not
        store type information in the skeleton because TSDoc deliberately
        omits it from @param tags (the type is already in the source code).

        Parameters
        ----------
        params_node : Node or None
            The Tree-sitter 'formal_parameters' node, or None.

        Returns
        -------
        list of dict
            Each entry has 'name' and 'description' keys.
        """
        params: list[dict] = []
        if params_node is None:
            return params

        for param in params_node.named_children:
            if param.type not in ("required_parameter", "optional_parameter"):
                continue

            pattern_node = param.child_by_field_name("pattern")
            if pattern_node is None:
                continue

            # The pattern can be a plain identifier, a rest_pattern
            # (e.g. ...args), an object_pattern, or an array_pattern.
            # For destructuring patterns we use their raw text as the
            # name so the LLM has enough context to describe them.
            if pattern_node.type == "rest_pattern":
                # Strip the leading '...' from the textual representation
                name_text = pattern_node.text.decode().lstrip(".")
            else:
                name_text = pattern_node.text.decode()

            params.append({
                "name":        name_text,
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
        Append variable / field / property entries to *skeleton* under *key*.

        Each node is expected to be one of:
            - variable_declarator         (module-level variables)
            - public_field_definition     (class fields)
            - property_signature          (interface properties)

        TypeScript already carries the type on the declaration itself; we
        keep a 'type' key in the skeleton because — unlike for @param —
        types ARE useful when describing standalone module variables and
        class/interface members (rendered as plain Markdown, not as a
        TSDoc tag).

        Parameters
        ----------
        nodes : list of Node
            Tree-sitter nodes to process.
        skeleton : dict
            The skeleton dictionary to mutate in place.
        key : str
            The key under which the list will be stored ('variables' for
            module-level declarations, 'attributes' for class fields and
            interface properties).
        """
        entries: list[dict] = []
        for n in nodes:
            name_node = n.child_by_field_name("name")
            type_node = n.child_by_field_name("type")  # optional type_annotation

            type_text = "<placeholder>"
            if type_node is not None:
                # 'type_annotation' text looks like ': number' — strip the colon
                type_text = type_node.text.decode().lstrip(":").strip()

            entries.append({
                "name":        name_node.text.decode() if name_node else "<placeholder>",
                "type":        type_text,
                "description": "<placeholder>",
            })
        skeleton[key] = entries

    @staticmethod
    def _is_public_member(node: Node) -> bool:
        """
        Determine whether a class member should be documented.

        A member is considered private (and thus skipped) when:
            - it carries an explicit 'private' or 'protected' accessibility
              modifier, or
            - its name starts with '#' (ECMAScript private field syntax).

        Parameters
        ----------
        node : Node
            A Tree-sitter node for a class member (typically
            public_field_definition).

        Returns
        -------
        bool
            True if the member is public.
        """
        # Accessibility modifiers ('public', 'private', 'protected') appear
        # as direct anonymous children in tree-sitter-typescript.
        for child in node.children:
            if child.type == "accessibility_modifier":
                if child.text.decode() in ("private", "protected"):
                    return False

        name_node = node.child_by_field_name("name")
        if name_node is not None:
            name_text = name_node.text.decode()
            if name_text.startswith("#"):
                return False

        return True