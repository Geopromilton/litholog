"""LithoLog -> OpenHydro Studio import files."""
from __future__ import annotations

import pandas as pd
import pytest

from litholog import load_project
from litholog.cli import main
from litholog.openhydro import export_openhydro, parse_layer_option, soundings_table, observation_wells_table


def _project(tmp_path):
    p = tmp_path / "p.xlsx"
    with pd.ExcelWriter(p) as xw:
        pd.DataFrame({"Borehole ID": ["A", "B", "C"], "X": [100.0, 200.0, 300.0], "Y": [10.0, 20.0, 30.0],
                      "Elevation": [100.0, 98.0, 95.0], "Total depth": [50.0, 30.0, 12.0]}
                     ).to_excel(xw, sheet_name="Boreholes", index=False)
        pd.DataFrame({
            "BH": ["A", "A", "A", "B", "B", "C", "C"],
            "From": [0, 5, 20, 0, 3, 0, 4],
            "To": [5, 20, 50, 3, 30, 4, 12],
            "Code": ["SOIL", "CLAY", "GRN", "SOIL", "GRN", "SOIL", "CLAY"],
        }).to_excel(xw, sheet_name="Lithology", index=False)
        pd.DataFrame({"BH": ["A", "A", "B"], "Date": ["2025-01-10", "2025-06-10", "2025-06-10"],
                      "Depth to water (m bgl)": [8.0, 6.0, 5.0]}
                     ).to_excel(xw, sheet_name="WaterLevels", index=False)
    return load_project(p)


LAYERS = {"Soil": ["SOIL"], "Clay": ["CLAY"], "Granite": ["GRN"]}


def test_layer_bases_pinch_out_and_not_reached(tmp_path):
    t = soundings_table(_project(tmp_path), LAYERS).set_index("station_id")
    assert list(t.columns[3:6]) == ["soil_base_depth_m", "clay_base_depth_m", "granite_base_depth_m"]
    assert t.loc["A", ["soil_base_depth_m", "clay_base_depth_m", "granite_base_depth_m"]].tolist() == [5, 20, 50]
    # B has no clay: zero-thickness pinch-out (clay base = soil base)
    assert t.loc["B", ["soil_base_depth_m", "clay_base_depth_m", "granite_base_depth_m"]].tolist() == [3, 3, 30]
    # C ends in clay: granite not reached
    assert t.loc["C", "clay_base_depth_m"] == 12
    assert pd.isna(t.loc["C", "granite_base_depth_m"])
    assert t.loc["A", "elevation_m"] == 100.0


def test_automatic_layers_follow_depth_order(tmp_path):
    t = soundings_table(_project(tmp_path))
    codes_in_order = [c.replace("_base_depth_m", "") for c in t.columns if c.endswith("_base_depth_m")]
    assert len(codes_in_order) == 3
    assert codes_in_order[0].startswith("soil") or "soil" in codes_in_order[0]


def test_observation_wells_statistics(tmp_path):
    prj = _project(tmp_path)
    w = observation_wells_table(prj, "latest").set_index("well_id")
    assert w.loc["A", "dtw_m"] == 6.0 and w.loc["B", "dtw_m"] == 5.0
    assert observation_wells_table(prj, "mean").set_index("well_id").loc["A", "dtw_m"] == 7.0
    assert "layer" not in w.columns            # let OpenHydro place the well from its depth


def test_cli_and_layer_option(tmp_path):
    prj = tmp_path / "p.xlsx"
    _project(tmp_path)
    assert parse_layer_option("Soil=SOIL;Rock=CLAY,GRN") == {"Soil": ["SOIL"], "Rock": ["CLAY", "GRN"]}
    with pytest.raises(ValueError):
        parse_layer_option("Soil")
    assert main(["openhydro", str(prj), "-o", str(tmp_path / "oh"), "--layers", "Soil=SOIL;Rock=CLAY,GRN"]) == 0
    s = pd.read_csv(tmp_path / "oh" / "litholog_soundings.csv")
    assert s.loc[s.station_id == "A", "rock_base_depth_m"].iloc[0] == 50
    assert (tmp_path / "oh" / "litholog_observation_wells.csv").exists()
