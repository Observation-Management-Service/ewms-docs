"""Generate a Sphinx RST reference page from an OpenAPI spec's components.schemas objects."""

import argparse
import json
import pathlib
import textwrap


def main() -> None:
    """Parse args and write the RST file."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=pathlib.Path, help="Path to openapi.json")
    parser.add_argument("output", type=pathlib.Path, help="Path to output .rst file")
    parser.add_argument("--title", default="API Schemas", help="Page title")
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
            lines.append(".. list-table::")
            lines.append("   :header-rows: 1")
            lines.append("   :widths: 25 15 60")
            lines.append("")
            lines.append("   * - Field")
            lines.append("     - Type")
            lines.append("     - Description")
            for pname, pschema in props.items():
                ptype = pschema.get("type", "")
                if not ptype and "anyOf" in pschema:
                    ptype = " | ".join(s.get("type", "?") for s in pschema["anyOf"])
                pdesc = pschema.get("description", "")
                lines.append(f"   * - ``{pname}``")
                lines.append(f"     - {ptype}")
                lines.append(f"     - {pdesc}")
        lines.append("")

    args.output.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
