"""Zoomed section on the seal interface (right edge, y=0) to verify ridge-in-groove."""
import vtk
import cadquery as cq

ns = {"show_object": lambda *a, **k: None}
with open("enclosure.py", "r") as f:
    exec(compile(f.read(), "enclosure.py", "exec"), ns)


def _shape(obj):
    return obj.val() if isinstance(obj, cq.Workplane) else obj


def clip(shp):
    # Section at x=0 (a straight run of the north seal arm), keep x<=0, and
    # window around the north arm tip at y~37 so the profile reads cleanly.
    keep = cq.Solid.makeBox(1.5, 9, 26, cq.Vector(-1.5, 32, 24))  # x[-1.5,0] y[32,41] z[24,50]
    return shp.intersect(keep)


def actors(asm):
    out = []
    for ch in asm.children:
        s = _shape(ch.obj)
        if ch.loc is not None:
            s = s.located(ch.loc)
        col = ch.color.toTuple()[:3] if ch.color is not None else (0.8, 0.8, 0.8)
        try:
            cs = clip(s)
            if cs.Volume() > 1e-6:
                out.append((cs, col))
        except Exception as e:
            print("clip skip", e)
    return out


def render(asm, path, size=(1200, 900)):
    ren = vtk.vtkRenderer(); ren.SetBackground(0.52, 0.54, 0.57)
    for shp, col in actors(asm):
        pd = shp.toVtkPolyData(0.01, 0.1, True)
        m = vtk.vtkPolyDataMapper(); m.SetInputData(pd); m.ScalarVisibilityOff()
        a = vtk.vtkActor(); a.SetMapper(m)
        p = a.GetProperty(); p.SetColor(*col); p.SetEdgeVisibility(0)
        ren.AddActor(a)
    rw = vtk.vtkRenderWindow(); rw.SetOffScreenRendering(1); rw.AddRenderer(ren); rw.SetSize(*size)
    ren.ResetCamera()
    cam = ren.GetActiveCamera()
    cam.ParallelProjectionOn()
    fp = cam.GetFocalPoint()
    cam.SetPosition(120, fp[1], fp[2]); cam.SetViewUp(0, 0, 1)
    ren.ResetCamera()
    ren.ResetCameraClippingRange(); rw.Render()
    w2i = vtk.vtkWindowToImageFilter(); w2i.SetInput(rw); w2i.Update()
    wr = vtk.vtkPNGWriter(); wr.SetFileName(path); wr.SetInputConnection(w2i.GetOutputPort()); wr.Write()
    print("wrote", path)


render(ns["make_assembly"](0.0), "seal_mated.png")
render(ns["make_assembly"](4.0), "seal_gap.png")
