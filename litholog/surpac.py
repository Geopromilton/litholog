"""GEOVIA Surpac string (.str) and triangulation wireframe (.dtm) format handler.

Reads and writes Surpac ASCII string files (.str) and DTM surface wireframes (.dtm).
Surpac coordinates are ordered Y (Northing), X (Easting), Z (Elevation).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


class SurpacString:
    """Represents a set of polyline strings in a Surpac .str file."""

    def __init__(self, string_id: int, points: list[tuple[float, float, float]], desc: str = ""):
        self.string_id = string_id
        self.points = points  # (X, Y, Z) list
        self.desc = desc


def read_surpac_str(path: Path | str) -> list[SurpacString]:
    """Read an ASCII Surpac string file (.str).

    Note: Surpac records store Y (Northing) before X (Easting).
    This reader converts them to standard (X, Y, Z).
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    strings_map: dict[int, list[tuple[float, float, float]]] = {}

    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("surpac") or s.startswith("SURPAC"):
            continue
        parts = [p.strip() for p in s.split(",")]
        if len(parts) < 4:
            continue
        try:
            str_id = int(parts[0])
            if str_id == 0:
                continue
            y = float(parts[1])  # Surpac: Northing (Y)
            x = float(parts[2])  # Surpac: Easting (X)
            z = float(parts[3])  # Elevation (Z)
            strings_map.setdefault(str_id, []).append((x, y, z))
        except ValueError:
            continue

    return [SurpacString(sid, pts) for sid, pts in sorted(strings_map.items())]


def write_surpac_str(path: Path | str, strings: list[SurpacString], title: str = "LithoLog Export") -> Path:
    """Write polyline strings to an ASCII Surpac string file (.str).

    Outputs coordinates in Surpac standard order: String, Y (Northing), X (Easting), Z (Elevation).
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"SURPAC STRING FILE, {title}, exported by LithoLog\n",
        "0,     0.000,     0.000,     0.000, , , , \n",
    ]

    for s in strings:
        for pt in s.points:
            x, y = pt[0], pt[1]
            z = pt[2] if len(pt) > 2 else 0.0
            lines.append(f"{s.string_id:4d}, {y:12.3f}, {x:12.3f}, {z:10.3f}, {s.desc}\n")
        # End of segment marker in Surpac string format
        lines.append(f"   0, {y:12.3f}, {x:12.3f}, {z:10.3f}\n")

    lines.append("   0,     0.000,     0.000,     0.000\n")
    p.write_text("".join(lines), encoding="ascii")
    return p


def write_surpac_dtm(
    str_or_dtm_path: Path | str,
    dtm_path_or_verts: Path | str | np.ndarray,
    vertices_or_faces: np.ndarray,
    faces: Optional[np.ndarray] = None,
    string_id: int = 1,
) -> tuple[Path, Path]:
    """Write 3D surface mesh to matching Surpac .str and .dtm files."""
    if faces is None:
        p_dtm = Path(str_or_dtm_path)
        p_str = p_dtm.with_suffix(".str")
        vertices = np.asarray(dtm_path_or_verts)
        faces = np.asarray(vertices_or_faces)
    else:
        p_str = Path(str_or_dtm_path)
        p_dtm = Path(dtm_path_or_verts)
        vertices = np.asarray(vertices_or_faces)
        faces = np.asarray(faces)

    p_str.parent.mkdir(parents=True, exist_ok=True)
    p_dtm.parent.mkdir(parents=True, exist_ok=True)

    # 1. Write String file (.str) with 1-based vertex IDs
    str_lines = [
        "SURPAC STRING FILE, DTM Vertices exported by LithoLog\n",
        "0,     0.000,     0.000,     0.000, , , , \n",
    ]
    for idx, (x, y, z) in enumerate(vertices, 1):
        str_lines.append(f"{string_id:4d}, {y:12.3f}, {x:12.3f}, {z:10.3f}\n")
    str_lines.append("   0,     0.000,     0.000,     0.000\n")
    p_str.write_text("".join(str_lines), encoding="ascii")

    # 2. Write DTM triangulation file (.dtm)
    # Surpac DTM line format: Triangle_ID, Pt1, Pt2, Pt3, String_ID
    dtm_lines = [
        "SURPAC DTM FILE, Surface Triangulation exported by LithoLog\n",
        f"0, {len(vertices)}, {len(faces)}, 0\n",
    ]
    for t_id, (p1, p2, p3) in enumerate(faces, 1):
        # 1-based point index in Surpac
        dtm_lines.append(f"{t_id:6d}, {p1 + 1:6d}, {p2 + 1:6d}, {p3 + 1:6d}, {string_id:4d}\n")
    dtm_lines.append("0, 0, 0, 0, 0\n")
    p_dtm.write_text("".join(dtm_lines), encoding="ascii")

    return p_str, p_dtm


def read_surpac_dtm(
    str_path: Path | str,
    dtm_path: Path | str,
) -> tuple[np.ndarray, np.ndarray]:
    """Read a Surpac DTM surface from matching .str (vertices) and .dtm (triangles) files.

    Parameters
    ----------
    str_path : Path or str
        Path to the .str file containing vertex points.
    dtm_path : Path or str
        Path to the .dtm file containing triangle indices.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        (vertices, faces) where vertices is (N, 3) float array and faces is (M, 3) int array.
    """
    p_str = Path(str_path)
    p_dtm = Path(dtm_path)

    vertices: list[list[float]] = []
    if p_str.exists():
        for line in p_str.read_text(encoding="ascii", errors="replace").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or s.startswith("surpac") or s.startswith("SURPAC"):
                continue
            parts = [p.strip() for p in s.split(",")]
            if len(parts) >= 4:
                try:
                    str_id = int(parts[0])
                    if str_id != 0:
                        y = float(parts[1])
                        x = float(parts[2])
                        z = float(parts[3])
                        vertices.append([x, y, z])
                except (ValueError, IndexError):
                    continue

    faces: list[list[int]] = []
    if p_dtm.exists():
        for line in p_dtm.read_text(encoding="ascii", errors="replace").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or s.startswith("surpac") or s.startswith("SURPAC"):
                continue
            parts = [p.strip() for p in s.split(",")]
            if len(parts) >= 4:
                try:
                    t_id = int(parts[0])
                    if t_id != 0:
                        p1 = int(parts[1]) - 1
                        p2 = int(parts[2]) - 1
                        p3 = int(parts[3]) - 1
                        faces.append([p1, p2, p3])
                except (ValueError, IndexError):
                    continue

    v_arr = np.array(vertices, dtype=float) if vertices else np.empty((0, 3), dtype=float)
    f_arr = np.array(faces, dtype=int) if faces else np.empty((0, 3), dtype=int)
    return v_arr, f_arr
