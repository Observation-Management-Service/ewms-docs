"""Generate a Sphinx RST reference page from an OpenAPI spec's components.schemas objects."""

import argparse
import json
import pathlib
import re


# Matches bare URLs (https://...)
# in spec descriptions, converting them to RST anonymous hyperlinks.
# Match URLs, stopping before trailing punctuation (. , ) that ends a sentence)
def _linkify(text: str) -> str:
    """Strip backticks around URLs — Sphinx auto-links bare https:// URLs."""
    return re.sub(r"`(https?://[^`\s]+)`", r"\1", text)


def _ref_name(schema: dict) -> str | None:
    """Return the schema name from a $ref pointer, or None if not a $ref."""
    ref = schema.get("$ref", "")
    return ref.split("/")[-1] if ref else None


def _ref_link(schema: dict) -> str | None:
    """Return a human-readable 'See X_.' string for a $ref, or None if not a $ref.

    Handles both top-level refs (#/components/schemas/Foo) and deep refs
    (#/components/schemas/Foo/properties/bar), linking to the top-level schema
    in both cases. For deep refs, appends '(field)' to hint that the link
    target is a sub-field — the Type column carries the actual dotted path.
    """
    ref = schema.get("$ref", "")
    if not ref:
        return None
    # e.g. ['components', 'schemas', 'SchemaName'] or
    #      ['components', 'schemas', 'SchemaName', 'properties', 'fieldName']
    parts = ref.lstrip("#/").split("/")
    # Need at least components/schemas/Name to be a valid ref
    if len(parts) < 3:
        return None
    schema_name = parts[2]
    # Exactly 3 parts = top-level schema ref
    if len(parts) == 3:
        return f"See `{schema_name}`_."
    # Deep ref — Type column already shows the dotted path; just hint at field-ness
    return f"See field in `{schema_name}`_."


def _clean_pointer_parts(parts: list[str]) -> list[str]:
    """Drop JSON Pointer structural separators so a deep ref path reads like field access.

    Composition keywords (oneOf/anyOf/allOf/prefixItems/patternProperties) are
    followed by an index/key that's also structural, so drop both.
    """
    # JSON Pointer parts that are structural and should be dropped on their own
    drop_alone = {"properties", "items", "additionalProperties", "not"}
    # JSON Pointer parts where the keyword AND the following part are both structural
    drop_with_next = {"oneOf", "anyOf", "allOf", "prefixItems", "patternProperties"}

    cleaned: list[str] = []
    i = 0
    while i < len(parts):
        p = parts[i]
        if p in drop_alone:
            i += 1
        elif p in drop_with_next:
            # skip the keyword + the following index/key
            i += 2
        else:
            cleaned.append(p)
            i += 1
    return cleaned


def _resolve_type_human(schema: dict) -> str:
    """Return a human-readable type string for a schema.

    - top-level $ref  -> ``RefName``
    - deep $ref       -> ``Schema.field`` (dotted path)
    - array           -> 'array of X' where X is the items type
                         (X is parenthesized if it contains '|')
    - anyOf/oneOf     -> 'X | Y' (pipe-separated)
    - multi-type      -> 'string | null' (OpenAPI 3.1 'type' array)
    - plain type      -> 'string', 'integer', etc.
    """
    ref = schema.get("$ref", "")
    if ref:
        # e.g. ['components', 'schemas', 'SchemaName', ...]
        parts = ref.lstrip("#/").split("/")
        # Exactly 3 parts = top-level schema ref with a usable name
        if len(parts) == 3:
            name = parts[2]
            return f"``{name}``"
        else:
            # Deep ref (e.g. #/components/schemas/Foo/properties/bar) — render
            # as 'Foo.bar' dotted path, dropping JSON Pointer structural noise.
            schema_name = parts[2]
            cleaned = _clean_pointer_parts(parts[3:])
            if cleaned:
                full = f"{schema_name}." + ".".join(cleaned)
            else:
                full = schema_name
            return f"``{full}``"
    ptype = schema.get("type", "")
    # OpenAPI 3.1 multi-type: type: ["string", "null"] -> "string | null"
    if isinstance(ptype, list):
        return " | ".join(ptype)
    if ptype == "array":
        items = schema.get("items", {})
        items_type = _resolve_type_human(items)
        if not items_type:
            return "array"
        # Bracket compound item types so union scope is unambiguous
        # ("array of (string | null)" not "array of string | null")
        if " | " in items_type:
            items_type = f"({items_type})"
        return f"array of {items_type}"
    # anyOf/oneOf union — recurse so $refs and multi-types render properly
    variants = schema.get("anyOf") or schema.get("oneOf")
    if not ptype and variants:
        return " | ".join(_resolve_type_human(v) for v in variants)
    return ptype


def _prefix(depth: int) -> str:
    """Return the '> > ' depth prefix for a given nesting level."""
    return "> " * depth


def _expand_schema(
    pschema: dict,
    depth: int,
    rows: list[tuple[str, str, str]],
) -> None:
    """Expand a schema's children into rows, handling objects and arrays recursively.

    Mutates rows in place. $ref children are noted as 'See <n>_' and not expanded.
    Arrays do not emit a [] row — the type column on the parent says 'array of X(s)'
    and children of object items are prefixed with [*]. to signal per-item fields.
    """
    # Nested object with known properties
    if nested_props := pschema.get("properties", {}):
        _collect_rows(nested_props, depth=depth + 1, rows=rows)
        return

    # Free-form object (additionalProperties, no fixed properties)
    if pschema.get("type") == "object" and "additionalProperties" in pschema:
        addl = pschema["additionalProperties"]
        value_type = _resolve_type_human(addl) if isinstance(addl, dict) else ""
        rows.append(
            (
                f"{_prefix(depth + 1)}*(any key)*",
                value_type,
                "",
            )
        )
        return

    # Array — no [] row; recurse into items with [*]. field prefix if object
    if pschema.get("type") == "array":
        items = pschema.get("items", {})
        if _ref_link(items):
            return  # type column already says "array of RefName(s)", nothing to expand
        if item_props := items.get("properties", {}):
            _collect_rows(item_props, depth=depth + 1, rows=rows, field_prefix="[*].")
        elif items.get("type") == "array":
            # Array of arrays — recurse
            _expand_schema(items, depth, rows)
        # Note: no branch for array-of-free-form-objects (items.type == "object"
        # with additionalProperties but no properties). The type column already
        # says "array of object(s)" which is sufficient — there are no known
        # sub-fields to expand.


def _collect_rows(
    props: dict,
    depth: int = 0,
    rows: list[tuple[str, str, str]] | None = None,
    field_prefix: str = "",
) -> list[tuple[str, str, str]]:
    """Recursively collect (field, type, description) rows for a properties dict.

    Depth is shown via '> ' prefixes. field_prefix is prepended to field names —
    '[*].' when expanding array item properties to signal per-item fields.
    """
    if rows is None:
        rows = []

    for pname, pschema in props.items():
        ptype = _resolve_type_human(pschema)
        pdesc = _linkify(pschema.get("description", ""))

        if link := _ref_link(pschema):
            pdesc = f"{pdesc} {link}" if pdesc else link
        elif pschema.get("type") == "array" and (
            ilink := _ref_link(pschema.get("items", {}))
        ):
            # Array whose items are a $ref — append See link on the parent row
            pdesc = f"{pdesc} {ilink}" if pdesc else ilink
        elif enum := pschema.get("enum"):
            # Show enum values one per line using RST line blocks (| prefix).
            # Continuation lines need 7 spaces to align under the opening |.
            sep = "\n" + " " * 7 + "| "
            ptype = "| " + sep.join(f'``"{v}"``' for v in enum)

        rows.append((f"{_prefix(depth)}``{field_prefix}{pname}``", ptype, pdesc))

        # Don't recurse into $ref fields — they're documented as their own schema
        if not _ref_link(pschema):
            _expand_schema(pschema, depth, rows)

    return rows


def _operations_using_schema(spec: dict) -> dict[str, list[tuple[str, str, str]]]:
    """Build a reverse map {schema_name: [(METHOD, path, role), ...]} from the spec.

    Walks each operation's request side (parameters + requestBody) and response side
    (responses) separately so each occurrence can be labeled. Path-level parameters
    are folded into the request side for every method on that path. Role is one of
    'request', 'response', or 'request & response' (when a schema appears on both
    sides of a single operation).

    Only TOP-LEVEL $refs (e.g. '#/components/schemas/Manifest') count as a use.
    Deep refs into a sub-field (e.g. '.../Manifest/properties/scan_id') are ignored
    — they borrow a field definition, not the whole object.
    """

    def find_refs(node: object) -> set[str]:
        """Recursively collect every top-level component schema referenced under node.

        Deep refs (>3 parts) are intentionally skipped — see parent docstring.
        """
        refs: set[str] = set()
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "$ref" and isinstance(v, str):
                    # parts looks like ['components', 'schemas', 'Name']
                    parts = v.lstrip("#/").split("/")
                    # Exactly 3 parts = top-level component schema ref
                    if (
                        len(parts) == 3
                        and parts[0] == "components"
                        and parts[1] == "schemas"
                    ):
                        refs.add(parts[2])
                else:
                    refs |= find_refs(v)
        elif isinstance(node, list):
            for x in node:
                refs |= find_refs(x)
        return refs

    result: dict[str, list[tuple[str, str, str]]] = {}
    for path, item in spec.get("paths", {}).items():
        # Path-level parameters apply to every method on this path
        path_param_refs = find_refs(item.get("parameters", []))
        for method in ("get", "post", "put", "delete", "patch"):
            if method not in item:
                continue
            op = item[method]
            # Request side = requestBody + op-level parameters + path-level parameters
            req_refs = (
                find_refs(op.get("requestBody", {}))
                | find_refs(op.get("parameters", []))
                | path_param_refs
            )
            # Response side = responses
            resp_refs = find_refs(op.get("responses", {}))

            # Each schema gets one entry per (method, path), role tells you which side
            for schema in req_refs | resp_refs:
                in_req = schema in req_refs
                in_resp = schema in resp_refs
                if in_req and in_resp:
                    role = "request & response"
                elif in_req:
                    role = "request"
                else:
                    role = "response"
                # spec-order is preserved via dict insertion order
                result.setdefault(schema, []).append((method.upper(), path, role))

    return result


def _endpoint_anchor(method: str, path: str) -> str:
    """Build a sphinxcontrib-openapi-style anchor: 'post--scans-find'.

    Method is lowercased; path slashes become dashes; curly braces are stripped.
    """
    # strip leading slash, replace path separators with dashes, drop curly braces
    slug = path.lstrip("/").replace("/", "-").replace("{", "").replace("}", "")
    return f"{method.lower()}--{slug}"


def main() -> None:
    """Parse args and write the RST file."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=pathlib.Path, help="Path to openapi.json")
    parser.add_argument("output", type=pathlib.Path, help="Path to output .rst file")
    parser.add_argument("--title", default="API Objects", help="Page title")
    parser.add_argument(
        "--include",
        action="append",
        help="RST directives to include. Ex: '../foo.rst' -> '.. include:: ../foo.rst'",
    )
    parser.add_argument(
        "--endpoints-url",
        help="URL or relative path to the API page; each schema then gets a "
        "bulleted list of operations that use it. Ex: '../skydriver.html' for "
        "a relative link from a sibling _generated/ dir, or a full https:// URL.",
    )
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text())
    schemas = spec.get("components", {}).get("schemas", {})
    # Reverse-map (schema -> list of endpoints with role) once; empty if flag off
    ops_by_schema = _operations_using_schema(spec) if args.endpoints_url else {}

    lines = []
    for include in args.include or []:
        lines.extend([f".. include:: {include}", ""])
    lines.extend([args.title, "=" * len(args.title), ""])

    for name, schema in schemas.items():
        lines.append(name)
        lines.append("-" * len(name))
        if desc := schema.get("description"):
            lines.append(_linkify(desc))
        lines.append("")
        # Bulleted list of endpoints that reference this schema (skipped if empty).
        # Label gives context; bold method makes scanning verbs at a glance easy;
        # italic role at the end indicates request vs response side.
        if ops := ops_by_schema.get(name):
            lines.append("**Used by:**")
            lines.append("")
            for method, path, role in ops:
                url = f"{args.endpoints_url}#{_endpoint_anchor(method, path)}"
                lines.append(f"- **{method}** `{path} <{url}>`__ — *{role}*")
            lines.append("")
        props = schema.get("properties", {})
        if props:
            rows = _collect_rows(props)
            lines.append(".. list-table::")
            lines.append("   :header-rows: 1")
            lines.append("   :widths: 30 40 30")
            lines.append("")
            lines.append("   * - Field")
            lines.append("     - Type")
            lines.append("     - Description")
            for field, ftype, fdesc in rows:
                lines.append(f"   * - {field}")
                lines.append(f"     - {ftype}")
                lines.append(f"     - {fdesc}")
        lines.append("")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
