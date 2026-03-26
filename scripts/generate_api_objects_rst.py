"""Generate a Sphinx RST reference page from an OpenAPI spec's components.schemas objects."""

import argparse
import json
import pathlib
import textwrap

# Non-breaking space — prevents RST from collapsing leading whitespace in table cells.
_NBSP = "\u00a0"


def _resolve_type(pschema: dict) -> str:
    """Return a human-readable type string for a property schema."""
    ptype = pschema.get("type", "")
    if not ptype and "anyOf" in pschema:
        ptype = " | ".join(s.get("type", "?") for s in pschema["anyOf"])
    return ptype


def _expand_schema(
    pschema: dict,
    depth: int,
    parent_prefix: str,
    rows: list[tuple[str, str, str]],
) -> None:
    """Expand a schema's children into rows, handling objects and arrays recursively.

    Mutates rows in place.
    """
    # Nested object with known properties
    nested_props = pschema.get("properties", {})
    if nested_props:
        _collect_rows(
            nested_props, depth=depth + 1, parent_prefix=parent_prefix, rows=rows
        )
        return

    # Free-form object (additionalProperties, no fixed properties)
    if pschema.get("type") == "object" and "additionalProperties" in pschema:
        addl = pschema["additionalProperties"]
        # additionalProperties can be `true` (allow anything) or a schema dict
        value_type = _resolve_type(addl) if isinstance(addl, dict) else ""
        rows.append(
            (
                f"{parent_prefix}└─{_NBSP}*(any key)*",
                value_type,
                "Additional properties.",
            )
        )
        return

    # Array — show items as a single └─ [] child, then recurse into items
    if pschema.get("type") == "array":
        items = pschema.get("items", {})
        rows.append(
            (
                f"{parent_prefix}└─{_NBSP}``[]``",
                _resolve_type(items),
                items.get("description", ""),
            )
        )
        # [] is the only child so it's always last — continuation is 3 NBSP
        _expand_schema(items, depth + 1, parent_prefix + _NBSP * 3, rows)


def _collect_rows(
    props: dict,
    depth: int = 0,
    parent_prefix: str = "",
    rows: list[tuple[str, str, str]] | None = None,
) -> list[tuple[str, str, str]]:
    """Recursively collect (field, type, description) rows for a properties dict.

    Uses tree characters (├─, └─, │) to show hierarchy. Leading whitespace uses
    non-breaking spaces so RST does not collapse it inside table cells.
    """
    if rows is None:
        rows = []

    items = list(props.items())
    for i, (pname, pschema) in enumerate(items):
        is_last = i == len(items) - 1
        branch = f"└─{_NBSP}" if is_last else f"├─{_NBSP}"
        # Continuation prefix passed to children: 3 NBSP if last, │ + 2 NBSP if not
        child_prefix = parent_prefix + (_NBSP * 3 if is_last else f"│{_NBSP * 2}")

        ptype = _resolve_type(pschema)
        pdesc = pschema.get("description", "")

        if enum := pschema.get("enum"):
            enum_str = ", ".join(f"``{v}``" for v in enum)
            pdesc = f"{pdesc} One of: {enum_str}." if pdesc else f"One of: {enum_str}."

        if depth == 0:
            field_display = f"``{pname}``"
        else:
            field_display = f"{parent_prefix}{branch}``{pname}``"

        rows.append((field_display, ptype, pdesc))
        _expand_schema(pschema, depth, child_prefix, rows)

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
