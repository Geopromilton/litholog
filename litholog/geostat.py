"""3D Geostatistics: Anisotropic search ellipsoids, 3D IDW, and 3D Ordinary Kriging.

Implements Surpac-style 3D search ellipsoids oriented by Strike, Dip, and Plunge,
with 3D Inverse Distance Weighting and 3D Ordinary Kriging with variograms.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class SearchEllipsoid:
    """3D Search Ellipsoid for anisotropic spatial estimation.

    Parameters
    ----------
    major_range : float
        Radius along principal (major) axis of continuity.
    semi_major_range : float
        Radius along semi-major axis (in plane of strike/dip).
    minor_range : float
        Radius along minor axis (perpendicular to continuity, across thickness).
    azimuth : float, default 0.0
        Strike / azimuth of the major axis (0 to 360 degrees clockwise from North).
    dip : float, default 0.0
        Dip of the plane (-90 to +90 degrees).
    plunge : float, default 0.0
        Plunge of the major axis within the dipping plane.
    """
    major_range: float = 100.0
    semi_major_range: float = 50.0
    minor_range: float = 20.0
    azimuth: float = 0.0
    dip: float = 0.0
    plunge: float = 0.0

    def rotation_matrix(self) -> np.ndarray:
        """3x3 rotation matrix from world (X, Y, Z) to ellipsoid axes (U, V, W)."""
        a = math.radians(self.azimuth)
        d = math.radians(self.dip)
        p = math.radians(self.plunge)

        # Rz(azimuth) * Rx(dip) * Ry(plunge)
        Rz = np.array([
            [math.cos(a), -math.sin(a), 0],
            [math.sin(a),  math.cos(a), 0],
            [0,            0,           1],
        ])
        Rx = np.array([
            [1, 0,            0],
            [0, math.cos(d), -math.sin(d)],
            [0, math.sin(d),  math.cos(d)],
        ])
        Ry = np.array([
            [ math.cos(p), 0, math.sin(p)],
            [ 0,           1, 0],
            [-math.sin(p), 0, math.cos(p)],
        ])
        return Rz @ Rx @ Ry

    def anisotropic_distance(self, p1: np.ndarray, p2: np.ndarray) -> float:
        """Normalized anisotropic distance between two points."""
        diff = np.asarray(p2) - np.asarray(p1)
        rot = self.rotation_matrix()
        # Rotate into ellipsoid coordinates
        uvw = rot.T @ diff
        norm_d = math.sqrt(
            (uvw[0] / self.major_range) ** 2 +
            (uvw[1] / self.semi_major_range) ** 2 +
            (uvw[2] / self.minor_range) ** 2
        )
        return norm_d


def idw_3d(
    sample_points: np.ndarray,
    sample_values: np.ndarray,
    target_point: np.ndarray,
    ellipsoid: Optional[SearchEllipsoid] = None,
    power: float = 2.0,
    min_samples: int = 1,
    max_samples: int = 12,
) -> float:
    """Estimate a 3D target point value using 3D Inverse Distance Weighting."""
    if len(sample_points) == 0:
        return np.nan

    pts = np.asarray(sample_points, float)
    vals = np.asarray(sample_values, float)
    t = np.asarray(target_point, float)

    if ellipsoid is not None:
        rot = ellipsoid.rotation_matrix()
        diffs = pts - t[None, :]
        uvw = (rot.T @ diffs.T).T
        d_norm = np.sqrt(
            (uvw[:, 0] / ellipsoid.major_range) ** 2 +
            (uvw[:, 1] / ellipsoid.semi_major_range) ** 2 +
            (uvw[:, 2] / ellipsoid.minor_range) ** 2
        )
        mask = d_norm <= 1.0  # Inside search ellipsoid
    else:
        d_norm = np.hypot(np.hypot(pts[:, 0] - t[0], pts[:, 1] - t[1]), pts[:, 2] - t[2])
        mask = np.ones(len(pts), bool)

    valid_pts = pts[mask]
    valid_vals = vals[mask]
    valid_d = d_norm[mask]

    if len(valid_vals) < min_samples:
        return np.nan

    # Exact match on point
    exact = np.isclose(valid_d, 0.0)
    if exact.any():
        return float(valid_vals[exact][0])

    if len(valid_vals) > max_samples:
        idx = np.argsort(valid_d)[:max_samples]
        valid_vals = valid_vals[idx]
        valid_d = valid_d[idx]

    weights = 1.0 / (valid_d ** power)
    return float(np.sum(weights * valid_vals) / np.sum(weights))


def variogram_spherical(h: np.ndarray | float, nugget: float, sill: float, rng: float) -> np.ndarray | float:
    """Spherical variogram model."""
    h_arr = np.asarray(h, float)
    c = sill - nugget
    val = np.where(
        h_arr <= rng,
        nugget + c * (1.5 * (h_arr / rng) - 0.5 * (h_arr / rng) ** 3),
        sill,
    )
    val = np.where(h_arr == 0.0, 0.0, val)
    return val if isinstance(h, np.ndarray) else float(val)


def ordinary_kriging_3d(
    sample_points: np.ndarray,
    sample_values: np.ndarray,
    target_point: np.ndarray,
    nugget: float = 0.0,
    sill: float = 1.0,
    range_val: float = 100.0,
    max_samples: int = 16,
) -> tuple[float, float]:
    """Estimate target point and variance using 3D Ordinary Kriging."""
    pts = np.asarray(sample_points, float)
    vals = np.asarray(sample_values, float)
    t = np.asarray(target_point, float)

    d_to_target = np.linalg.norm(pts - t[None, :], axis=1)
    if len(pts) > max_samples:
        idx = np.argsort(d_to_target)[:max_samples]
        pts = pts[idx]
        vals = vals[idx]
        d_to_target = d_to_target[idx]

    n = len(pts)
    if n == 0:
        return np.nan, np.nan
    if n == 1:
        return float(vals[0]), float(sill)

    # Inter-sample distance matrix
    dist_matrix = np.linalg.norm(pts[:, None, :] - pts[None, :, :], axis=2)
    gamma_mat = variogram_spherical(dist_matrix, nugget, sill, range_val)

    # Form Kriging LHS matrix with Lagrange multiplier row/column
    A = np.zeros((n + 1, n + 1))
    A[:n, :n] = gamma_mat
    A[n, :n] = 1.0
    A[:n, n] = 1.0
    A[n, n] = 0.0

    # RHS vector
    gamma_target = variogram_spherical(d_to_target, nugget, sill, range_val)
    b = np.zeros(n + 1)
    b[:n] = gamma_target
    b[n] = 1.0

    try:
        weights_and_mu = np.linalg.solve(A, b)
        weights = weights_and_mu[:n]
        mu = weights_and_mu[n]
        est = float(np.sum(weights * vals))
        variance = float(np.sum(weights * gamma_target) + mu)
        return est, max(0.0, variance)
    except np.linalg.LinAlgError:
        return float(np.mean(vals)), float(sill)
