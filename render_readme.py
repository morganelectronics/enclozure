"""Generate the README renders into docs/img/ (head-less, via VTK)."""
import math
import os

import cadquery as cq
import vtk

from enclosure import Enclosure

OUT = os.path.join("docs", "img")
os.makedirs(OUT, exist_ok=True)

BASE_COL = (0.85, 0.72, 0.18)
LID_COL = (0.30, 0.55, 0.80)
BG = (0.93, 0.93, 0.95)


def _shape(o):
    return o.val() if isinstance(o, cq.Workplane) else o


def _asm_actors(asm):
    out = []
    for ch in asm.children:
        s = _shape(ch.obj)
        if ch.loc is not None:
            s = s.located(ch.loc)
        col = ch.color.toTuple()[:3] if ch.color is not None else (0.8, 0.8, 0.8)
        out.append((s, col))
    return out


def _render(actors, path, setup, size=(1200, 900), parallel=False, edges=True):
    ren = vtk.vtkRenderer()
    ren.SetBackground(*BG)
    for shp, col in actors:
        pd = shp.toVtkPolyData(0.03, 0.2, True)
        m = vtk.vtkPolyDataMapper()
        m.SetInputData(pd)
        m.ScalarVisibilityOff()
        a = vtk.vtkActor()
        a.SetMapper(m)
        p = a.GetProperty()
        p.SetColor(*col)
        if edges:
            p.SetEdgeVisibility(1)
            p.SetEdgeColor(0.18, 0.18, 0.18)
            p.SetLineWidth(1)
        ren.AddActor(a)
    rw = vtk.vtkRenderWindow()
    rw.SetOffScreenRendering(1)
    rw.AddRenderer(ren)
    rw.SetSize(*size)
    ren.ResetCamera()
    cam = ren.GetActiveCamera()
    if parallel:
        cam.ParallelProjectionOn()
    setup(cam, ren)
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


def iso(az, el):
    def f(cam, ren):
        cam.Azimuth(az)
        cam.Elevation(el)
    return f


def slab(shp, y0, y1):
    """Keep a thin slab x<=0 around y in [y0,y1], z>=22 — for the seal section."""
    keep = cq.Solid.makeBox(120, y1 - y0, 40, cq.Vector(-120, y0, 22))
    return shp.intersect(keep)


def main():
    default = Enclosure()                                   # 100x80x(30+10)
    featured = Enclosure(flange=True, pcb_mounts=True)

    # 1) the default box (closed assembly)
    _render(_asm_actors(default.make_assembly(0.0)), os.path.join(OUT, "default_box.png"),
            iso(-50, 25))

    # 2) assembly with a gap, slantwise
    _render(_asm_actors(default.make_assembly(28.0)), os.path.join(OUT, "exploded.png"),
            iso(-55, 18))

    # 3) bottom part without lid
    _render([(_shape(default.make_base()), BASE_COL)], os.path.join(OUT, "base_open.png"),
            iso(-45, 35))

    # 4) view from the side
    def side(cam, ren):
        fp = cam.GetFocalPoint()
        cam.SetPosition(fp[0], fp[1] - 400, fp[2])
        cam.SetViewUp(0, 0, 1)
        ren.ResetCamera()
    _render(_asm_actors(default.make_assembly(0.0)), os.path.join(OUT, "side.png"),
            side, size=(1200, 700), parallel=True)

    # 5) cross-section through the seal (north arm, x=0 plane)
    asm = default.make_assembly(0.0)
    sec = [(slab(s, 30.0, 41.0), c) for s, c in _asm_actors(asm)]

    def section(cam, ren):
        cam.ParallelProjectionOn()
        fp = cam.GetFocalPoint()
        cam.SetPosition(120, fp[1], fp[2])
        cam.SetViewUp(0, 0, 1)
        ren.ResetCamera()
    _render(sec, os.path.join(OUT, "section_seal.png"), section, size=(1100, 850), edges=False)

    # 6) feature shot: flange + PCB standoffs
    _render([(_shape(featured.make_base()), BASE_COL)], os.path.join(OUT, "featured.png"),
            iso(-55, 30))


if __name__ == "__main__":
    main()
