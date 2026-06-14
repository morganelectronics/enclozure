import cadquery as cq

# Allow the script to run head-less (plain `python enclosure.py`) as well as
# inside CQ-editor, which injects `show_object` into globals.
try:
    show_object
except NameError:
    def show_object(*args, **kwargs):
        pass

# ----------------------------------------------------------------------------
# Enclosure parameters
# ----------------------------------------------------------------------------
lid_height = 10
base_height = 30

width_x = 100
length_y = 80

outer_wall = 2

# O-ring sits in a captured groove and is compressed by a fitted ridge.
oring_notional = 2.0  # o-ring cross-section
oring_notch = oring_notional + 0.8
ledge = 1.2  # ridge (tongue) width
ledge_from_outer = outer_wall + (oring_notch / 2) - (ledge / 2)  # centre ledge in notch
ledge_height = 0.6

# Corner screw posts (M3 heat-set insert: 4 mm hole; 2.6 mm for a self-tapper).
outer_pillar_hole = 4
outer_pillar_dia = outer_pillar_hole + 2 * outer_wall
outer_pillar_lid_clearance_hole = 3.6

pcb_pedistal_hole = 2.4
pcb_pedistal_dia = pcb_pedistal_hole + 2 * outer_wall

# Lid seal groove (cut down from the lid rim) and assembly spacing.
lid_groove_depth = 3.0  # how deep the o-ring groove is sunk into the lid rim
assembly_gap = 0.0      # gap between mated base rim and lid rim (raise to explode)

# ----------------------------------------------------------------------------
# Seal corner radius
# ----------------------------------------------------------------------------
# The seal cross has a convex vertex (arm tip) a short "shoulder" away from a
# concave vertex (armpit). Two equal fillets need 2*r of straight edge between
# them, so r must be <= shoulder / 2 or the fillets overlap into the doubled
# edge. A small margin keeps the fillets from meeting exactly tangent, which
# OCC handles poorly.
seal_shoulder = outer_pillar_dia - ledge_from_outer
oring_centre_radius = min(4.0, seal_shoulder / 2.0 - 0.1)
assert oring_centre_radius > 0.0, "shoulder too small for any fillet"
print(f"{seal_shoulder=}  {oring_centre_radius=}")


# ----------------------------------------------------------------------------
# Seal geometry
# ----------------------------------------------------------------------------
def seal_centreline(radius: float) -> cq.Sketch:
    """Filleted plus/cross seal centreline, routed inside the corner posts.

    Two overlapping rectangles form the cross; filleting at sketch level rounds
    the convex arm tips and the concave armpits in one pass. The groove and the
    ridge are both offset from this single centreline so they track exactly.
    """
    sketch = (
        cq.Sketch()
        .rect(width_x - 2 * outer_pillar_dia, length_y - 2 * ledge_from_outer)
        .rect(width_x - 2 * ledge_from_outer, length_y - 2 * outer_pillar_dia)
        .clean()
        .vertices()
        .fillet(radius)
    )
    return sketch


sketch_outside = cq.Sketch().rect(width_x, length_y).vertices().fillet(outer_pillar_dia / 2)

centreline = seal_centreline(oring_centre_radius)

# Wire form of the centreline, used to make true parallel offsets.
#
# NOTE: pull the wire straight off the sketch's face. `.reset()` clears the
# vertex selection left behind by `.fillet()` so `.faces()` can see the face
# again. The previous `Workplane(...).placeSketch(...).wires().val()` found no
# wires and silently returned the plane ORIGIN (a Vector), which then blew up
# in offset2D with "'Vector' object has no attribute 'offset2D'".
centre_wire = centreline.reset().faces().val().outerWire()


def cross_prism(half_width: float, height: float) -> cq.Workplane:
    """Prism whose footprint is the centreline offset sideways by half_width.

    A positive half_width offsets outward, negative inward. Uses the low-level
    Wire.offset2D / Solid.extrudeLinear path so it doesn't depend on pending-wire
    handling, which differs between CadQuery versions. "arc" rounds the convex
    corners; keep groove and ridge on the same kind so they track.
    """
    wire = centre_wire.offset2D(half_width, "arc")[0]
    face = cq.Face.makeFromWires(wire)
    solid = cq.Solid.extrudeLinear(face, cq.Vector(0, 0, height))
    return cq.Workplane(obj=solid)


# ----------------------------------------------------------------------------
# Corner screw holes
# ----------------------------------------------------------------------------
def screw_points():
    """Centres of the four corner posts (tangent to the outer walls)."""
    dx = width_x / 2 - outer_pillar_dia / 2
    dy = length_y / 2 - outer_pillar_dia / 2
    return [(dx, dy), (-dx, dy), (dx, -dy), (-dx, -dy)]


def drill_corners(part: cq.Workplane, dia: float, z0: float, z1: float) -> cq.Workplane:
    """Cut a dia-wide bore at each corner post, spanning z0..z1."""
    r = dia / 2.0
    for (x, y) in screw_points():
        bore = cq.Solid.makeCylinder(r, z1 - z0, cq.Vector(x, y, z0), cq.Vector(0, 0, 1))
        part = part.cut(cq.Workplane(obj=bore))
    return part


# ----------------------------------------------------------------------------
# Parts
# ----------------------------------------------------------------------------
def make_base() -> cq.Workplane:
    """Base: box, seal ridge (tongue) on the rim, plus-shaped cavity, screw bores.

    Screw bores are sized for the threaded inserts (outer_pillar_hole) and run
    straight through at constant diameter, so the corner posts print without any
    internal overhang / support material.
    """
    cavity_floor = outer_wall  # material left under the cavity
    cavity_depth = base_height + ledge_height - cavity_floor

    base = cq.Workplane("XY").placeSketch(sketch_outside).extrude(base_height)

    # Ridge: thin band between the two parallel offsets, sat on the base top.
    ridge = cross_prism(ledge / 2, ledge_height).cut(cross_prism(-ledge / 2, ledge_height))
    base = base.union(ridge.translate((0, 0, base_height)))

    # Cavity: hollow up to the ridge inner wall, leaving an outer_wall floor.
    cavity = cross_prism(-ledge / 2, cavity_depth + 1.0).translate((0, 0, cavity_floor))
    base = base.cut(cavity)

    # Threaded-insert bores: constant diameter, straight through (no support).
    base = drill_corners(base, outer_pillar_hole, -1.0, base_height + ledge_height + 1.0)
    return base


def make_lid() -> cq.Workplane:
    """Lid (built the same way up as the base for easy comparison).

    Cross-section across the seal, from the outer wall inward:
      * outer wall      : box edge .. +oring_notional/2
      * o-ring groove   : +oring_notional/2 .. -oring_notional/2   (cut from rim)
      * extra inner wall: -oring_notional/2 .. -oring_notional/2 - outer_wall
      * main cavity      : everything inboard of the inner wall

    The groove receives the base's ridge and seats the o-ring; the inner edge of
    the groove is at the seal centreline - oring_notional/2 as specified, and the
    extra wall is one outer_wall thick just inboard of it.
    """
    half = oring_notional / 2.0
    lid_floor = outer_wall

    lid = cq.Workplane("XY").placeSketch(sketch_outside).extrude(lid_height)

    # Main cavity: hollow inboard of the extra inner wall, leaving a floor.
    inner_edge = -(half + outer_wall)  # inner face of the extra wall
    cav_depth = lid_height - lid_floor
    cavity = cross_prism(inner_edge, cav_depth + 1.0).translate((0, 0, lid_floor))
    lid = lid.cut(cavity)

    # O-ring groove: band [-half, +half] cut down from the rim.
    groove = cross_prism(half, lid_groove_depth + 1.0).cut(cross_prism(-half, lid_groove_depth + 1.0))
    groove = groove.translate((0, 0, lid_height - lid_groove_depth))
    lid = lid.cut(groove)

    # Clearance bores: through the lid.
    lid = drill_corners(lid, outer_pillar_lid_clearance_hole, -1.0, lid_height + 1.0)
    return lid


def make_assembly(gap: float = assembly_gap) -> cq.Assembly:
    """Base with the lid flipped over and mated on top, separated by `gap`.

    The plus/cross seal is symmetric about both axes, so flipping the lid 180
    about X lands its groove exactly over the base ridge.
    """
    base = make_base()
    lid = make_lid().rotate((0, 0, 0), (1, 0, 0), 180)
    lid = lid.translate((0, 0, base_height + lid_height + gap))

    asm = cq.Assembly()
    asm.add(base, name="base", color=cq.Color(0.85, 0.72, 0.18))
    asm.add(lid, name="lid", color=cq.Color(0.30, 0.55, 0.80))
    return asm


# ----------------------------------------------------------------------------
# Show — comment/uncomment to inspect individual parts.
# ----------------------------------------------------------------------------
# show_object(make_base())
# show_object(make_lid())
show_object(make_assembly())
