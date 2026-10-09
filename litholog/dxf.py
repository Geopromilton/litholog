"""AutoCAD DXF export for boreholes, cross-sections, and contour lines.

Outputs standard AutoCAD DXF (R12 / AC1009 ASCII), compatible with AutoCAD,
Civil 3D, Carlson, QGIS, Surpac, MicroStation, and all modern CAD tools.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from .correlate import panel, units
from .patterns import Legend
from .project import Project
from .section import SectionLine, contact_edges


def _hex_to_aci(hex_col: str) -> int:
    """Map a hex color (#RRGGBB) to the closest AutoCAD Color Index (1-255)."""
    hex_col = hex_col.lstrip("#")
    if len(hex_col) != 6:
        return 7
    r, g, b = int(hex_col[0:2], 16), int(hex_col[2:4], 16), int(hex_col[4:6], 16)

    # Standard ACI primaries: 1: Red, 2: Yellow, 3: Green, 4: Cyan, 5: Blue, 6: Magenta, 7: White/Black, 8: DkGray, 9: LtGray
    standards = [
        (1, 255, 0, 0),
        (2, 255, 255, 0),
        (3, 0, 255, 0),
        (4, 0, 255, 255),
        (5, 0, 0, 255),
        (6, 255, 0, 255),
        (7, 255, 255, 255),
        (8, 128, 128, 128),
        (9, 192, 192, 192),
        (10, 255, 0, 0),
        (30, 255, 127, 0),
        (50, 255, 255, 0),
        (70, 127, 255, 0),
        (90, 0, 255, 0),
        (110, 0, 255, 127),
        (130, 0, 255, 255),
        (150, 0, 127, 255),
        (170, 0, 0, 255),
        (190, 127, 0, 255),
        (210, 255, 0, 255),
        (230, 255, 0, 127),
        (34, 165, 82, 0),
        (144, 0, 100, 180),
        (44, 200, 150, 50),
    ]
    best_dist = float("inf")
    best_aci = 7
    for aci, cr, cg, cb in standards:
        dist = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2
        if dist < best_dist:
            best_dist = dist
            best_aci = aci
    return best_aci


class DxfDocument:
    """Lightweight, zero-dependency DXF R12 ASCII builder."""

    def __init__(self):
        self.layers: dict[str, int] = {"0": 7}
        self.entities: list[str] = []

    def add_layer(self, name: str, color: int = 7):
        clean = "".join(c if c.isalnum() or c in "_-" else "_" for c in name)
        self.layers[clean] = color
        return clean

    def add_point(self, x: float, y: float, z: float = 0.0, layer: str = "0", color: int | None = None):
        c_code = f" 62\n{color}\n" if color is not None else ""
        self.entities.append(
            f"  0\nPOINT\n  8\n{layer}\n{c_code}"
            f" 10\n{x:.4f}\n 20\n{y:.4f}\n 30\n{z:.4f}\n"
        )

    def add_line(self, x1: float, y1: float, z1: float,
                 x2: float, y2: float, z2: float,
                 layer: str = "0", color: int | None = None):
        c_code = f" 62\n{color}\n" if color is not None else ""
        self.entities.append(
            f"  0\nLINE\n  8\n{layer}\n{c_code}"
            f" 10\n{x1:.4f}\n 20\n{y1:.4f}\n 30\n{z1:.4f}\n"
            f" 11\n{x2:.4f}\n 21\n{y2:.4f}\n 31\n{z2:.4f}\n"
        )

    def add_text(self, text: str, x: float, y: float, z: float = 0.0,
                 height: float = 2.5, layer: str = "0", color: int | None = None, rotation: float = 0.0):
        c_code = f" 62\n{color}\n" if color is not None else ""
        rot_code = f" 50\n{rotation:.2f}\n" if rotation else ""
        self.entities.append(
            f"  0\nTEXT\n  8\n{layer}\n{c_code}"
            f" 10\n{x:.4f}\n 20\n{y:.4f}\n 30\n{z:.4f}\n"
            f" 40\n{height:.3f}\n  1\n{text}\n{rot_code}"
        )

    def add_polyline_3d(self, points, layer: str = "0", color: int | None = None, closed: bool = False):
        if len(points) < 2:
            return
        c_code = f" 62\n{color}\n" if color is not None else ""
        flags = 9 if closed else 8  # 8 = 3D polyline, 1 = closed
        chunk = [f"  0\nPOLYLINE\n  8\n{layer}\n{c_code} 66\n1\n 70\n{flags}\n"]
        for p in points:
            pz = p[2] if len(p) > 2 else 0.0
            chunk.append(
                f"  0\nVERTEX\n  8\n{layer}\n 70\n32\n"
                f" 10\n{p[0]:.4f}\n 20\n{p[1]:.4f}\n 30\n{pz:.4f}\n"
            )
        chunk.append("  0\nSEQEND\n")
        self.entities.append("".join(chunk))

    def write(self, path: Path | str) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "  0\nSECTION\n  2\nHEADER\n",
            "  9\n$ACADVER\n  1\nAC1009\n",
            "  0\nENDSEC\n",
            "  0\nSECTION\n  2\nTABLES\n",
            "  0\nTABLE\n  2\nLAYER\n 70\n" + str(len(self.layers)) + "\n",
        ]
        for name, col in self.layers.items():
            lines.append(
                f"  0\nLAYER\n  2\n{name}\n 70\n0\n 62\n{col}\n  6\nCONTINUOUS\n"
            )
        lines.append("  0\nENDTAB\n  0\nENDSEC\n")
        lines.append("  0\nSECTION\n  2\nENTITIES\n")
        lines.extend(self.entities)
        lines.append("  0\nENDSEC\n  0\nEOF\n")
        p.write_text("".join(lines), encoding="ascii", errors="replace")
        return p


def export_boreholes_dxf(project: Project, path: Path | str, legend: Legend | None = None) -> Path:
    """Export 3D borehole sticks, collars and lithology contacts to AutoCAD DXF."""
    legend = legend or project.legend
    doc = DxfDocument()
    doc.add_layer("COLLARS", 7)
    doc.add_layer("BOREHOLES", 8)
    doc.add_layer("WATER_TABLE", 5)

    for bh in project:
        if pd.isna(bh.x) or pd.isna(bh.y):
            continue
        elev = bh.elevation if bh.has_elevation else 0.0
        depth = bh.depth or 1.0

        # Collar Point & Label
        doc.add_point(bh.x, bh.y, elev, layer="COLLARS", color=7)
        label = f"{bh.id} (El:{elev:.1f}m, TD:{depth:.1f}m)"
        doc.add_text(label, bh.x + 1.0, bh.y + 1.0, elev, height=2.0, layer="COLLARS", color=7)

        # Full borehole axis line
        doc.add_line(bh.x, bh.y, elev, bh.x, bh.y, elev - depth, layer="BOREHOLES", color=8)

        # Lithology intervals
        for _, r in bh.lithology.iterrows():
            f, t, code = r.get("from"), r.get("to"), str(r.get("code", "")).strip().upper()
            if pd.isna(f) or pd.isna(t) or t <= f:
                continue
            z_top = elev - f
            z_bot = elev - t
            ltype = legend.get(code)
            aci = _hex_to_aci(ltype.color)
            layer_name = doc.add_layer(f"LITH_{code}", aci)
            doc.add_line(bh.x, bh.y, z_top, bh.x, bh.y, z_bot, layer=layer_name, color=aci)

        # Water level marker
        wl = bh.water_levels.dropna(subset=["depth"])
        if len(wl) and bh.has_elevation:
            wl_z = elev - wl.iloc[-1]["depth"]
            doc.add_point(bh.x, bh.y, wl_z, layer="WATER_TABLE", color=5)
            doc.add_text(f"WL: {wl_z:.2f}m", bh.x + 1.0, bh.y - 1.0, wl_z, height=1.5, layer="WATER_TABLE", color=5)

    return doc.write(path)


def export_section_dxf(project: Project, line: SectionLine, path: Path | str,
                       legend: Legend | None = None, ve: float = 1.0,
                       scale: float = 25.0) -> Path:
    """Export correlated 2D cross-section panels and traces to AutoCAD DXF.

    Coordinates in DXF are (X=Distance along section, Y=Elevation * VE).
    """
    legend = legend or project.legend
    doc = DxfDocument()
    doc.add_layer("GROUND_SURFACE", 34)
    doc.add_layer("BASE_OF_LOGS", 8)
    doc.add_layer("WATER_TABLE", 5)
    doc.add_layer("BOREHOLES", 7)
    doc.add_layer("CONTACTS", 8)

    holes = [(st, project.borehole(st.id)) for st in line.stations]
    unit_sets = [units(b, datum="elevation") for _, b in holes]

    # Lithology correlated panels
    for k in range(len(holes) - 1):
        (sa, _), (sb, _) = holes[k], holes[k + 1]
        polys = panel(unit_sets[k], unit_sets[k + 1], sa.s, sb.s, scale)
        for code, verts in polys:
            ltype = legend.get(code)
            aci = _hex_to_aci(ltype.color)
            layer = doc.add_layer(f"LITH_{code.upper()}", aci)
            # Transform verts with vertical exaggeration
            dxf_pts = [(v[0], v[1] * ve, 0.0) for v in verts]
            doc.add_polyline_3d(dxf_pts, layer=layer, color=aci, closed=True)

        for p, q in contact_edges(polys):
            doc.add_line(p[0], p[1] * ve, 0.0, q[0], q[1] * ve, 0.0, layer="CONTACTS", color=8)

    # Ground line & Base line
    tops = [(st.s, us[0].top * ve, 0.0) for (st, _), us in zip(holes, unit_sets) if us]
    if len(tops) >= 2:
        doc.add_polyline_3d(tops, layer="GROUND_SURFACE", color=34, closed=False)

    bots = [(st.s, us[-1].bot * ve, 0.0) for (st, _), us in zip(holes, unit_sets) if us]
    if len(bots) >= 2:
        doc.add_polyline_3d(bots, layer="BASE_OF_LOGS", color=8, closed=False)

    # Water table
    wl_pts = []
    for (st, bh), us in zip(holes, unit_sets):
        wl = bh.water_levels.dropna(subset=["depth"])
        if len(wl) and us and bh.has_elevation:
            wl_z = (bh.elevation - wl.iloc[-1]["depth"]) * ve
            wl_pts.append((st.s, wl_z, 0.0))
    if len(wl_pts) >= 2:
        doc.add_polyline_3d(wl_pts, layer="WATER_TABLE", color=5, closed=False)

    # Borehole axes & labels
    for (st, bh), us in zip(holes, unit_sets):
        if not us:
            continue
        z_top = us[0].top * ve
        z_bot = us[-1].bot * ve
        doc.add_line(st.s, z_top, 0.0, st.s, z_bot, 0.0, layer="BOREHOLES", color=7)
        label = st.id if abs(st.offset) < 1e-6 else f"{st.id} ({st.offset:+.0f}m)"
        doc.add_text(label, st.s, z_top + 2.0, 0.0, height=3.0, layer="BOREHOLES", color=7)

    return doc.write(path)


def export_contours_dxf(grid, path: Path | str, levels=None, layer_name: str = "CONTOURS") -> Path:
    """Export contour lines of a Grid to AutoCAD DXF with 3D elevations."""
    import matplotlib.pyplot as plt

    doc = DxfDocument()
    doc.add_layer(layer_name, 4)  # Cyan

    X, Y = grid.mesh()
    Z = np.ma.masked_invalid(grid.z)

    # Extract contours via matplotlib internal contour engine without displaying
    fig, ax = plt.subplots()
    try:
        cs = ax.contour(X, Y, Z, levels=levels if levels is not None else 12)
        for level, segs in zip(cs.levels, cs.allsegs):
            for seg in segs:
                if len(seg) < 2:
                    continue
                pts_3d = [(float(pt[0]), float(pt[1]), float(level)) for pt in seg]
                is_closed = np.allclose(seg[0], seg[-1])
                doc.add_polyline_3d(pts_3d, layer=layer_name, color=4, closed=is_closed)
    finally:
        plt.close(fig)

    return doc.write(path)
