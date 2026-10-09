import numpy as np
import pandas as pd
import pytest

from litholog import (
    Borehole,
    Project,
    SurpacString,
    composite_assays,
    minimum_curvature,
    read_surpac_str,
    write_surpac_dtm,
    write_surpac_str,
)


def test_minimum_curvature_survey():
    collar_x, collar_y, collar_z = 1000.0, 2000.0, 500.0
    surveys = pd.DataFrame({
        "borehole_id": ["DH-01", "DH-01", "DH-01"],
        "depth": [0.0, 50.0, 100.0],
        "dip": [-60.0, -55.0, -50.0],     # inclined hole, flattening out
        "azimuth": [45.0, 50.0, 55.0],    # turning towards north-east
    })

    stations = minimum_curvature(collar_x, collar_y, collar_z, surveys)
    assert len(stations) == 3

    # Check collar station
    assert stations[0].x == 1000.0
    assert stations[0].y == 2000.0
    assert stations[0].z == 500.0
    assert stations[0].tvd == 0.0

    # At 100m, hole has drilled north-east (X > 1000, Y > 2000) and down (Z < 500)
    end = stations[-1]
    assert end.x > 1000.0
    assert end.y > 2000.0
    assert end.z < 500.0
    # Because dip is ~ -55 to -60 deg, TVD must be less than 100m
    assert 75.0 < end.tvd < 95.0

    # Test Borehole.path integration
    bh = Borehole("DH-01", x=collar_x, y=collar_y, elevation=collar_z, survey=surveys)
    path = bh.path()
    assert path.shape == (3, 3)
    assert np.allclose(path[0], [1000.0, 2000.0, 500.0])

    # Interpolate path at custom depth (e.g. 25m)
    interp_pt = bh.path([25.0])[0]
    assert 1000.0 < interp_pt[0] < end.x
    assert 2000.0 < interp_pt[1] < end.y
    assert end.z < interp_pt[2] < 500.0


def test_assay_compositing():
    assays = pd.DataFrame({
        "borehole_id": ["DDH-10", "DDH-10", "DDH-10"],
        "from": [0.0, 0.8, 1.5],
        "to": [0.8, 1.5, 3.2],
        "Cu": [1.5, 2.0, 0.5],
        "Au": [0.5, 30.0, 0.2],
    })

    # Composite to 1.0m intervals
    # Interval 0 - 1.0:
    # 0 to 0.8: Cu = 1.5 (len 0.8)
    # 0.8 to 1.0: Cu = 2.0 (len 0.2)
    # Weighted Cu = (0.8 * 1.5 + 0.2 * 2.0) / 1.0 = 1.6
    comps = composite_assays(assays, composite_length=1.0, min_length=0.5)
    assert len(comps) == 3
    assert abs(comps.loc[0, "Cu"] - 1.6) < 1e-5
    assert comps.loc[0, "from"] == 0.0 and comps.loc[0, "to"] == 1.0

    # Test top-cut capping on Au (e.g. top cut 10.0 g/t)
    comps_capped = composite_assays(assays, composite_length=1.0, min_length=0.5, top_cuts={"Au": 10.0})
    # For 0-1.0m: Au was 0.5 (len 0.8) and 30.0 capped to 10.0 (len 0.2) -> (0.8 * 0.5 + 0.2 * 10) / 1.0 = 2.4
    assert abs(comps_capped.loc[0, "Au"] - 2.4) < 1e-5


def test_surpac_str_and_dtm_io(tmp_path):
    str_path = tmp_path / "test_strings.str"
    strings_in = [
        SurpacString(1, [(100.0, 200.0, 50.0), (120.0, 220.0, 55.0)], "Pit Crest"),
        SurpacString(2, [(105.0, 205.0, 40.0), (125.0, 225.0, 42.0)], "Pit Toe"),
    ]

    write_surpac_str(str_path, strings_in, title="Test Pit")
    assert str_path.exists()

    strings_out = read_surpac_str(str_path)
    assert len(strings_out) == 2
    assert strings_out[0].string_id == 1
    assert len(strings_out[0].points) == 2
    assert strings_out[0].points[0] == (100.0, 200.0, 50.0)

    # Test DTM surface write
    dtm_str = tmp_path / "surface.str"
    dtm_file = tmp_path / "surface.dtm"
    verts = np.array([
        [0.0, 0.0, 10.0],
        [10.0, 0.0, 12.0],
        [10.0, 10.0, 15.0],
        [0.0, 10.0, 11.0],
    ])
    faces = np.array([
        [0, 1, 2],
        [0, 2, 3],
    ])

    write_surpac_dtm(dtm_str, dtm_file, verts, faces)
    assert dtm_str.exists()
    assert dtm_file.exists()
    dtm_text = dtm_file.read_text(encoding="ascii")
    assert "SURPAC DTM FILE" in dtm_text
    assert "0, 4, 2, 0" in dtm_text
