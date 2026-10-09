"""Exact-answer checks for the numerical routines (no sample data needed)."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from litholog import Grid, calculate_cut_fill, charge_balance_error, correct_spt_n, minimum_curvature


def _stations(depths, dips, azis, collar=(0.0, 0.0, 100.0)):
    df = pd.DataFrame({"depth": depths, "dip": dips, "azimuth": azis})
    return minimum_curvature(*collar, df)


def test_minimum_curvature_vertical_hole():
    st = _stations([0.0, 100.0], [-90.0, -90.0], [0.0, 0.0])
    assert st[-1].tvd == pytest.approx(100.0)
    assert st[-1].x == pytest.approx(0.0, abs=1e-9)
    assert st[-1].y == pytest.approx(0.0, abs=1e-9)
    assert st[-1].z == pytest.approx(0.0)


def test_minimum_curvature_straight_inclined_hole():
    """45 degrees below horizontal, due east: equal horizontal and vertical offsets."""
    st = _stations([0.0, 100.0], [-45.0, -45.0], [90.0, 90.0])
    assert st[-1].x == pytest.approx(100 * math.sqrt(0.5))
    assert st[-1].y == pytest.approx(0.0, abs=1e-9)
    assert st[-1].tvd == pytest.approx(100 * math.sqrt(0.5))


def test_minimum_curvature_circular_arc_is_exact():
    """Vertical to horizontal along a circular arc of radius R: the method is exact for arcs."""
    radius = 200.0
    length = math.pi * radius / 2.0
    st = _stations([0.0, length], [-90.0, 0.0], [90.0, 90.0])
    assert st[-1].x == pytest.approx(radius, rel=1e-9)
    assert st[-1].tvd == pytest.approx(radius, rel=1e-9)


def test_charge_balance_error_exact_values():
    # 1 meq/L of Ca (20.039 mg/L) against 1 meq/L of Cl (35.453 mg/L) balances exactly
    balanced = pd.DataFrame({"ca": [20.039], "cl": [35.453]})
    assert charge_balance_error(balanced)[0] == pytest.approx(0.0, abs=1e-9)
    # 2 meq/L cations against 1 meq/L anions: (2 - 1) / (2 + 1) = 33.33 %
    skewed = pd.DataFrame({"ca": [2 * 20.039], "cl": [35.453]})
    assert charge_balance_error(skewed)[0] == pytest.approx(100.0 / 3.0)


def _grid(value, n=10, cell=5.0):
    x = (np.arange(n) + 0.5) * cell
    return Grid(x=x, y=x.copy(), z=np.full((n, n), float(value)), cell=cell)


def test_cut_and_fill_volumes():
    original = _grid(10.0)
    lowered = _grid(9.0)        # 1 m cut over 10 x 10 cells of 25 m2
    r = calculate_cut_fill(original, lowered, density=2.0)
    assert r.cut_volume_m3 == pytest.approx(2500.0)
    assert r.fill_volume_m3 == 0.0
    assert r.cut_tonnes == pytest.approx(5000.0)
    assert r.area_m2 == pytest.approx(2500.0)
    raised = calculate_cut_fill(original, _grid(12.0))
    assert raised.fill_volume_m3 == pytest.approx(5000.0)
    assert raised.net_volume_m3 == pytest.approx(-5000.0)


# --- SPT correction (Skempton 1986; Youd et al. 2001; Liao and Whitman 1986) ---------

def test_spt_energy_ratio_is_applied():
    n60 = correct_spt_n(raw_n=24, energy_ratio=45, rod_length_m=12, borehole_dia_mm=150)
    assert float(n60) == pytest.approx(24 * 45 / 60 * 1.05 * 1.0 * 1.0, abs=0.1)


def test_spt_rod_length_and_diameter_factors():
    # C_R: <4 m 0.75, 4-6 m 0.85, 6-10 m 0.95, >=10 m 1.0 ; C_B: <=115 mm 1.0, 150 mm 1.05, 200 mm 1.15
    assert float(correct_spt_n(20, rod_length_m=3, borehole_dia_mm=100)) == pytest.approx(15.0, abs=0.05)
    assert float(correct_spt_n(20, rod_length_m=5, borehole_dia_mm=100)) == pytest.approx(17.0, abs=0.05)
    assert float(correct_spt_n(20, rod_length_m=8, borehole_dia_mm=100)) == pytest.approx(19.0, abs=0.05)
    assert float(correct_spt_n(20, rod_length_m=12, borehole_dia_mm=100)) == pytest.approx(20.0, abs=0.05)
    assert float(correct_spt_n(20, rod_length_m=12, borehole_dia_mm=200)) == pytest.approx(23.0, abs=0.05)
    assert float(correct_spt_n(20, rod_length_m=12, sampler="no_liner")) == pytest.approx(20 * 1.05 * 1.2, abs=0.1)


def test_spt_overburden_normalisation():
    r = correct_spt_n(20, rod_length_m=12, borehole_dia_mm=100, effective_overburden_kpa=100.0)
    assert r.n1_60 == pytest.approx(r.n_60, abs=0.05)          # sigma'v = Pa -> C_N = 1
    r4 = correct_spt_n(20, rod_length_m=12, borehole_dia_mm=100, effective_overburden_kpa=25.0)
    assert r4.n1_60 == pytest.approx(r4.n_60 * 2.0, abs=0.1)   # sqrt(100/25) = 2
    assert r4["sigma_v_kpa"] == 25.0


def test_spt_depth_changes_result():
    assert float(correct_spt_n(24, rod_length_m=5.0)) != float(correct_spt_n(24, rod_length_m=15.0))
