"""Cut & Fill Earthworks and Surface-to-Surface Volumetrics.

Computes cut, fill, and net earthwork volumes and tonnages between
topographic and excavation surfaces (DTMs / Grids).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from .grid import Grid


@dataclass
class EarthworkVolume:
    cut_volume_m3: float
    fill_volume_m3: float
    net_volume_m3: float
    cut_tonnes: float
    fill_tonnes: float
    net_tonnes: float
    area_m2: float
    max_cut_depth_m: float
    max_fill_height_m: float
    cut_area_m2: float = 0.0
    fill_area_m2: float = 0.0


def calculate_cut_fill(
    original_grid: Grid,
    design_grid: Grid,
    density: float = 2.0,
    boundary=None,
    cell_size: Optional[float] = None,
) -> EarthworkVolume:
    """Calculate cut, fill, and net earthwork volumes between two digital elevation grids.

    Parameters
    ----------
    original_grid : Grid
        Pre-excavation / natural topography grid (Z1).
    design_grid : Grid
        Post-excavation / pit / fill design surface grid (Z2).
    density : float, default 2.0
        Material bulk density in tonnes / m3.
    boundary : Boundary, optional
        Optional polygon boundary to restrict calculation to.
    """
    z1 = original_grid.z if hasattr(original_grid, "z") else np.asarray(original_grid)
    z2 = design_grid.z if hasattr(design_grid, "z") else np.asarray(design_grid)
    if z1.shape != z2.shape:
        raise ValueError("Original and Design grids must have identical dimensions and cell sizes")

    c = getattr(original_grid, "cell", cell_size or 5.0)
    cell_area = c * c

    valid = np.isfinite(z1) & np.isfinite(z2)
    if boundary is not None:
        mask = boundary.mask(original_grid.x, original_grid.y)
        valid &= mask

    diff = z1[valid] - z2[valid]  # Positive = Cut, Negative = Fill

    cut_mask = diff > 0
    fill_mask = diff < 0

    cut_depths = diff[cut_mask]
    fill_heights = -diff[fill_mask]

    cut_vol = float(np.sum(cut_depths) * cell_area) if len(cut_depths) else 0.0
    fill_vol = float(np.sum(fill_heights) * cell_area) if len(fill_heights) else 0.0
    net_vol = cut_vol - fill_vol

    active_area = float(valid.sum() * cell_area)
    max_cut = float(cut_depths.max()) if len(cut_depths) else 0.0
    max_fill = float(fill_heights.max()) if len(fill_heights) else 0.0

    cut_area = float(cut_mask.sum() * cell_area)
    fill_area = float(fill_mask.sum() * cell_area)

    return EarthworkVolume(
        cut_volume_m3=cut_vol,
        fill_volume_m3=fill_vol,
        net_volume_m3=net_vol,
        cut_tonnes=cut_vol * density,
        fill_tonnes=fill_vol * density,
        net_tonnes=net_vol * density,
        area_m2=active_area,
        max_cut_depth_m=max_cut,
        max_fill_height_m=max_fill,
        cut_area_m2=cut_area,
        fill_area_m2=fill_area,
    )
