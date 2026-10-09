"""High-quality 3D viewer (VTK through PyVista) embedded in Qt."""
from __future__ import annotations
from .paths import debug_log_path

import numpy as np
import pyvista as pv
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget
from pyvistaqt import QtInteractor

from . import render, theme
from .legendbar import LegendBar

BACKGROUNDS = {
    "theme": None,
    "white": ("#FFFFFF", None),
    "black": ("#000000", None),
    "sky": ("#FFFFFF", "#9DB9D8"),
    "graphite": ("#15181E", "#3A4353"),
}

VIEW_DIRS = {
    "iso_sw": ((-1, -1.1, 0.9), (0, 0, 1)),
    "iso_se": ((1.1, -1, 0.9), (0, 0, 1)),
    "iso_ne": ((1, 1.1, 0.9), (0, 0, 1)),
    "iso_nw": ((-1.1, 1, 0.9), (0, 0, 1)),
    "top": ((0, 0, 1), (0, 1, 0)),
    "bottom": ((0, 0, -1), (0, 1, 0)),
    "front": ((0, -1, 0), (0, 0, 1)),
    "back": ((0, 1, 0), (0, 0, 1)),
    "left": ((-1, 0, 0), (0, 0, 1)),
    "right": ((1, 0, 0), (0, 0, 1)),
}


def solid_to_mesh(solid=None, split: bool = False):
    """Triangle mesh of a solid."""
    faces = np.hstack([
        np.full((len(solid.faces), 1), 3, np.int64),
        solid.faces.astype(np.int64),
    ]).ravel()
    mesh = pv.PolyData(solid.verts.astype(np.float64), faces)
    return mesh.compute_normals(split_vertices=split, feature_angle=45, auto_orient_normals=True)


DEFAULT_LOOK = {
    "texture": "grain",
    "vivid": True,
    "edges": True,
    "ssao": False,
}


class Viewer3D(QWidget):
    message = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.plotter = QtInteractor(self, auto_update=False)
        lay.addWidget(self.plotter.interactor)

        self.legend = LegendBar(self)
        lay.addWidget(self.legend)

        self.background = "theme"
        self.show_axes_grid = True
        self.look = dict(DEFAULT_LOOK)
        self.label_size = 13
        self.axis_size = 12
        self.bh_actors = []
        self.bh_labels = []
        self.units = {}
        self.unit_code = {}
        self.unit_hz = {}
        self.edges = {}
        self.code_vis = {}
        self.hz_vis = {}
        self.extras = {}
        self.ve = 1.0
        self._clip_plane = None
        self._model = None

        try:
            self.plotter.enable_anti_aliasing("msaa", multi_samples=8)
        except Exception:
            pass

        self.apply_theme(render=False)
        self._welcome()

    def apply_theme(self, render: bool = True, render_now: bool | None = None):
        if render_now is not None:
            render = render_now
        bg = BACKGROUNDS.get(self.background)
        if bg is None:
            self.plotter.set_background(theme.BG)
        elif bg[1] is None:
            self.plotter.set_background(bg[0])
        else:
            self.plotter.set_background(bg[0], top=bg[1])
        if render:
            self.plotter.render()

    def set_background(self, name: str):
        self.background = name
        self.apply_theme(render_now=True)

    def _welcome(self):
        self.plotter.clear()
        try:
            cube = pv.Cube()
            edges = cube.extract_all_edges() if hasattr(cube, "extract_all_edges") else cube
            self.plotter.add_orientation_widget(edges, color=theme.ACCENT)
        except Exception:
            pass
        self.plotter.reset_camera()

    def clear(self):
        self.plotter.clear()
        self.units.clear()
        self.unit_code.clear()
        self.bh_actors.clear()
        self.bh_labels.clear()
        self.extras.clear()
        self.legend.set_items([])
        self._welcome()

    def show_model(self, model, solids, legend, ve: float = 1.0, boreholes: bool = True, labels: bool = True, boundary=None, opacity: float = 1.0, cutaway: bool = False):
        import time
        try:
            with open(debug_log_path(), "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%H:%M:%S')}] [Viewer3D.show_model] Starting with {len(solids)} solids...\n")
        except Exception:
            pass
        self.clear()
        self._model = model
        self.ve = ve

        legend_items = []
        for code, solid in solids.items():
            lt = legend.get(code) if legend is not None else None
            color = getattr(lt, "color", "#888888") if lt else "#888888"
            try:
                mesh = solid_to_mesh(solid)
                if ve != 1.0:
                    mesh.points[:, 2] *= ve
                actor = self.plotter.add_mesh(mesh, color=color, opacity=opacity, name=f"solid_{code}")
                self.units[code] = actor
            except Exception as e:
                try:
                    with open(debug_log_path(), "a", encoding="utf-8") as f:
                        f.write(f"[{time.strftime('%H:%M:%S')}] [Viewer3D.show_model] Warning on solid {code}: {e}\n")
                except Exception:
                    pass
            legend_items.append(lt or type("Obj", (), {"code": code, "name": code, "color": color, "visible": True})())

        if boreholes and hasattr(model, "project"):
            try:
                self._add_boreholes(model, ve=ve, labels=labels)
            except Exception as e:
                try:
                    with open(debug_log_path(), "a", encoding="utf-8") as f:
                        f.write(f"[{time.strftime('%H:%M:%S')}] [Viewer3D.show_model] Warning on boreholes: {e}\n")
                except Exception:
                    pass

        self.legend.set_items(legend_items)
        try:
            self.plotter.reset_camera()
            self.plotter.render()
        except Exception as e:
            try:
                with open(debug_log_path(), "a", encoding="utf-8") as f:
                    f.write(f"[{time.strftime('%H:%M:%S')}] [Viewer3D.show_model] Warning on render: {e}\n")
            except Exception:
                pass
        try:
            with open(debug_log_path(), "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%H:%M:%S')}] [Viewer3D.show_model] Finished successfully\n")
        except Exception:
            pass

    def _add_boreholes(self, model, ve: float = 1.0, labels: bool = True):
        if not hasattr(model, "project") or not model.project:
            return
        for bh in model.project:
            if bh.x is None or bh.y is None:
                continue
            z_top = (bh.elevation or 0.0) * ve
            z_bot = z_top - (bh.depth or 10.0) * ve
            line = pv.Line((bh.x, bh.y, z_top), (bh.x, bh.y, z_bot))
            tube = line.tube(radius=max(1.0, (bh.depth or 10.0) * 0.01))
            self.bh_actors.append(self.plotter.add_mesh(tube, color="#F0A43A", name=f"bh_{bh.id}"))
            if labels:
                self.bh_labels.append(self.plotter.add_point_labels([(bh.x, bh.y, z_top + 2.0)], [bh.id], point_size=0, text_color=theme.TEXT))

    def show_deviated_drillholes(self, survey_results: list[dict], ve: float = 1.0):
        """Phase 3 GEOVIA Surpac: Renders 3D minimum curvature borehole traces."""
        for s in survey_results:
            bh_id = s.get("borehole_id", "BH")
            coords = s.get("coordinates", [])
            if len(coords) < 2:
                continue
            pts = np.array([[c[0], c[1], c[2] * ve] for c in coords])
            poly = pv.PolyData(pts)
            poly.lines = np.hstack([len(pts), np.arange(len(pts))])
            tube = poly.tube(radius=1.5)
            self.plotter.add_mesh(tube, color="#E67E22", name=f"deviated_{bh_id}")

    def show_block_model(self, block_model, attribute: str = "grade", cutoff: float | None = None, ve: float = 1.0):
        """Phase 4 GEOVIA Surpac: Renders 3D Grade Block Model."""
        pts = []
        vals = []
        for blk in getattr(block_model, "blocks", []):
            val = blk.attributes.get(attribute, 0.0)
            if cutoff is not None and val < cutoff:
                continue
            pts.append([blk.x, blk.y, blk.z * ve])
            vals.append(val)
        if pts:
            cloud = pv.PolyData(np.array(pts))
            cloud[attribute] = np.array(vals)
            self.plotter.add_mesh(cloud, scalars=attribute, cmap="viridis", point_size=8, render_points_as_spheres=True, name="block_model")
            self.plotter.reset_camera()

    def show_wireframe(self, dtm, color: str = "#00AAFF", opacity: float = 0.8, name: str = "wireframe"):
        """Phase 3 GEOVIA Surpac: Renders Surpac .dtm wireframe."""
        if hasattr(dtm, "vertices") and hasattr(dtm, "triangles"):
            faces = np.hstack([np.full((len(dtm.triangles), 1), 3), dtm.triangles]).ravel()
            mesh = pv.PolyData(np.array(dtm.vertices), faces)
            self.plotter.add_mesh(mesh, color=color, opacity=opacity, name=name)

    def set_view(self, name: str):
        if name in VIEW_DIRS:
            pos, up = VIEW_DIRS[name]
            self.plotter.view_vector(pos, viewup=up)

    def set_unit_visible(self, code: str, visible: bool):
        actor = self.units.get(code)
        if actor:
            actor.SetVisibility(bool(visible))
            self.plotter.render()

    def set_axes_grid(self, on: bool):
        self.show_axes_grid = bool(on)
        if on:
            self.plotter.show_grid()
        else:
            self.plotter.remove_bounds_axes()
        self.plotter.render()

    def enable_clip(self, normal: str = "x"):
        self.plotter.add_clip_plane(normal=normal, assign_to_axis=normal)

    def disable_clip(self):
        self.plotter.clear_clip_planes()

    def screenshot(self, path: str):
        self.plotter.screenshot(path)
