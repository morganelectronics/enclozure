"""Build every box size, in four variants, into an output directory (default: dist).

Variants: {plain, flanged} x {heat-set insert holes, self-tapping screw holes}.
Each variant of each size becomes one zip (STEP + STL + PCB DXF + parameters).
If run inside a tag build (GITHUB_REF_TYPE=tag), also writes dist/NOTES.md with a
wide download table (all variants of a size on one row) for the release body.
"""
import os
import sys
from urllib.parse import quote

from box_sizes import SIZES
from enclosure import Enclosure

LID_HEIGHT = 10.0
INSERT_HOLE = 4.0   # M3 heat-set insert
SCREW_HOLE = 2.6    # M3 self-tapping screw pilot

# (suffix, options, column header)
VARIANTS = [
    ("_insert", dict(flange=False, outer_pillar_hole=INSERT_HOLE), "Insert"),
    ("_insert_flanged", dict(flange=True, outer_pillar_hole=INSERT_HOLE), "Insert + flange"),
    ("_screw", dict(flange=False, outer_pillar_hole=SCREW_HOLE), "Screw"),
    ("_screw_flanged", dict(flange=True, outer_pillar_hole=SCREW_HOLE), "Screw + flange"),
]


def build(outdir: str = "dist"):
    os.makedirs(outdir, exist_ok=True)
    table = []  # [(length, width, height, {suffix: filename})]
    for length, width, height in SIZES:
        per_variant = {}
        for suffix, opts, _ in VARIANTS:
            enc = Enclosure(
                width=length,
                breadth=width,
                base_height=round(height - LID_HEIGHT, 1),
                lid_height=LID_HEIGHT,
                **opts,
            )
            zp = enc.export_zip(outdir, suffix=suffix)
            per_variant[suffix] = os.path.basename(zp)
            print("built", os.path.basename(zp))
        table.append((length, width, height, per_variant))
    _write_notes(outdir, table)
    return table


def _write_notes(outdir, table):
    """Write a wide release-notes table: one row per size, a link per variant."""
    repo = os.environ.get("GITHUB_REPOSITORY")
    tag = os.environ.get("GITHUB_REF_NAME") if os.environ.get("GITHUB_REF_TYPE") == "tag" else None
    if not (repo and tag):
        return

    def link(fn):
        return f"[zip](https://github.com/{repo}/releases/download/{tag}/{quote(fn)})"

    headers = [v[2] for v in VARIANTS]
    lines = [
        "## Pre-built boxes",
        "",
        "Each zip contains base + lid (STEP & STL), the PCB outline (DXF) and a parameters file.",
        "",
        "| Size L×W×H (mm) | " + " | ".join(headers) + " |",
        "|" + "---|" * (len(headers) + 1),
    ]
    for length, width, height, per_variant in table:
        cells = [link(per_variant[v[0]]) for v in VARIANTS]
        lines.append(f"| {length:g}×{width:g}×{height:g} | " + " | ".join(cells) + " |")
    with open(os.path.join(outdir, "NOTES.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote", os.path.join(outdir, "NOTES.md"))


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "dist")
