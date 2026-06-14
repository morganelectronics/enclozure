"""Build every box size, in four variants, into an output directory (default: dist).

Variants: {plain, flanged} x {heat-set insert holes, self-tapping screw holes}.
Each variant of each size becomes one zip (STEP + STL + PCB DXF + parameters).
If run inside a tag build (GITHUB_REF_TYPE=tag), also writes dist/NOTES.md with a
download table for the release body. Used by CI (artifacts) and the release job.
"""
import os
import sys
from urllib.parse import quote

from box_sizes import SIZES
from enclosure import Enclosure

LID_HEIGHT = 10.0
INSERT_HOLE = 4.0   # M3 heat-set insert
SCREW_HOLE = 2.6    # M3 self-tapping screw pilot

# (suffix, options, corner-fixing label, flange label)
VARIANTS = [
    ("_insert", dict(flange=False, outer_pillar_hole=INSERT_HOLE), "heat-set insert", "no"),
    ("_insert_flanged", dict(flange=True, outer_pillar_hole=INSERT_HOLE), "heat-set insert", "yes"),
    ("_screw", dict(flange=False, outer_pillar_hole=SCREW_HOLE), "self-tapping screw", "no"),
    ("_screw_flanged", dict(flange=True, outer_pillar_hole=SCREW_HOLE), "self-tapping screw", "yes"),
]


def build(outdir: str = "dist"):
    os.makedirs(outdir, exist_ok=True)
    rows = []
    for length, width, height in SIZES:
        for suffix, opts, fixing, flanged in VARIANTS:
            enc = Enclosure(
                width=length,
                breadth=width,
                base_height=round(height - LID_HEIGHT, 1),
                lid_height=LID_HEIGHT,
                **opts,
            )
            zp = enc.export_zip(outdir, suffix=suffix)
            rows.append((length, width, height, flanged, fixing, os.path.basename(zp)))
            print("built", os.path.basename(zp))
    _write_notes(outdir, rows)
    return rows


def _write_notes(outdir, rows):
    """Write a release-notes table with download links (tag builds only)."""
    repo = os.environ.get("GITHUB_REPOSITORY")
    tag = os.environ.get("GITHUB_REF_NAME") if os.environ.get("GITHUB_REF_TYPE") == "tag" else None
    if not (repo and tag):
        return
    lines = [
        "## Pre-built boxes",
        "",
        "Each zip contains base + lid (STEP & STL), the PCB outline (DXF) and a parameters file.",
        "",
        "| Size L×W×H (mm) | Flange | Corner fixing | Download |",
        "|---|---|---|---|",
    ]
    for length, width, height, flanged, fixing, fn in rows:
        url = f"https://github.com/{repo}/releases/download/{tag}/{quote(fn)}"
        lines.append(f"| {length:g}×{width:g}×{height:g} | {flanged} | {fixing} | [zip]({url}) |")
    with open(os.path.join(outdir, "NOTES.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote", os.path.join(outdir, "NOTES.md"))


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "dist")
