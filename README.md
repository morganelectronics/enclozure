# enclosure

Parametric sealed enclosure generator (CadQuery). A two-part box (base + lid)
with an o-ring tongue-and-groove seal, corner screw posts for threaded inserts,
and an M5 wall-mount flange.

## Generate STEP + STL

Exports `base` and `lid` as STEP and STL, bundled into a single `.zip` in the
current directory:

```sh
uv run enclosure.py --width 100 --breadth 80 --lid-height 10 --base-height 30
```

Options:

| flag             | default | meaning                 |
|------------------|---------|-------------------------|
| `--width`        | 100     | overall X (mm)          |
| `--breadth`      | 80      | overall Y (mm)          |
| `--lid-height`   | 10      | lid Z (mm)              |
| `--base-height`  | 30      | base Z (mm)             |
| `--flange`       | off     | add the M5 mount flange |
| `-o/--outdir`    | `.`     | output directory        |

Running with no arguments produces the default box (no flange).

## Flange (opt-in, `--flange`)

A flat M5 mounting base. It is the **convex hull of one disc per centre**: the
corner pillars (at the pillar radius, so the hull reproduces the case outline)
plus a disc of radius `head_r + outer_wall` at every mounting hole and slot end
(so one wall thickness of plate is left around the big head hole). Being a hull
it is entirely convex — no
concave notches or thin "weak bits". Each long side carries a central keyhole
slot (eye + slot, parallel to the wall, ~2 head-widths long so the head drops
through the eye and slides fully over the plate) plus an end round hole either
side. As the box shrinks the round holes are dropped and only the keyhole slot
remains.

## Inspect interactively

Open `enclosure.py` in CQ-editor (it injects `show_object`); toggle the
`show_object(...)` calls at the bottom to view the base, lid, or assembly.
`render_check.py` renders PNGs head-less via VTK.
