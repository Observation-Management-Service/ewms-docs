"""Generate a Sphinx RST reference page from an OpenAPI spec's components.schemas objects."""

import argparse
import json
import pathlib
import textwrap


def _resolve_type(pschema: dict) -> str:
    """Return a human-readable type string for a property schema."""
    ptype = pschema.get("type", "")
    if not ptype and "anyOf" in pschema:
        ptype = " | ".join(s.get("type", "?") for s in pschema["anyOf"])
    return ptype


def _expand_schema(
    pschema: dict,
    full_name: str,
    depth: int,
    rows: list[tuple[str, str, str]],
) -> None:
    """Expand a schema's children into rows, handling objects and arrays recursively.

    Mutates rows in place.
    """
    indent = "\u00a0" * ((depth + 1) * 4)

    # Nested object with known properties
    nested_props = pschema.get("properties", {})
    if nested_props:
        _collect_rows(nested_props, prefix=f"{full_name}.", depth=depth + 1, rows=rows)
        return

    # Free-form object (additionalProperties, no properties)
    if pschema.get("type") == "object" and "additionalProperties" in pschema:
        rows.append(
            (
                f"{indent}*(any key)*",
                _resolve_type(pschema["additionalProperties"]),
                "Additional properties.",
            )
        )
        return

    # Array — recurse into items with [] suffix
    if pschema.get("type") == "array":
        items = pschema.get("items", {})
        items_type = _resolve_type(items)
        array_name = f"{full_name}[]"
        items_desc = items.get("description", "")
        rows.append(
            (
                f"{indent}``{array_name}``",
                items_type,
                items_desc,
            )
        )
        _expand_schema(items, array_name, depth + 1, rows)


def _collect_rows(
    props: dict,
    prefix: str = "",
    depth: int = 0,
    rows: list[tuple[str, str, str]] | None = None,
) -> list[tuple[str, str, str]]:
    """Recursively collect (field, type, description) rows from a properties dict.

    Nested object properties are expanded inline with dot-notation field names.
    Array items are expanded with [] notation. Handles arbitrary nesting depth.
    """
    if rows is None:
        rows = []
    indent = "\u00a0" * (depth * 4)

    for pname, pschema in props.items():
        full_name = f"{prefix}{pname}" if prefix else pname
        ptype = _resolve_type(pschema)
        pdesc = pschema.get("description", "")

        # Add enum values to description if present
        if enum := pschema.get("enum"):
            enum_str = ", ".join(f"``{v}``" for v in enum)
            pdesc = f"{pdesc} One of: {enum_str}." if pdesc else f"One of: {enum_str}."

        rows.append((f"{indent}``{full_name}``", ptype, pdesc))
        _expand_schema(pschema, full_name, depth, rows)

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
            lines.append("   :widths: 30 15 55")
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
