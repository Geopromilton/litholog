"""Export a LithoLog project to OpenHydro Studio import files.

Two CSV files are written, ready for OpenHydro's import wizards:

* ``litholog_soundings.csv`` for *Data > Subsurface > Soundings*: one row per
  borehole with the ground elevation and, per model layer, the depth of the
  layer base below ground. A layer that a borehole does not contain is written
  with zero thickness (a pinch-out). A borehole that ends inside a layer leaves
  the deeper layers blank, which OpenHydro treats as "not reached".
* ``litholog_observation_wells.csv`` for *Data > Wells > Observation*: collar
  coordinates, well depth and one depth to water (latest, mean, minimum or
  maximum). No ``layer`` column is written, so OpenHydro places each well in
  the layer that holds the bottom of the well.

Coordinates are written as they are in the LithoLog workbook, so they must be
in the OpenHydro model's projected CRS (metres).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Mapping, Sequence, Union

import numpy as np
import pandas as pd

from .project import Project

LayerSpec = Union[None, Mapping[str, Sequence[str]], Sequence[Union[str, tuple]]]


def _slug(name: str) -> str:
    s = re.sub(r"[^0-9a-zA-Z]+", "_", str(name).strip().lower()).strip("_")
    return s or "layer"


def layer_stack(project: Project, layers: LayerSpec = None) -> list[tuple[str, list[str]]]:
    """Ordered ``(layer name, [lithology codes])`` list, top layer first.

    ``layers`` may be a mapping ``{"Soil": ["SOIL"], "Rock": ["GRN", "LST"]}``,
    a list of codes (one layer each), or a list of ``(name, codes)`` pairs.
    When omitted, every lithology code is a layer, ordered by its average depth.
    """
    litho = project.lithology
    if layers is None:
        if litho.empty:
            return []
        mid = (litho["from"].astype(float) + litho["to"].astype(float)) / 2.0
        order = mid.groupby(litho["code"].astype(str).str.strip().str.upper()).mean().sort_values()
        out = []
        for code in order.index:
            name = project.legend.get(code).name
            out.append((name if name and not name.endswith("(not in legend)") else code, [code]))
        return out
    if isinstance(layers, Mapping):
        items = list(layers.items())
    else:
        items = []
        for it in layers:
            if isinstance(it, str):
                items.append((it, [it]))
            else:
                items.append((it[0], list(it[1])))
    return [(str(n), [str(c).strip().upper() for c in codes]) for n, codes in items]


def _bases_for_borehole(litho: pd.DataFrame, group_of: dict[str, int], n_layers: int) -> list[float]:
    """Depth of the base of each layer for one borehole (NaN = not reached)."""
    rows = litho.dropna(subset=["from", "to"])
    rows = rows[rows["code"].astype(str).str.strip().str.upper().isin(group_of)]
    if rows.empty:
        return [np.nan] * n_layers
    g = rows["code"].astype(str).str.strip().str.upper().map(group_of).to_numpy()
    to = rows["to"].astype(float).to_numpy()
    deepest_layer = int(g[np.argmax(to)])      # the layer holding the bottom of the log
    bases: list[float] = []
    for i in range(n_layers):
        if i > deepest_layer:
            bases.append(np.nan)
            continue
        sel = g <= i
        base = float(to[sel].max()) if sel.any() else 0.0
        if i == deepest_layer:
            base = float(to.max())
        bases.append(max(base, bases[-1] if bases else 0.0))
    return bases


def soundings_table(project: Project, layers: LayerSpec = None) -> pd.DataFrame:
    stack = layer_stack(project, layers)
    if not stack:
        raise ValueError("The project has no lithology to build layers from")
    group_of = {code: i for i, (_, codes) in enumerate(stack) for code in codes}
    names = []
    for n, _ in stack:
        s = _slug(n)
        while s in names:
            s += "_2"
        names.append(s)
    rows = []
    bh = project.boreholes.set_index("borehole_id")
    for bid in project.ids:
        lit = project.lithology[project.lithology["borehole_id"] == bid]
        b = bh.loc[bid]
        bases = _bases_for_borehole(lit, group_of, len(stack))
        row = {"station_id": bid, "x": b["x"], "y": b["y"], "elevation_m": b["elevation"]}
        for nm, v in zip(names, bases):
            row[f"{nm}_base_depth_m"] = None if np.isnan(v) else round(v, 3)
        row["source"] = "LithoLog Studio"
        rows.append(row)
    df = pd.DataFrame(rows)
    keep = [c for c in df.columns if c.endswith("_base_depth_m") and df[c].notna().any()]
    return df[["station_id", "x", "y", "elevation_m", *keep, "source"]]


def observation_wells_table(project: Project, statistic: str = "latest") -> pd.DataFrame:
    if statistic not in ("latest", "mean", "min", "max"):
        raise ValueError("statistic must be latest, mean, min or max")
    wl = project.water_levels.dropna(subset=["depth"])
    if wl.empty:
        raise ValueError("The project has no water levels")
    bh = project.boreholes.set_index("borehole_id")
    rows = []
    for bid, g in wl.groupby("borehole_id", sort=False):
        if bid not in bh.index:
            continue
        g = g.copy()
        g["date"] = pd.to_datetime(g["date"], errors="coerce")
        d = g["depth"].astype(float)
        if statistic == "latest":
            val = float(g.sort_values("date").iloc[-1]["depth"])
        elif statistic == "mean":
            val = float(d.mean())
        elif statistic == "min":
            val = float(d.min())
        else:
            val = float(d.max())
        b = bh.loc[bid]
        rows.append({
            "well_id": bid, "x": b["x"], "y": b["y"], "elevation_m": b["elevation"],
            "well_depth_m": b["total_depth"], "well_type": "Bore well",
            "dtw_m": round(val, 3), "n_levels": len(g), "statistic": statistic,
        })
    return pd.DataFrame(rows)


def export_openhydro(project: Project, out_dir: Union[str, Path], layers: LayerSpec = None,
                     statistic: str = "latest") -> dict[str, Path]:
    """Write the OpenHydro import files into ``out_dir`` and return their paths."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {}
    s = soundings_table(project, layers)
    paths["soundings"] = out / "litholog_soundings.csv"
    s.to_csv(paths["soundings"], index=False)
    if len(project.water_levels.dropna(subset=["depth"])):
        w = observation_wells_table(project, statistic)
        paths["observation_wells"] = out / "litholog_observation_wells.csv"
        w.to_csv(paths["observation_wells"], index=False)
    return paths


def parse_layer_option(text: str | None) -> LayerSpec:
    """Parse ``"Soil=SOIL;Weathered=CLAY,SAND;Rock=LST,GRN"`` from the command line."""
    if not text:
        return None
    out: dict[str, list[str]] = {}
    for part in text.split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError(f"Layer '{part}' must look like Name=CODE1,CODE2")
        name, codes = part.split("=", 1)
        out[name.strip()] = [c.strip() for c in codes.split(",") if c.strip()]
    return out
