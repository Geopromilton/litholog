"""Mining interval assays and downhole length-weighted compositing.

Implements Surpac-style downhole run-of-hole and bench compositing
with length-weighted grade averaging and top-cut outlier capping.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


def composite_assays(
    df: pd.DataFrame,
    composite_length: float = 1.0,
    min_length: float = 0.5,
    elements: Optional[list[str]] = None,
    top_cuts: Optional[dict[str, float]] = None,
) -> pd.DataFrame:
    """Compute fixed-length downhole composites with length-weighted averaging.

    Parameters
    ----------
    df : pd.DataFrame
        Assays table with columns: borehole_id, from, to, and one or more grade elements.
    composite_length : float, default 1.0
        Target composite interval length (m).
    min_length : float, default 0.5
        Minimum length to retain a composite (shorter end-of-hole intervals dropped).
    elements : list of str, optional
        List of numeric grade columns to composite. If None, auto-detects numeric columns.
    top_cuts : dict, optional
        Maximum allowable grade cap per element, e.g. {"Au": 25.0}.
    """
    if df.empty:
        return pd.DataFrame(columns=["borehole_id", "from", "to", "length", "mid"])

    top_cuts = top_cuts or {}
    core_cols = {"borehole_id", "from", "to", "length", "mid"}
    if elements is None:
        elements = [c for c in df.columns if c not in core_cols and pd.api.types.is_numeric_dtype(df[c])]

    composites = []
    for bid, group in df.groupby("borehole_id", sort=False):
        g = group.sort_values("from").dropna(subset=["from", "to"]).copy()
        if g.empty:
            continue
        start_d = float(g["from"].min())
        end_d = float(g["to"].max())

        # Generate regular composite bounds
        comp_edges = np.arange(start_d, end_d + composite_length, composite_length)
        if len(comp_edges) < 2:
            continue

        for i in range(len(comp_edges) - 1):
            c_from = comp_edges[i]
            c_to = min(comp_edges[i + 1], end_d)
            c_len = c_to - c_from
            if c_len < min_length:
                continue

            # Find overlapping raw assay intervals
            overlaps = g[(g["from"] < c_to) & (g["to"] > c_from)].copy()
            if overlaps.empty:
                continue

            comp_row = {
                "borehole_id": bid,
                "from": round(c_from, 3),
                "to": round(c_to, 3),
                "length": round(c_len, 3),
                "mid": round((c_from + c_to) / 2.0, 3),
            }

            for elem in elements:
                w_sum = 0.0
                l_sum = 0.0
                for _, row in overlaps.iterrows():
                    val = row[elem]
                    if pd.isna(val):
                        continue
                    if elem in top_cuts:
                        val = min(float(val), top_cuts[elem])

                    # Intersecting length
                    int_from = max(c_from, float(row["from"]))
                    int_to = min(c_to, float(row["to"]))
                    overlap_len = max(0.0, int_to - int_from)
                    if overlap_len > 0:
                        w_sum += float(val) * overlap_len
                        l_sum += overlap_len

                comp_row[elem] = (w_sum / l_sum) if l_sum > 0 else np.nan

            composites.append(comp_row)

    cols = ["borehole_id", "from", "to", "length", "mid"] + elements
    return pd.DataFrame(composites, columns=cols)
