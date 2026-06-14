"""Parametric sealed enclosure (CadQuery).

Run as a script to export STEP + STL of the parts, zipped, into the CWD:

    uv run enclosure.py --width 100 --breadth 80 --lid-height 10 --base-height 30

Open in CQ-editor to interactively inspect (it injects `show_object`); comment /
uncomment the calls at the very bottom to look at the base, lid or assembly.
"""
import math
from dataclasses import dataclass

import cadquery as cq


def _convex_hull(points):
    """2-D convex hull (Andrew's monotone chain), returned CCW."""
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


@dataclass
class Enclosure:
    # ---- overall size (the four headline parameters) --------------------
    width: float = 100.0       # X
    breadth: float = 80.0      # Y
    lid_height: float = 10.0   # Z
    base_height: float = 30.0  # Z

    # ---- shell / seal ---------------------------------------------------
    outer_wall: float = 2.0
    oring_notional: float = 2.0   # o-ring cross-section
    ledge: float = 1.2            # ridge (tongue) width
    ledge_height: float = 0.6
    lid_groove_depth: float = 3.0

    # ---- corner screw posts --------------------------------------------
    outer_pillar_hole: float = 4.0              # threaded-insert hole (base)
    outer_pillar_lid_clearance_hole: float = 3.6  # screw clearance (lid)

    # ---- M5 wall-mount flange (opt-in) ---------------------------------
    flange: bool = False
    flange_thickness: float = 4.0
    flange_wall_gap: float = 1.0        # gap from case wall to the head hole
    flange_end_margin: float = 4.0      # keep end round holes in from the corners
    keyhole_len_heads: float = 2.0      # slot length (eye centre -> slot end) in head widths
    m5_clearance: float = 5.5           # M5 shank clearance
    m5_head_clearance: float = 10.0     # M5 head pass-through (keyhole eye / "head width")

    # ---- misc -----------------------------------------------------------
    assembly_gap: float = 0.0

    # =====================================================================
    # Derived seal dimensions
    # =====================================================================
    @property
    def oring_notch(self) -> float:
        return self.oring_notional + 0.8

    @property
    def ledge_from_outer(self) -> float:
        # centre the ledge in the o-ring notch
        return self.outer_wall + self.oring_notch / 2 - self.ledge / 2

    @property
    def outer_pillar_dia(self) -> float:
        return self.outer_pillar_hole + 2 * self.outer_wall

    @property
    def oring_centre_radius(self) -> float:
        # The seal cross has a convex arm tip a short "shoulder" away from a
        # concave armpit; two equal fillets need 2*r of straight edge between
        # them, so r <= shoulder/2 (with a small margin OCC likes).
        seal_shoulder = self.outer_pillar_dia - self.ledge_from_outer
        r = min(4.0, seal_shoulder / 2.0 - 0.1)
        assert r > 0.0, "shoulder too small for any fillet"
        return r

    # =====================================================================
    # Seal geometry
    # =====================================================================
    def sketch_outside(self) -> cq.Sketch:
        return cq.Sketch().rect(self.width, self.breadth).vertices().fillet(self.outer_pillar_dia / 2)

    def seal_centreline(self) -> cq.Sketch:
        """Filleted plus/cross seal centreline, routed inside the corner posts."""
        return (
            cq.Sketch()
            .rect(self.width - 2 * self.outer_pillar_dia, self.breadth - 2 * self.ledge_from_outer)
            .rect(self.width - 2 * self.ledge_from_outer, self.breadth - 2 * self.outer_pillar_dia)
            .clean()
            .vertices()
            .fillet(self.oring_centre_radius)
        )

    def centre_wire(self) -> cq.Wire:
        """Outer wire of the centreline (cached). `.reset()` clears the vertex
        selection left by `.fillet()` so `.faces()` can see the face again."""
        if getattr(self, "_cw", None) is None:
            self._cw = self.seal_centreline().reset().faces().val().outerWire()
        return self._cw

    def cross_prism(self, half_width: float, height: float) -> cq.Workplane:
        """Prism whose footprint is the centreline offset sideways by half_width
        (positive = outward, negative = inward). "arc" rounds the convex corners."""
        wire = self.centre_wire().offset2D(half_width, "arc")[0]
        face = cq.Face.makeFromWires(wire)
        solid = cq.Solid.extrudeLinear(face, cq.Vector(0, 0, height))
        return cq.Workplane(obj=solid)

    # =====================================================================
    # Corner screw bores
    # =====================================================================
    def screw_points(self):
        dx = self.width / 2 - self.outer_pillar_dia / 2
        dy = self.breadth / 2 - self.outer_pillar_dia / 2
        return [(dx, dy), (-dx, dy), (dx, -dy), (-dx, -dy)]

    def drill_corners(self, part: cq.Workplane, dia: float, z0: float, z1: float) -> cq.Workplane:
        r = dia / 2.0
        for (x, y) in self.screw_points():
            bore = cq.Solid.makeCylinder(r, z1 - z0, cq.Vector(x, y, z0), cq.Vector(0, 0, 1))
            part = part.cut(cq.Workplane(obj=bore))
        return part

    # =====================================================================
    # Flange
    # =====================================================================
    def _flange_geom(self):
        """Shared flange dimensions.

        Features live just outside each long (X) wall, so the keyhole slot runs
        parallel to that wall. pad_r is the screw-head pad radius (head + clear).
        """
        head_r = self.m5_head_clearance / 2
        shank_r = self.m5_clearance / 2
        # hull disc radius: leaves one wall thickness of plate around the head hole
        pad_r = head_r + self.outer_wall
        slot_len = self.keyhole_len_heads * self.m5_head_clearance  # eye centre -> slot end
        feat_y = self.breadth / 2 + head_r + self.flange_wall_gap   # the head hole clears the wall
        round_x = self.width / 2 - (pad_r + self.flange_end_margin)
        # keep the end round holes only while their pads clear the centre slot pad
        include_round = (round_x - pad_r) > (slot_len / 2 + pad_r + 2.0)
        return head_r, shank_r, pad_r, slot_len, feat_y, round_x, include_round

    def include_round_holes(self) -> bool:
        return self._flange_geom()[6]

    def _flange_centres(self):
        """(x, y, radius) of every disc the flange hulls: the corner pillars
        (at the pillar radius, so the hull reproduces the case outline) plus a
        head-clearance disc at each mounting hole / slot end."""
        head_r, shank_r, pad_r, slot_len, feat_y, round_x, inc = self._flange_geom()
        discs = [(x, y, self.outer_pillar_dia / 2) for (x, y) in self.screw_points()]
        for sgn in (+1, -1):
            fy = sgn * feat_y
            discs += [(-slot_len / 2, fy, pad_r), (slot_len / 2, fy, pad_r)]  # slot ends
            if inc:
                discs += [(round_x, fy, pad_r), (-round_x, fy, pad_r)]
        return discs

    def _flange_outline(self, segments: int = 48):
        """Convex hull of one disc per centre -> a smooth, all-convex base with
        no concave (crack-prone) features. Each disc is sampled into points and
        the hull of the lot is taken."""
        pts = []
        for (x, y, r) in self._flange_centres():
            for k in range(segments):
                a = 2 * math.pi * k / segments
                pts.append((x + r * math.cos(a), y + r * math.sin(a)))
        return _convex_hull(pts)

    def make_flanges(self) -> cq.Workplane:
        return cq.Workplane("XY").polyline(self._flange_outline()).close().extrude(self.flange_thickness)

    def cut_flange_holes(self, part: cq.Workplane) -> cq.Workplane:
        head_r, shank_r, pad_r, slot_len, feat_y, round_x, inc = self._flange_geom()
        t = self.flange_thickness
        for sgn in (+1, -1):
            fy = sgn * feat_y
            # Keyhole: eye (head passes) at +X end, shank slot back to -X end.
            sk = (
                cq.Sketch()
                .push([(slot_len / 2, fy)]).circle(head_r)
                .reset().push([(0.0, fy)]).rect(slot_len, 2 * shank_r)
                .reset().push([(-slot_len / 2, fy)]).circle(shank_r)
                .clean()
            )
            keyhole = cq.Workplane("XY").placeSketch(sk).extrude(t + 2).translate((0, 0, -1))
            part = part.cut(keyhole)
            if inc:
                for cx in (round_x, -round_x):
                    cyl = cq.Solid.makeCylinder(shank_r, t + 2, cq.Vector(cx, fy, -1))
                    part = part.cut(cq.Workplane(obj=cyl))
        return part

    # =====================================================================
    # Parts
    # =====================================================================
    def make_base(self) -> cq.Workplane:
        """Box, seal ridge, plus-shaped cavity, optional flange, through bores."""
        cavity_floor = self.outer_wall
        cavity_depth = self.base_height + self.ledge_height - cavity_floor

        base = cq.Workplane("XY").placeSketch(self.sketch_outside()).extrude(self.base_height)

        ridge = self.cross_prism(self.ledge / 2, self.ledge_height).cut(
            self.cross_prism(-self.ledge / 2, self.ledge_height)
        )
        base = base.union(ridge.translate((0, 0, self.base_height)))

        cavity = self.cross_prism(-self.ledge / 2, cavity_depth + 1.0).translate((0, 0, cavity_floor))
        base = base.cut(cavity)

        if self.flange:
            base = base.union(self.make_flanges())

        # Threaded-insert bores: constant diameter, straight through (no support).
        base = self.drill_corners(base, self.outer_pillar_hole, -1.0, self.base_height + self.ledge_height + 1.0)

        if self.flange:
            base = self.cut_flange_holes(base)
        return base

    def make_lid(self) -> cq.Workplane:
        """Lid (built the same way up as the base for easy comparison).

        Across the seal, outward -> inward: outer wall | o-ring groove (cut from
        the rim) | extra inner wall (one wall thick) | main cavity. The groove's
        inner edge sits at the seal centreline - oring_notional/2.
        """
        half = self.oring_notional / 2.0
        lid_floor = self.outer_wall

        lid = cq.Workplane("XY").placeSketch(self.sketch_outside()).extrude(self.lid_height)

        inner_edge = -(half + self.outer_wall)
        cav_depth = self.lid_height - lid_floor
        cavity = self.cross_prism(inner_edge, cav_depth + 1.0).translate((0, 0, lid_floor))
        lid = lid.cut(cavity)

        groove = self.cross_prism(half, self.lid_groove_depth + 1.0).cut(
            self.cross_prism(-half, self.lid_groove_depth + 1.0)
        )
        groove = groove.translate((0, 0, self.lid_height - self.lid_groove_depth))
        lid = lid.cut(groove)

        lid = self.drill_corners(lid, self.outer_pillar_lid_clearance_hole, -1.0, self.lid_height + 1.0)
        return lid

    def make_assembly(self, gap: float = None) -> cq.Assembly:
        if gap is None:
            gap = self.assembly_gap
        base = self.make_base()
        lid = self.make_lid().rotate((0, 0, 0), (1, 0, 0), 180)
        lid = lid.translate((0, 0, self.base_height + self.lid_height + gap))
        asm = cq.Assembly()
        asm.add(base, name="base", color=cq.Color(0.85, 0.72, 0.18))
        asm.add(lid, name="lid", color=cq.Color(0.30, 0.55, 0.80))
        return asm

    # =====================================================================
    # Export
    # =====================================================================
    def stem(self) -> str:
        return (f"enclosure_{self.width:g}x{self.breadth:g}"
                f"_base{self.base_height:g}_lid{self.lid_height:g}")

    def export_zip(self, outdir: str = ".") -> str:
        """Write STEP + STL of base and lid into a single .zip in `outdir`."""
        import os
        import tempfile
        import zipfile

        os.makedirs(outdir, exist_ok=True)
        parts = {"base": self.make_base(), "lid": self.make_lid()}
        stem = self.stem()
        zip_path = os.path.join(outdir, stem + ".zip")

        with tempfile.TemporaryDirectory() as td:
            files = []
            for name, part in parts.items():
                step = os.path.join(td, f"{stem}_{name}.step")
                stl = os.path.join(td, f"{stem}_{name}.stl")
                cq.exporters.export(part, step)
                cq.exporters.export(part, stl, tolerance=0.1, angularTolerance=0.2)
                files += [step, stl]
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
                for f in files:
                    z.write(f, os.path.basename(f))
        return zip_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv=None):
    import argparse

    p = argparse.ArgumentParser(description="Export STEP + STL of the enclosure parts as a .zip in the CWD.")
    p.add_argument("--width", type=float, default=100.0, help="overall X (mm)")
    p.add_argument("--breadth", type=float, default=80.0, help="overall Y (mm)")
    p.add_argument("--lid-height", type=float, default=10.0, help="lid Z (mm)")
    p.add_argument("--base-height", type=float, default=30.0, help="base Z (mm)")
    p.add_argument("--flange", action="store_true", help="add the M5 wall-mount flange")
    p.add_argument("-o", "--outdir", default=".", help="output directory (default: CWD)")
    a = p.parse_args(argv)

    enc = Enclosure(
        width=a.width, breadth=a.breadth,
        lid_height=a.lid_height, base_height=a.base_height,
        flange=a.flange,
    )
    path = enc.export_zip(a.outdir)
    if enc.flange:
        note = "flange: round + keyhole" if enc.include_round_holes() else "flange: keyhole only"
    else:
        note = "no flange"
    print(f"wrote {path}  ({note})")


# ---------------------------------------------------------------------------
# Dispatch: CQ-editor shows objects; plain run / uv run exports.
# ---------------------------------------------------------------------------
try:
    show_object  # type: ignore  # noqa: B018  (injected by CQ-editor)
    _HAVE_SHOW = True
except NameError:
    _HAVE_SHOW = False

    def show_object(*args, **kwargs):  # noqa: D401
        pass

if _HAVE_SHOW:
    _enc = Enclosure()
    _enc.flange = True
    # show_object(_enc.make_base(), name="base")
    # show_object(_enc.make_lid(), name="lid")
    show_object(_enc.make_assembly(), name="assembly")
elif __name__ == "__main__":
    main()
