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


def _collect_rows(
    props: dict,
    prefix: str = "",
    depth: int = 0,
) -> list[tuple[str, str, str]]:
    """Recursively collect (field, type, description) rows from a properties dict.

    Nested object properties are expanded inline with dot-notation field names
    and an extra level of indentation indicated by the prefix.
    """
    rows: list[tuple[str, str, str]] = []
    indent = "\u00a0" * (depth * 4)  # non-breaking spaces for visual indent

    for pname, pschema in props.items():
        full_name = f"{prefix}{pname}" if prefix else pname
        display_name = f"{indent}``{full_name}``"
        ptype = _resolve_type(pschema)
        pdesc = pschema.get("description", "")

        # Add enum values to description if present
        if enum := pschema.get("enum"):
            enum_str = ", ".join(f"``{v}``" for v in enum)
            pdesc = f"{pdesc} One of: {enum_str}." if pdesc else f"One of: {enum_str}."

        rows.append((display_name, ptype, pdesc))

        # Recurse into nested object properties
        nested_props = pschema.get("properties", {})
        if nested_props:
            rows.extend(
                _collect_rows(
                    nested_props,
                    prefix=f"{full_name}.",
                    depth=depth + 1,
                )
            )
        elif ptype == "object" and "additionalProperties" in pschema:
            # Note free-form objects
            rows.append(
                (
                    f"{'\u00a0' * ((depth + 1) * 4)}*(any key)*",
                    _resolve_type(pschema["additionalProperties"]),
                    "Additional properties.",
                )
            )

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
