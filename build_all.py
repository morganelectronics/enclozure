"""Build every box size into an output directory (default: ./dist).

Each size becomes one zip (STEP + STL + PCB DXF + parameters), named by its
dimensions. Used by CI (artifacts) and the release workflow.
"""
import os
import sys

from box_sizes import SIZES
from enclosure import Enclosure

LID_HEIGHT = 10.0


def build(outdir: str = "dist"):
    os.makedirs(outdir, exist_ok=True)
    made = []
    for length, width, height in SIZES:
        enc = Enclosure(
            width=length,
            breadth=width,
            base_height=round(height - LID_HEIGHT, 1),
            lid_height=LID_HEIGHT,
        )
        zp = enc.export_zip(outdir)
        made.append(zp)
        print("built", zp)
    return made


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "dist")
