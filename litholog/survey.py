"""3D Borehole Survey Deviation & Minimum Curvature Trajectory.

Calculates true 3D coordinates (X Easting, Y Northing, Z Elevation / TVD)
along curved/deviated borehole paths using the industry-standard
Minimum Curvature Method (SPE / API standard, identical to GEOVIA Surpac).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


@dataclass
class SurveyStation:
    depth: float     # Measured depth (m)
    dip: float       # Dip angle in degrees (-90 = vertical down, 0 = horizontal)
    azimuth: float   # Azimuth angle in degrees (0 - 360 clockwise from North)
    x: float         # Easting (m)
    y: float         # Northing (m)
    z: float         # Elevation (m amsl)
    tvd: float       # True vertical depth below collar (m)


def minimum_curvature(
    collar_x: float,
    collar_y: float,
    collar_z: float,
    surveys: pd.DataFrame,
) -> list[SurveyStation]:
    """Calculate 3D trajectory stations from survey measurements.

    Parameters
    ----------
    collar_x, collar_y, collar_z : float
        Coordinates of the borehole collar.
    surveys : pd.DataFrame
        Table with columns: depth (or md), dip (degrees), azimuth (degrees).
        Dip convention: -90 = straight down, 0 = horizontal, +90 = straight up.
    """
    if surveys.empty:
        return [SurveyStation(0.0, -90.0, 0.0, collar_x, collar_y, collar_z, 0.0)]

    s = surveys.sort_values("depth").dropna(subset=["depth", "dip", "azimuth"]).copy()
    if s.empty:
        return [SurveyStation(0.0, -90.0, 0.0, collar_x, collar_y, collar_z, 0.0)]

    # Ensure collar station at depth 0
    stations = []
    first = s.iloc[0]
    cur_x, cur_y, cur_z = collar_x, collar_y, collar_z
    cur_md = 0.0
    cur_dip = float(first["dip"])
    cur_azi = float(first["azimuth"])
    stations.append(SurveyStation(0.0, cur_dip, cur_azi, cur_x, cur_y, cur_z, 0.0))

    for _, row in s.iterrows():
        next_md = float(row["depth"])
        next_dip = float(row["dip"])
        next_azi = float(row["azimuth"])
        d_md = next_md - cur_md
        if d_md <= 0:
            continue

        # In inclination convention: theta = 90 - dip (0 = down, 90 = horizontal)
        # Here: dip -90 is straight down. Let inclination i = (90 + dip) in degrees (0 = down).
        # We compute using standard directional drilling formula where:
        # I1, I2 are inclinations from vertical (radians, 0 = straight down).
        i1 = math.radians(abs(cur_dip + 90.0))  # 0 when dip = -90
        i2 = math.radians(abs(next_dip + 90.0))  # 0 when dip = -90
        a1 = math.radians(cur_azi)
        a2 = math.radians(next_azi)

        # Dogleg angle beta
        cos_beta = math.cos(i2 - i1) - math.sin(i1) * math.sin(i2) * (1.0 - math.cos(a2 - a1))
        cos_beta = max(-1.0, min(1.0, cos_beta))
        beta = math.acos(cos_beta)

        # Ratio Factor RF
        if abs(beta) < 1e-6:
            rf = 1.0
        else:
            rf = (2.0 / beta) * math.tan(beta / 2.0)

        # Displacements
        dx = (d_md / 2.0) * (math.sin(i1) * math.sin(a1) + math.sin(i2) * math.sin(a2)) * rf
        dy = (d_md / 2.0) * (math.sin(i1) * math.cos(a1) + math.sin(i2) * math.cos(a2)) * rf
        # dz is vertical downward (TVD increment)
        dtvd = (d_md / 2.0) * (math.cos(i1) + math.cos(i2)) * rf

        cur_x += dx
        cur_y += dy
        cur_z -= dtvd  # Elevation decreases as depth increases
        cur_md = next_md
        cur_dip = next_dip
        cur_azi = next_azi

        stations.append(SurveyStation(cur_md, cur_dip, cur_azi, cur_x, cur_y, cur_z, collar_z - cur_z))

    return stations


def interpolate_path(stations: list[SurveyStation], depths: list[float] | np.ndarray) -> np.ndarray:
    """Interpolate 3D coordinates (x, y, z) for any list of depths downhole."""
    st_md = np.array([st.depth for st in stations])
    st_x = np.array([st.x for st in stations])
    st_y = np.array([st.y for st in stations])
    st_z = np.array([st.z for st in stations])

    d = np.asarray(depths, float)
    x = np.interp(d, st_md, st_x)
    y = np.interp(d, st_md, st_y)
    z = np.interp(d, st_md, st_z)
    return np.column_stack([x, y, z])
