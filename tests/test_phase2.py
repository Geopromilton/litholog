from pathlib import Path
import pandas as pd
import pytest

from litholog import (
    Project,
    charge_balance_error,
    classify_uscs,
    correct_spt_n,
    piper_figure,
    read_las,
    rqd_quality,
    save_piper,
    save_striplog,
    stiff_figure,
    to_meq,
    water_type,
)
from litholog.cli import main
from litholog.patterns import Legend


def test_uscs_classification():
    # Coarse-grained: Gravels
    gw = classify_uscs(gravel_pct=60, sand_pct=36, fines_pct=4, cu=5.0, cc=2.0)
    assert gw.code == "GW"
    assert "Well-graded" in gw.name

    gp = classify_uscs(gravel_pct=70, sand_pct=26, fines_pct=4, cu=2.0, cc=0.5)
    assert gp.code == "GP"

    # Coarse-grained: Sands
    sw = classify_uscs(gravel_pct=15, sand_pct=82, fines_pct=3, cu=7.0, cc=1.5)
    assert sw.code == "SW"

    sp = classify_uscs(gravel_pct=10, sand_pct=87, fines_pct=3, cu=3.0, cc=0.8)
    assert sp.code == "SP"

    # Fine-grained: Clays and Silts
    cl = classify_uscs(gravel_pct=5, sand_pct=15, fines_pct=80, ll=38, pi=18)
    assert cl.code == "CL"

    ch = classify_uscs(gravel_pct=0, sand_pct=10, fines_pct=90, ll=65, pi=38)
    assert ch.code == "CH"

    ml = classify_uscs(gravel_pct=5, sand_pct=15, fines_pct=80, ll=35, pi=8)
    assert ml.code == "ML"

    mh = classify_uscs(gravel_pct=2, sand_pct=8, fines_pct=90, ll=60, pi=22)
    assert mh.code == "MH"

    # Dual CL-ML (Casagrande hatch zone)
    cl_ml = classify_uscs(gravel_pct=0, sand_pct=10, fines_pct=90, ll=26, pi=5.5)
    assert cl_ml.code == "CL-ML"


def test_spt_and_rqd():
    n60 = correct_spt_n(raw_n=24, energy_ratio=60, rod_length_m=12, borehole_dia_mm=150)
    assert 20 <= n60 <= 26

    qual, col = rqd_quality(82)
    assert qual == "Good"
    assert col == "#5CB85C"

    qual_bad, _ = rqd_quality(20)
    assert qual_bad == "Very Poor"


def test_hydrochem_calculations_and_piper(tmp_path):
    # Balanced potable water sample
    df = pd.DataFrame([{
        "borehole_id": "BH-WQ1",
        "ca": 65.0,    # ~3.24 meq/L
        "mg": 18.0,    # ~1.48 meq/L
        "na": 25.0,    # ~1.09 meq/L
        "k": 3.5,      # ~0.09 meq/L
        "cl": 32.0,    # ~0.90 meq/L
        "so4": 45.0,   # ~0.94 meq/L
        "hco3": 240.0, # ~3.93 meq/L
        "co3": 0.0,
        "no3": 5.0,    # ~0.08 meq/L
    }, {
        "borehole_id": "BH-WQ2",
        "ca": 20.0,
        "mg": 8.0,
        "na": 95.0,
        "k": 6.0,
        "cl": 120.0,
        "so4": 60.0,
        "hco3": 85.0,
        "co3": 0.0,
        "no3": 2.0,
    }])

    meq = to_meq(df)
    assert "ca_meq" in meq.columns
    assert "cl_meq" in meq.columns
    assert meq.loc[0, "ca_meq"] > 3.0

    cbe = charge_balance_error(df)
    assert abs(cbe[0]) < 10.0  # reasonable charge balance error

    w_facies = water_type(df.iloc[0])
    assert "Ca" in w_facies
    assert "HCO3" in w_facies

    # Piper plot figure
    fig = piper_figure(df)
    piper_out = tmp_path / "test_piper.png"
    fig.savefig(piper_out)
    assert piper_out.exists()

    # Stiff diagram
    fig_stiff = stiff_figure(df.iloc[0])
    stiff_out = tmp_path / "test_stiff.png"
    fig_stiff.savefig(stiff_out)
    assert stiff_out.exists()


def test_las_parser(tmp_path):
    las_text = """~VERSION INFORMATION
 VERS.                          2.0 :   CWLS LOG ASCII STANDARD -VERSION 2.0
 WRAP.                           NO :   ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT .M                       10.0 :   START DEPTH
 STOP .M                       13.0 :   STOP DEPTH
 STEP .M                        1.0 :   STEP
 NULL .                     -999.25 :   NULL VALUE
 COMP .                     GEO-CORP:   COMPANY
 WELL .                        BH-01:   WELL NAME
~CURVE INFORMATION
 DEPT .M                            :   Depth
 GR   .GAPI                     GAMMA:  Gamma Ray
 RES  .OHMM               RESISTIVITY:  Resistivity
~A  DEPTH     GR    RES
    10.0    45.2   12.4
    11.0    52.1   14.2
    12.0    68.5   22.0
    13.0   -999.25 18.5
"""
    las_file = tmp_path / "test.las"
    las_file.write_text(las_text)

    parsed = read_las(las_file)
    assert parsed.well_name == "BH-01"
    assert len(parsed.curves) == 3
    assert len(parsed.data) == 4

    dh_table = parsed.to_downhole_table()
    assert "borehole_id" in dh_table.columns
    assert "parameter" in dh_table.columns
    assert "value" in dh_table.columns
    # Null value at 13.0 for GR should be filtered out
    gr_rows = dh_table[dh_table["parameter"] == "GR"]
    assert len(gr_rows) == 3


def test_geotech_strip_log(tmp_path):
    bh_df = pd.DataFrame({"borehole_id": ["GT-01"], "x": [100.0], "y": [200.0], "elevation": [50.0], "total_depth": [25.0]})
    lith_df = pd.DataFrame({
        "borehole_id": ["GT-01", "GT-01"],
        "from": [0.0, 5.0],
        "to": [5.0, 25.0],
        "code": ["SAND", "GRA"],
        "description": ["Loose sand", "Massive granite"],
    })
    gt_df = pd.DataFrame({
        "borehole_id": ["GT-01", "GT-01", "GT-01"],
        "from": [1.0, 3.0, 6.0],
        "to": [1.5, 3.5, 10.0],
        "spt_n": [12, 28, 55],
        "n60": [14, 30, 58],
        "rqd": [0, 0, 85],
        "recovery": [60, 80, 95],
        "weathering": ["W1", "W2", "W4"],
    })

    tables = {
        "boreholes": bh_df,
        "lithology": lith_df,
        "construction": pd.DataFrame(columns=["borehole_id", "from", "to", "element", "diameter", "material"]),
        "water_levels": pd.DataFrame(columns=["borehole_id", "date", "depth"]),
        "downhole": pd.DataFrame(columns=["borehole_id", "depth", "parameter", "value", "unit"]),
        "geotech": gt_df,
        "water_quality": pd.DataFrame(columns=["borehole_id", "date", "ca", "mg", "na", "k", "cl", "so4", "hco3", "co3", "no3", "ph", "tds", "ec"]),
    }
    proj = Project(**tables, legend=Legend())
    bh = proj.borehole("GT-01")
    assert len(bh.geotech) == 3

    out_pdf = tmp_path / "geotech_log.pdf"
    res = save_striplog(bh, proj.legend, out_pdf)
    assert res[0].exists()
    assert res[0].stat().st_size > 10000
