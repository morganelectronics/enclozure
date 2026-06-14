import cadquery as cq

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

pcb_pedistal_hole = 2.4
pcb_pedistal_dia = pcb_pedistal_hole + 2 * outer_wall

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
# Build
# ----------------------------------------------------------------------------
cavity_floor = outer_wall  # material left under the cavity
cavity_depth = base_height + ledge_height - cavity_floor

result = cq.Workplane("front").placeSketch(sketch_outside).extrude(base_height)

# Ridge: thin band between the two parallel offsets, sat on the base top.
ridge = cross_prism(ledge / 2, ledge_height).cut(cross_prism(-ledge / 2, ledge_height))
result = result.union(ridge.translate((0, 0, base_height)))

# Cavity: hollow up to the ridge inner wall, leaving an outer_wall floor.
cavity = cross_prism(-ledge / 2, cavity_depth + 1.0).translate((0, 0, cavity_floor))
result = result.cut(cavity)

show_object(result)
