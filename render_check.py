"""Render PNGs of the enclosure parts for visual inspection."""
import vtk
import cadquery as cq

# Run enclosure.py with a no-op show_object so its functions become available.
ns = {"show_object": lambda *a, **k: None}
with open("enclosure.py", "r") as f:
    exec(compile(f.read(), "enclosure.py", "exec"), ns)


def _shape(obj):
    if isinstance(obj, cq.Workplane):
        return obj.val()
    return obj


def _actors(obj):
    """Return [(shape, (r,g,b)), ...] for a Workplane or an Assembly."""
    if isinstance(obj, cq.Assembly):
        out = []
        for ch in obj.children:
            shp = _shape(ch.obj)
            if ch.loc is not None:
                shp = shp.located(ch.loc)
            col = ch.color.toTuple()[:3] if ch.color is not None else (0.8, 0.8, 0.8)
            out.append((shp, col))
        return out
    return [(_shape(obj), (0.88, 0.74, 0.12))]


def render(obj, path, azimuth=-50, elevation=28, size=(1100, 850)):
    ren = vtk.vtkRenderer()
    ren.SetBackground(0.52, 0.54, 0.57)
    for shp, col in _actors(obj):
        pd = shp.toVtkPolyData(0.05, 0.2, True)
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(pd)
        mapper.ScalarVisibilityOff()
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        p = actor.GetProperty()
        p.SetColor(*col)
        p.SetEdgeVisibility(1)
        p.SetEdgeColor(0.15, 0.15, 0.15)
        p.SetLineWidth(1)
        ren.AddActor(actor)

    rw = vtk.vtkRenderWindow()
    rw.SetOffScreenRendering(1)
    rw.AddRenderer(ren)
    rw.SetSize(*size)

    ren.ResetCamera()
    cam = ren.GetActiveCamera()
    cam.Azimuth(azimuth)
    cam.Elevation(elevation)
    ren.ResetCameraClippingRange()
    rw.Render()

    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(rw)
    w2i.Update()
    wr = vtk.vtkPNGWriter()
    wr.SetFileName(path)
    wr.SetInputConnection(w2i.GetOutputPort())
    wr.Write()
    print("wrote", path)


render(ns["make_base"](), "out_base.png")
render(ns["make_lid"](), "out_lid.png")
render(ns["make_lid"](), "out_lid_top.png", azimuth=-50, elevation=70)
render(ns["make_assembly"](0.0), "out_assembly_mated.png")
render(ns["make_assembly"](18.0), "out_assembly_exploded.png")
