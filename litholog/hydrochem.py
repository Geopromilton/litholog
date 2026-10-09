"""Hydrochemistry suite: ion balance, Piper trilinear diagrams, and Stiff diagrams.

Implements standard hydrochemical calculations (mg/L to meq/L, charge balance error %),
Piper trilinear diagram plotting, and Stiff polygonal diagrams for groundwater facies analysis.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Polygon

# Equivalent weights (atomic/molecular weight divided by valence) in mg/meq
EQ_WEIGHTS = {
    "ca": 20.039,    # Ca2+
    "mg": 12.153,    # Mg2+
    "na": 22.990,    # Na+
    "k": 39.098,     # K+
    "cl": 35.453,    # Cl-
    "so4": 48.030,   # SO4 2-
    "hco3": 61.016,  # HCO3-
    "co3": 30.005,   # CO3 2-
    "no3": 62.004,   # NO3-
}

SAMPLE_COLORS = [
    "#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD",
    "#8C564B", "#E377C2", "#7F7F7F", "#BCBD22", "#17BECF",
]


def to_meq(df: pd.DataFrame) -> pd.DataFrame:
    """Convert ion concentrations from mg/L to meq/L."""
    out = df.copy()
    for ion, eq in EQ_WEIGHTS.items():
        if ion in out.columns:
            out[f"{ion}_meq"] = pd.to_numeric(out[ion], errors="coerce") / eq
        else:
            out[f"{ion}_meq"] = 0.0
    return out


def charge_balance_error(df: pd.DataFrame) -> pd.Series:
    """Calculate Charge Balance Error percentage (CBE %).

    CBE% = (sum(Cations) - sum(Anions)) / (sum(Cations) + sum(Anions)) * 100
    Acceptable threshold in analytical laboratories is typically <= 5%.
    """
    meq = to_meq(df)
    cations = meq["ca_meq"].fillna(0) + meq["mg_meq"].fillna(0) + meq["na_meq"].fillna(0) + meq["k_meq"].fillna(0)
    anions = (meq["cl_meq"].fillna(0) + meq["so4_meq"].fillna(0) +
              meq["hco3_meq"].fillna(0) + meq["co3_meq"].fillna(0) + meq["no3_meq"].fillna(0))
    total = cations + anions
    return np.where(total > 0, ((cations - anions) / total) * 100.0, np.nan)


def water_type(row: pd.Series) -> str:
    """Determine hydrochemical facies (e.g. Ca-HCO3, Na-Cl)."""
    meq = to_meq(pd.DataFrame([row])).iloc[0]
    c_ca = meq.get("ca_meq", 0) or 0
    c_mg = meq.get("mg_meq", 0) or 0
    c_na = (meq.get("na_meq", 0) or 0) + (meq.get("k_meq", 0) or 0)
    cat_dom = "Ca" if c_ca >= c_mg and c_ca >= c_na else ("Mg" if c_mg >= c_na else "Na")

    a_cl = meq.get("cl_meq", 0) or 0
    a_so4 = meq.get("so4_meq", 0) or 0
    a_hco3 = (meq.get("hco3_meq", 0) or 0) + (meq.get("co3_meq", 0) or 0)
    an_dom = "HCO3" if a_hco3 >= a_cl and a_hco3 >= a_so4 else ("Cl" if a_cl >= a_so4 else "SO4")
    return f"{cat_dom}-{an_dom}"


def piper_figure(df: pd.DataFrame, title: str = "Piper Trilinear Diagram", figsize: tuple = (10, 9)):
    """Draw a publication-grade Piper Trilinear Diagram."""
    meq = to_meq(df)
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_aspect("equal")
    ax.axis("off")

    h = math.sqrt(3) / 2
    # Geometry offsets:
    # Left triangle (cations): base (0, 0) to (1, 0), apex (0.5, h)
    # Right triangle (anions): base (1.2, 0) to (2.2, 0), apex (1.7, h)
    # Central diamond: bottom (1.1, 0.173), top (1.1, 1.905)
    dx_cat = 0.0
    dx_ani = 1.2
    
    # 1. Cation Triangle
    tri_c = np.array([[dx_cat, 0], [dx_cat + 1.0, 0], [dx_cat + 0.5, h], [dx_cat, 0]])
    ax.plot(tri_c[:, 0], tri_c[:, 1], color="#333333", lw=1.2)
    # Internal grid lines (20%, 40%, 60%, 80%)
    for p in [0.2, 0.4, 0.6, 0.8]:
        ax.plot([dx_cat + p, dx_cat + p * 0.5], [0, p * h], color="#E0E0E0", lw=0.6, ls=":")
        ax.plot([dx_cat + p * 0.5, dx_cat + 1.0 - p * 0.5], [p * h, p * h], color="#E0E0E0", lw=0.6, ls=":")
        ax.plot([dx_cat + 1.0 - p, dx_cat + 1.0 - p * 0.5], [0, p * h], color="#E0E0E0", lw=0.6, ls=":")

    ax.text(dx_cat - 0.03, -0.05, "Ca²⁺", ha="center", va="top", fontsize=10, fontweight="bold")
    ax.text(dx_cat + 1.03, -0.05, "Na⁺ + K⁺", ha="center", va="top", fontsize=10, fontweight="bold")
    ax.text(dx_cat + 0.5, h + 0.04, "Mg²⁺", ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax.text(dx_cat + 0.5, -0.11, "CATIONS (% meq/L)", ha="center", va="top", fontsize=9, fontweight="bold", color="#555555")

    # 2. Anion Triangle
    tri_a = np.array([[dx_ani, 0], [dx_ani + 1.0, 0], [dx_ani + 0.5, h], [dx_ani, 0]])
    ax.plot(tri_a[:, 0], tri_a[:, 1], color="#333333", lw=1.2)
    for p in [0.2, 0.4, 0.6, 0.8]:
        ax.plot([dx_ani + p, dx_ani + p * 0.5], [0, p * h], color="#E0E0E0", lw=0.6, ls=":")
        ax.plot([dx_ani + p * 0.5, dx_ani + 1.0 - p * 0.5], [p * h, p * h], color="#E0E0E0", lw=0.6, ls=":")
        ax.plot([dx_ani + 1.0 - p, dx_ani + 1.0 - p * 0.5], [0, p * h], color="#E0E0E0", lw=0.6, ls=":")

    ax.text(dx_ani - 0.03, -0.05, "HCO₃⁻ + CO₃²⁻", ha="center", va="top", fontsize=10, fontweight="bold")
    ax.text(dx_ani + 1.03, -0.05, "Cl⁻", ha="center", va="top", fontsize=10, fontweight="bold")
    ax.text(dx_ani + 0.5, h + 0.04, "SO₄²⁻", ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax.text(dx_ani + 0.5, -0.11, "ANIONS (% meq/L)", ha="center", va="top", fontsize=9, fontweight="bold", color="#555555")

    # 3. Central Diamond
    # Diamond vertices: bottom, right, top, left
    d_bot = np.array([0.5 * (dx_cat + 1.0 + dx_ani), (dx_ani - (dx_cat + 1.0)) * (h / 1.0)])  # (1.1, 0.173)
    d_right = d_bot + np.array([0.5, h])
    d_top = d_right + np.array([-0.5, h])
    d_left = d_bot + np.array([-0.5, h])
    dia = np.array([d_bot, d_right, d_top, d_left, d_bot])
    ax.plot(dia[:, 0], dia[:, 1], color="#333333", lw=1.2)
    # Diamond internal grid
    for p in [0.2, 0.4, 0.6, 0.8]:
        ax.plot([d_bot[0] + 0.5 * p, d_left[0] + 0.5 * p], [d_bot[1] + h * p, d_left[1] + h * p], color="#E0E0E0", lw=0.6, ls=":")
        ax.plot([d_bot[0] - 0.5 * p, d_right[0] - 0.5 * p], [d_bot[1] + h * p, d_right[1] + h * p], color="#E0E0E0", lw=0.6, ls=":")

    # 4. Plot Samples
    for idx, (_, r) in enumerate(meq.iterrows()):
        ca = r.get("ca_meq", 0) or 0
        mg = r.get("mg_meq", 0) or 0
        na_k = (r.get("na_meq", 0) or 0) + (r.get("k_meq", 0) or 0)
        c_tot = ca + mg + na_k

        cl = r.get("cl_meq", 0) or 0
        so4 = r.get("so4_meq", 0) or 0
        hco3 = (r.get("hco3_meq", 0) or 0) + (r.get("co3_meq", 0) or 0)
        a_tot = cl + so4 + hco3

        if c_tot <= 0 or a_tot <= 0:
            continue

        c_ca, c_mg, c_na = ca / c_tot, mg / c_tot, na_k / c_tot
        a_hco3, a_so4, a_cl = hco3 / a_tot, so4 / a_tot, cl / a_tot

        # Cation coord
        xc = dx_cat + c_na + 0.5 * c_mg
        yc = c_mg * h

        # Anion coord
        xa = dx_ani + a_cl + 0.5 * a_so4
        ya = a_so4 * h

        # Diamond coord via intersection of 60-deg rays
        # Ray from cation: (x - xc) * h + (y - yc) * 0.5 = 0 ...
        xd = 0.5 * (xc + xa - (ya - yc) / h * 0.5)
        yd = yc + (xd - xc) * h

        bid = str(r.get("borehole_id", f"Sample {idx+1}"))
        color = SAMPLE_COLORS[idx % len(SAMPLE_COLORS)]

        ax.scatter([xc], [yc], color=color, edgecolors="black", lw=0.6, s=45, zorder=5)
        ax.scatter([xa], [ya], color=color, edgecolors="black", lw=0.6, s=45, zorder=5)
        ax.scatter([xd], [yd], color=color, edgecolors="black", lw=0.6, s=55, zorder=5, label=bid)

    ax.set_title(title, fontsize=14, fontweight="bold", pad=20, color="#1F3A5F")
    if len(meq) <= 12:
        ax.legend(loc="upper right", framealpha=0.9, fontsize=8)

    ax.set_xlim(-0.15, dx_ani + 1.15)
    ax.set_ylim(-0.18, d_top[1] + 0.1)
    return fig


def stiff_figure(row: pd.Series, title: Optional[str] = None, max_meq: float = 20.0):
    """Draw a single Stiff diagram for a water quality sample."""
    meq = to_meq(pd.DataFrame([row])).iloc[0]
    na_k = (meq.get("na_meq", 0) or 0) + (meq.get("k_meq", 0) or 0)
    ca = meq.get("ca_meq", 0) or 0
    mg = meq.get("mg_meq", 0) or 0

    cl = meq.get("cl_meq", 0) or 0
    hco3 = (meq.get("hco3_meq", 0) or 0) + (meq.get("co3_meq", 0) or 0)
    so4 = meq.get("so4_meq", 0) or 0

    fig, ax = plt.subplots(figsize=(4, 3.5))
    ax.axvline(0, color="#666666", lw=1.0, ls="--")

    # Vertices (counter-clockwise):
    # Top: Na+K (left) -> Cl (right) at y=2
    # Mid: Ca (left) -> HCO3 (right) at y=1
    # Bot: Mg (left) -> SO4 (right) at y=0
    verts = [
        (-na_k, 2), (-ca, 1), (-mg, 0),
        (so4, 0), (hco3, 1), (cl, 2),
    ]
    poly = Polygon(verts, closed=True, facecolor="#5C9BD5", edgecolor="#1F3A5F", lw=1.5, alpha=0.6)
    ax.add_patch(poly)

    ax.set_yticks([0, 1, 2])
    ax.set_yticklabels(["Mg²⁺  |  SO₄²⁻", "Ca²⁺  |  HCO₃⁻", "Na⁺+K⁺ |  Cl⁻"], fontsize=9)
    ax.set_xlim(-max_meq, max_meq)
    ax.set_ylim(-0.5, 2.5)
    ax.set_xlabel("meq/L (Cations ← | → Anions)", fontsize=8)
    sample_id = title or str(row.get("borehole_id", "Water Sample"))
    ax.set_title(f"Stiff: {sample_id}", fontsize=10, fontweight="bold", color="#1F3A5F")
    ax.grid(True, lw=0.3, color="#E0E0E0")
    return fig


def save_piper(project, path: Path | str) -> Path:
    """Generate and save Piper trilinear diagram for all project water quality samples."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if not len(project.water_quality):
        raise ValueError("Project has no water quality data")
    fig = piper_figure(project.water_quality, title=f"Piper Diagram: {project.name}")
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out


def load_chemistry(path: Path | str) -> pd.DataFrame:
    p = Path(path)
    if p.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(p)
    return pd.read_csv(p)


def analyse(df: pd.DataFrame) -> pd.DataFrame:
    res = df.copy()
    cbe = charge_balance_error(df)
    res["cbe_pct"] = cbe
    res["balance_ok_5pct"] = np.abs(cbe) <= 5.0
    res["water_type"] = [water_type(row) for _, row in df.iterrows()]
    return res


def piper(df: pd.DataFrame, ax=None, title: str = "Piper Trilinear Diagram"):
    if ax is None:
        return piper_figure(df, title=title)
    fig = piper_figure(df, title=title)
    return fig


def durov(df: pd.DataFrame, ax):
    ax.text(0.5, 0.5, "Durov Diagram\n(Cations vs Anions vs TDS/pH)", ha="center", va="center", fontsize=12)
    ax.set_title("Durov Diagram", fontsize=14, fontweight="bold")


def stiff(df: pd.DataFrame):
    if len(df) > 0:
        return stiff_figure(df.iloc[0])
    return plt.figure()


def gibbs(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.set_title("Gibbs Diagram (TDS vs Na / (Na + Ca))", fontsize=14, fontweight="bold")
    ax.set_xlabel("Na / (Na + Ca)")
    ax.set_ylabel("TDS (mg/L)")
    return fig


def ussl(df: pd.DataFrame, res: pd.DataFrame, ax):
    ax.set_title("USSL Salinity Hazard Diagram", fontsize=14, fontweight="bold")


def wilcox(df: pd.DataFrame, res: pd.DataFrame, ax):
    ax.set_title("Wilcox Irrigation Water Quality Diagram", fontsize=14, fontweight="bold")

