"""3D Multi-Attribute Grade Block Modeling & Mineral Resource Estimation.

Implements Surpac-style 3D regular block models carrying bulk density
and multiple grade variables, with Grade-Tonnage curves and resource reporting.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from .assay import composite_assays
from .geostat import SearchEllipsoid, idw_3d
from .project import Project


@dataclass
class GradeBlockModel:
    """3D regular block model with grade attributes and resource evaluation."""
    x: np.ndarray       # Cell centres X (nx,)
    y: np.ndarray       # Cell centres Y (ny,)
    z: np.ndarray       # Cell centres Z (nz,)
    cell: float         # Horizontal block size (m)
    dz: float           # Vertical block size (m)
    grades: dict[str, np.ndarray]  # element -> (nz, ny, nx) float array
    density: np.ndarray            # (nz, ny, nx) bulk density in t/m3
    mask: np.ndarray               # (nz, ny, nx) True where block is valid

    @property
    def block_volume(self) -> float:
        return float(self.cell * self.cell * self.dz)

    def grade_tonnage(
        self,
        cutoffs: list[float] | np.ndarray,
        element: str,
        unit: str = "%",
    ) -> pd.DataFrame:
        """Compute Mineral Resource Grade-Tonnage curve across cut-off grades.

        Parameters
        ----------
        cutoffs : list of float
            Series of cutoff grades (e.g. [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]).
        element : str
            Grade variable name (e.g. 'Cu', 'Au').
        unit : str, default '%'
            '%' (percent) or 'g/t' (grams per tonne / ppm).
        """
        if element not in self.grades:
            raise KeyError(f"Element '{element}' not in block model (available: {list(self.grades.keys())})")

        g_arr = self.grades[element]
        d_arr = self.density
        valid = self.mask & np.isfinite(g_arr) & (g_arr >= 0)

        total_blocks = int(valid.sum())
        total_vol = total_blocks * self.block_volume
        total_tonnes = float(np.sum(d_arr[valid] * self.block_volume))

        rows = []
        for co in sorted(cutoffs):
            ore_mask = valid & (g_arr >= co)
            n_ore = int(ore_mask.sum())
            if n_ore == 0:
                rows.append({
                    "cutoff": co,
                    "ore_blocks": 0,
                    "ore_volume_m3": 0.0,
                    "ore_tonnes": 0.0,
                    "avg_grade": 0.0,
                    "metal_content": 0.0,
                    "unit": unit,
                    "waste_tonnes": total_tonnes,
                })
                continue

            v_ore = n_ore * self.block_volume
            tonnes_arr = d_arr[ore_mask] * self.block_volume
            ore_tonnes = float(np.sum(tonnes_arr))
            avg_g = float(np.sum(tonnes_arr * g_arr[ore_mask]) / ore_tonnes) if ore_tonnes > 0 else 0.0

            # Metal content calculation
            if unit == "%":
                metal = ore_tonnes * (avg_g / 100.0)  # metal in tonnes
            else:
                metal = ore_tonnes * avg_g / 1000.0   # kg of metal for g/t

            rows.append({
                "cutoff": co,
                "ore_blocks": n_ore,
                "ore_volume_m3": v_ore,
                "ore_tonnes": ore_tonnes,
                "avg_grade": avg_g,
                "metal_content": metal,
                "unit": unit,
                "waste_tonnes": total_tonnes - ore_tonnes,
            })

        return pd.DataFrame(rows)

    def write_csv(self, path: Path | str, element: str = "Cu") -> Path:
        """Export block model centroids and attributes to CSV."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        valid = self.mask & np.isfinite(self.grades.get(element, self.density))
        ks, js, is_ = np.nonzero(valid)

        rows = []
        for k, j, i in zip(ks, js, is_):
            r = {
                "x": self.x[i],
                "y": self.y[j],
                "z": self.z[k],
                "density": float(self.density[k, j, i]),
            }
            for elem, arr in self.grades.items():
                r[elem] = float(arr[k, j, i])
            rows.append(r)

        pd.DataFrame(rows).to_csv(p, index=False)
        return p


class BlockItem:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z
        self.attributes = {}

class SimpleBlockModel:
    def __init__(self, blocks):
        self.blocks = blocks
    def to_dataframe(self):
        rows = []
        for b in self.blocks:
            r = {"x": b.x, "y": b.y, "z": b.z}
            r.update(b.attributes)
            rows.append(r)
        return pd.DataFrame(rows)

def build_grade_model(
    project: Optional[Project] = None,
    elements: Optional[list[str]] = None,
    cell: float = 50.0,
    dz: float = 5.0,
    power: float = 2.0,
    default_density: float = 2.7,
    composite_len: float = 1.0,
    ellipsoid: Optional[SearchEllipsoid] = None,
    origin: Optional[tuple[float, float, float]] = None,
    **kwargs,
):
    """Build a 3D grade block model by compositing assays and interpolating via 3D IDW."""
    if origin is not None:
        ox, oy, oz = origin
        ex, ey, ez = kwargs.get("extent", (100.0, 100.0, 50.0))
        bs = kwargs.get("block_size", (cell, cell, dz))
        bx, by, bz = bs
        nx = max(1, int(ex / bx))
        ny = max(1, int(ey / by))
        nz = max(1, int(ez / bz))
        blocks = []
        for k in range(nz):
            for j in range(ny):
                for i in range(nx):
                    blocks.append(BlockItem(ox + (i + 0.5) * bx, oy + (j + 0.5) * by, oz + (k + 0.5) * bz))
        return SimpleBlockModel(blocks)

    elements = elements or []
    # 1. Collect and composite assay points in 3D
    sample_pts = []
    sample_vals: dict[str, list[float]] = {e: [] for e in elements}

    for bh in project:
        if not len(bh.assays) or pd.isna(bh.x) or pd.isna(bh.y):
            continue
        comps = composite_assays(bh.assays, composite_length=composite_len, elements=elements)
        if comps.empty:
            continue
        # True 3D path coordinates at composite midpoints
        pts_3d = bh.path(comps["mid"].values)
        for idx, (_, r) in enumerate(comps.iterrows()):
            sample_pts.append(pts_3d[idx])
            for elem in elements:
                sample_vals[elem].append(float(r[elem]) if pd.notna(r[elem]) else np.nan)

    if not sample_pts:
        raise ValueError("No assayed drillholes found in project")

    all_pts = np.array(sample_pts)
    x_min, x_max = float(all_pts[:, 0].min()), float(all_pts[:, 0].max())
    y_min, y_max = float(all_pts[:, 1].min()), float(all_pts[:, 1].max())
    z_min, z_max = float(all_pts[:, 2].min()), float(all_pts[:, 2].max())

    pad = 2.0 * cell
    gx = np.arange(x_min - pad, x_max + pad + cell, cell)
    gy = np.arange(y_min - pad, y_max + pad + cell, cell)
    gz = np.arange(z_min - pad, z_max + pad + dz, dz)

    nz, ny, nx = len(gz), len(gy), len(gx)
    grade_grids = {e: np.full((nz, ny, nx), np.nan, dtype=np.float32) for e in elements}
    density_grid = np.full((nz, ny, nx), default_density, dtype=np.float32)
    mask = np.zeros((nz, ny, nx), dtype=bool)

    # 3D Grid interpolation
    for k, z in enumerate(gz):
        for j, y in enumerate(gy):
            for i, x in enumerate(gx):
                target = np.array([x, y, z])
                for elem in elements:
                    v_arr = np.array(sample_vals[elem])
                    valid = np.isfinite(v_arr)
                    if valid.sum() == 0:
                        continue
                    est = idw_3d(all_pts[valid], v_arr[valid], target, ellipsoid=ellipsoid, power=power)
                    grade_grids[elem][k, j, i] = est
                    if np.isfinite(est):
                        mask[k, j, i] = True

    return GradeBlockModel(gx, gy, gz, cell, dz, grade_grids, density_grid, mask)
