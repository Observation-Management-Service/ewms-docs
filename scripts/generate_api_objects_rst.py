"""Generate a Sphinx RST reference page from an OpenAPI spec's components.schemas objects."""

import argparse
import json
import pathlib
import textwrap


def _ref_name(schema: dict) -> str | None:
    """Return the schema name from a $ref pointer, or None if not a $ref."""
    ref = schema.get("$ref", "")
    return ref.split("/")[-1] if ref else None


def _resolve_type(schema: dict) -> str:
    """Return a human-readable type string for a schema.

    Returns the $ref name (e.g. 'MQProfileObject') when present, so callers
    get a meaningful type label rather than a bare 'object'.
    """
    if ref := _ref_name(schema):
        return f"`{ref}`"
    ptype = schema.get("type", "")
    if not ptype and "anyOf" in schema:
        ptype = " | ".join(s.get("type", "?") for s in schema["anyOf"])
    return ptype


def _prefix(depth: int) -> str:
    """Return the '> > ' prefix string for a given depth level."""
    return "> " * depth


def _expand_schema(
    pschema: dict,
    depth: int,
    rows: list[tuple[str, str, str]],
) -> None:
    """Expand a schema's children into rows, handling objects and arrays recursively.

    Mutates rows in place. $ref children are noted as 'See <Name>' and not expanded.
    """
    # Nested object with known properties
    nested_props = pschema.get("properties", {})
    if nested_props:
        _collect_rows(nested_props, depth=depth + 1, rows=rows)
        return

    # Free-form object (additionalProperties, no fixed properties)
    if pschema.get("type") == "object" and "additionalProperties" in pschema:
        addl = pschema["additionalProperties"]
        value_type = _resolve_type(addl) if isinstance(addl, dict) else ""
        rows.append(
            (
                f"{_prefix(depth + 1)}*(any key)*",
                value_type,
                "Additional properties.",
            )
        )
        return

    # Array — show items as a [] child, then recurse into items
    if pschema.get("type") == "array":
        items = pschema.get("items", {})
        items_type = _resolve_type(items)
        items_type_display = f"{items_type}(s)" if items_type else ""
        items_desc = items.get("description", "")
        if ref := _ref_name(items):
            items_desc = f"See ``{ref}``."
        rows.append(
            (
                f"{_prefix(depth + 1)}``[]``",
                items_type_display,
                items_desc,
            )
        )
        # Only recurse into items if they are inline (not a $ref)
        if not _ref_name(items):
            _expand_schema(items, depth + 1, rows)


def _collect_rows(
    props: dict,
    depth: int = 0,
    rows: list[tuple[str, str, str]] | None = None,
) -> list[tuple[str, str, str]]:
    """Recursively collect (field, type, description) rows for a properties dict.

    Depth is indicated by '> ' prefixes: depth 1 = '> field', depth 2 = '> > field', etc.
    $ref fields are noted as 'See <Name>' rather than expanded inline.
    """
    if rows is None:
        rows = []

    for pname, pschema in props.items():
        ptype = _resolve_type(pschema)
        pdesc = pschema.get("description", "")

        if ref := _ref_name(pschema):
            # Append "See <Name>" to whatever description the property has
            see = f"See ``{ref}``."
            pdesc = f"{pdesc} {see}" if pdesc else see
        elif enum := pschema.get("enum"):
            enum_str = ", ".join(f"``{v}``" for v in enum)
            pdesc = f"{pdesc} One of: {enum_str}." if pdesc else f"One of: {enum_str}."

        rows.append((f"{_prefix(depth)}``{pname}``", ptype, pdesc))

        # Don't recurse into $ref fields — they're documented as their own schema
        if not _ref_name(pschema):
            _expand_schema(pschema, depth, rows)

    return rows


def main() -> None:
    """Parse args and write the RST file."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "spec",
        type=pathlib.Path,
        help="Path to openapi.json",
    )
    parser.add_argument(
        "output",
        type=pathlib.Path,
        help="Path to output .rst file",
    )
    parser.add_argument(
        "--title",
        default="API Objects",
        help="Page title",
    )
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
