import numpy as np
import pandas as pd
import pytest

from litholog import (
    Grid,
    Project,
    SearchEllipsoid,
    build_grade_model,
    calculate_cut_fill,
    idw_3d,
    ordinary_kriging_3d,
)
from litholog.patterns import Legend


def test_search_ellipsoid_and_3d_idw():
    # Ellipsoid oriented along striking 45 deg, dipping 30 deg
    ell = SearchEllipsoid(major_range=100.0, semi_major_range=50.0, minor_range=20.0, azimuth=45.0, dip=30.0)
    rot = ell.rotation_matrix()
    assert rot.shape == (3, 3)
    # Check that rotation matrix is orthogonal (R @ R.T = I)
    assert np.allclose(rot @ rot.T, np.eye(3), atol=1e-5)

    # Test 3D IDW
    pts = np.array([
        [0.0, 0.0, 0.0],
        [10.0, 0.0, 0.0],
        [0.0, 10.0, 0.0],
    ])
    vals = np.array([1.0, 2.0, 3.0])
    target = np.array([5.0, 0.0, 0.0])

    est = idw_3d(pts, vals, target, power=2.0)
    # Between 1.0 and 2.0, closer to 1 and 2
    assert 1.0 < est < 2.0


def test_3d_ordinary_kriging():
    pts = np.array([
        [0.0, 0.0, 0.0],
        [10.0, 0.0, 0.0],
        [0.0, 10.0, 0.0],
        [0.0, 0.0, 10.0],
    ])
    vals = np.array([1.5, 2.5, 3.5, 4.5])
    target = np.array([5.0, 5.0, 5.0])

    est, var = ordinary_kriging_3d(pts, vals, target, nugget=0.1, sill=1.0, range_val=50.0)
    assert 1.5 <= est <= 4.5
    assert var >= 0.0


def test_grade_block_model_and_grade_tonnage(tmp_path):
    # Two drillholes with assayed intervals
    bh_df = pd.DataFrame({
        "borehole_id": ["DH-1", "DH-2"],
        "x": [100.0, 150.0],
        "y": [200.0, 200.0],
        "elevation": [100.0, 100.0],
        "total_depth": [50.0, 50.0],
    })
    assays_df = pd.DataFrame({
        "borehole_id": ["DH-1", "DH-1", "DH-2", "DH-2"],
        "from": [0.0, 20.0, 0.0, 20.0],
        "to": [20.0, 50.0, 20.0, 50.0],
        "Cu": [0.5, 2.2, 0.4, 1.8],
        "Au": [0.1, 1.2, 0.1, 0.9],
    })

    tables = {
        "boreholes": bh_df,
        "lithology": pd.DataFrame(columns=["borehole_id", "from", "to", "code", "description"]),
        "construction": pd.DataFrame(columns=["borehole_id", "from", "to", "element", "diameter", "material"]),
        "water_levels": pd.DataFrame(columns=["borehole_id", "date", "depth"]),
        "downhole": pd.DataFrame(columns=["borehole_id", "depth", "parameter", "value", "unit"]),
        "geotech": pd.DataFrame(columns=["borehole_id", "from", "to", "spt_n", "n60", "rqd", "recovery", "weathering"]),
        "water_quality": pd.DataFrame(columns=["borehole_id", "date", "ca", "mg", "na", "k", "cl", "so4", "hco3", "co3", "no3", "ph", "tds", "ec"]),
        "survey": pd.DataFrame(columns=["borehole_id", "depth", "dip", "azimuth"]),
        "assays": assays_df,
    }
    proj = Project(**tables, legend=Legend())

    model = build_grade_model(proj, elements=["Cu", "Au"], cell=25.0, dz=10.0, default_density=2.7)
    assert model.mask.sum() > 0
    assert "Cu" in model.grades
    assert "Au" in model.grades

    # Compute Grade-Tonnage curve
    gt_df = model.grade_tonnage(cutoffs=[0.0, 0.3, 0.6, 1.0], element="Cu")
    assert len(gt_df) == 4
    # Higher cutoff -> lower or equal ore tonnes
    assert gt_df.loc[0, "ore_tonnes"] >= gt_df.loc[1, "ore_tonnes"] >= gt_df.loc[2, "ore_tonnes"]
    # Higher cutoff -> higher or equal average grade on non-empty cutoffs
    non_zero = gt_df[gt_df["ore_blocks"] > 0]
    assert non_zero.iloc[-1]["avg_grade"] >= non_zero.iloc[0]["avg_grade"]

    csv_path = tmp_path / "blocks.csv"
    model.write_csv(csv_path, element="Cu")
    assert csv_path.exists()


def test_cut_and_fill_earthworks():
    x = np.arange(0, 100, 10.0)
    y = np.arange(0, 100, 10.0)
    # Original natural topography: flat at 50 m
    z1 = np.full((len(y), len(x)), 50.0)
    # Design pit surface: excavated to 40 m
    z2 = np.full((len(y), len(x)), 40.0)

    g1 = Grid(x, y, z1, cell=10.0)
    g2 = Grid(x, y, z2, cell=10.0)

    vol = calculate_cut_fill(g1, g2, density=2.5)
    # 10m cut over 100 cells * 100 m2/cell = 10,000 m2 * 10m = 100,000 m3
    assert abs(vol.cut_volume_m3 - 100000.0) < 1e-4
    assert vol.fill_volume_m3 == 0.0
    assert vol.net_volume_m3 == 100000.0
    assert vol.cut_tonnes == 250000.0
    assert vol.max_cut_depth_m == 10.0
