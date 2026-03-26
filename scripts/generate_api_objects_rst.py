"""Generate a Sphinx RST reference page from an OpenAPI spec's components.schemas objects."""

import argparse
import json
import pathlib
import re
import textwrap

# Matches bare URLs (https://...)
# in spec descriptions, converting them to RST anonymous hyperlinks.
# Match URLs, stopping before trailing punctuation (. , ) that ends a sentence)
_URL_RE = re.compile(r"(https?://[^\s`]+?)([.,)]?)(?=\s|$)")


def _linkify(text: str) -> str:
    """Convert any URLs in text to RST anonymous hyperlinks."""
    return _URL_RE.sub(r"`\1`__\2", text)


def _ref_name(schema: dict) -> str | None:
    """Return the schema name from a $ref pointer, or None if not a $ref."""
    ref = schema.get("$ref", "")
    return ref.split("/")[-1] if ref else None


def _ref_link(schema: dict) -> str | None:
    """Return a human-readable 'See X_.' string for a $ref, or None if not a $ref.

    Handles both top-level refs (#/components/schemas/Foo) and deep refs
    (#/components/schemas/Foo/properties/bar), linking to the top-level schema
    in both cases.
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
    # More than 3 parts = deep ref into a sub-field — link to the top-level schema
    # and note which field it points to
    field_name = parts[-1]
    return f"See `{schema_name}`_ (``{field_name}`` field)."


def _resolve_type_human(schema: dict, plural: bool = False) -> str:
    """Return a human-readable type string for a schema.

    - top-level $ref  -> ``RefName`` (or ``RefName(s)`` if plural)
    - deep $ref       -> object (the actual type isn't a named schema)
    - array           -> 'array of X(s)' where X is the items type
    - anyOf           -> 'type1 | type2'
    - plain type      -> 'string', 'integer', etc.
    """
    ref = schema.get("$ref", "")
    if ref:
        # e.g. ['components', 'schemas', 'SchemaName', ...]
        parts = ref.lstrip("#/").split("/")
        # Exactly 3 parts = top-level schema ref with a usable name
        if len(parts) == 3:
            name = parts[2]
            return f"``{name}(s)``" if plural else f"``{name}``"
        else:
            # Deep ref (e.g. #/components/schemas/Foo/properties/bar) — no clean
            # type name to show; fall back to 'object'
            return "object"
    ptype = schema.get("type", "")
    if ptype == "array":
        items = schema.get("items", {})
        items_type = _resolve_type_human(items, plural=True)
        return f"array of {items_type}" if items_type else "array"
    if not ptype and "anyOf" in schema:
        ptype = " | ".join(s.get("type", "?") for s in schema["anyOf"])
    return f"{ptype}(s)" if (plural and ptype) else ptype


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


def main() -> None:
    """Parse args and write the RST file."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=pathlib.Path, help="Path to openapi.json")
    parser.add_argument("output", type=pathlib.Path, help="Path to output .rst file")
    parser.add_argument("--title", default="API Objects", help="Page title")
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text())
    schemas = spec.get("components", {}).get("schemas", {})

    lines = [args.title, "=" * len(args.title), ""]

    for name, schema in schemas.items():
        lines.append(name)
        lines.append("-" * len(name))
        if desc := schema.get("description"):
            lines.append(_linkify(desc))
        lines.append("")
        props = schema.get("properties", {})
        if props:
            rows = _collect_rows(props)
            lines.append(".. list-table::")
            lines.append("   :header-rows: 1")
            lines.append("   :widths: 35 15 50")
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
