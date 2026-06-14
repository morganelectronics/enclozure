"""Render PNGs of the enclosure parts for visual inspection."""
import vtk
import cadquery as cq

from enclosure import Enclosure


def _shape(obj):
    return obj.val() if isinstance(obj, cq.Workplane) else obj


def _actors(obj):
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


if __name__ == "__main__":
    default = Enclosure()  # bare default: no flange, no mounts
    big = Enclosure(width=100, breadth=80, flange=True, pcb_mounts=True)
    small = Enclosure(width=45, breadth=40, base_height=18, lid_height=8, flange=True)
    render(default.make_base(), "out_base_default.png")
    render(big.make_base(), "out_base_full.png", azimuth=-55, elevation=35)   # flange + standoffs
    render(big.make_base(), "out_flange_under.png", elevation=-35)            # flange from below
    render(small.make_base(), "out_flange_small.png", elevation=-35)
    render(default.make_assembly(), "out_assembly.png")
