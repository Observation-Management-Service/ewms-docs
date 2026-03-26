"""Generate a Sphinx RST reference page from an OpenAPI spec's components.schemas objects."""

import argparse
import json
import pathlib
import textwrap


def _ref_name(schema: dict) -> str | None:
    """Return the schema name from a $ref pointer, or None if not a $ref."""
    ref = schema.get("$ref", "")
    return ref.split("/")[-1] if ref else None


def _resolve_type_human(schema: dict, plural: bool = False) -> str:
    """Return a human-readable type string for a schema.

    - $ref       -> ``RefName`` (or ``RefName(s)`` if plural)
    - array      -> 'array of X(s)' where X is the items type
    - anyOf      -> 'type1 | type2'
    - plain type -> 'string', 'integer', etc.
    """
    if ref := _ref_name(schema):
        return f"``{ref}(s)``" if plural else f"``{ref}``"
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

    Mutates rows in place. $ref children are noted as 'See <Name>_' and not expanded.
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
        if _ref_name(items):
            return  # type column already says "array of RefName(s)", nothing to expand
        if item_props := items.get("properties", {}):
            _collect_rows(item_props, depth=depth + 1, rows=rows, field_prefix="[*].")
        elif items.get("type") == "array":
            # Array of arrays — recurse
            _expand_schema(items, depth, rows)
        elif items.get("type") == "object" and "additionalProperties" in items:
            addl = items["additionalProperties"]
            value_type = _resolve_type_human(addl) if isinstance(addl, dict) else ""
            rows.append(
                (
                    f"{_prefix(depth + 1)}*(any key)*",
                    value_type,
                    "",
                )
            )


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
        pdesc = pschema.get("description", "")

        if ref := _ref_name(pschema):
            see = f"See `{ref}`_."
            pdesc = f"{pdesc} {see}" if pdesc else see
        elif enum := pschema.get("enum"):
            enum_str = ", ".join(f"``{v}``" for v in enum)
            pdesc = f"{pdesc} One of: {enum_str}." if pdesc else f"One of: {enum_str}."

        rows.append((f"{_prefix(depth)}``{field_prefix}{pname}``", ptype, pdesc))

        # Don't recurse into $ref fields — they're documented as their own schema
        if not _ref_name(pschema):
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
            lines.append(textwrap.fill(desc, 80))
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
