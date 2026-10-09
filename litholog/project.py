"""In-memory project model: boreholes and their interval / point data."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .patterns import Legend

# Columns every table is guaranteed to have after loading.
TABLE_COLUMNS = {
    "boreholes": ["borehole_id", "x", "y", "elevation", "total_depth"],
    "lithology": ["borehole_id", "from", "to", "code", "description"],
    "construction": ["borehole_id", "from", "to", "element", "diameter", "material"],
    "water_levels": ["borehole_id", "date", "depth"],
    "downhole": ["borehole_id", "depth", "parameter", "value", "unit"],
    "geotech": ["borehole_id", "from", "to", "spt_n", "n60", "rqd", "recovery", "weathering"],
    "water_quality": ["borehole_id", "date", "ca", "mg", "na", "k", "cl", "so4", "hco3", "co3", "no3", "ph", "tds", "ec"],
    "survey": ["borehole_id", "depth", "dip", "azimuth"],
    "assays": ["borehole_id", "from", "to"],
    "fractures": ["borehole_id", "depth", "dip", "dip_direction", "aperture", "yield", "remarks"],
}


def empty_table(name: str) -> pd.DataFrame:
    return pd.DataFrame(columns=TABLE_COLUMNS[name])


@dataclass
class Borehole:
    id: str
    x: float = np.nan
    y: float = np.nan
    elevation: float = np.nan
    total_depth: float = np.nan
    info: dict = field(default_factory=dict)  # any extra collar columns
    lithology: pd.DataFrame = field(default_factory=lambda: empty_table("lithology"))
    construction: pd.DataFrame = field(default_factory=lambda: empty_table("construction"))
    water_levels: pd.DataFrame = field(default_factory=lambda: empty_table("water_levels"))
    downhole: pd.DataFrame = field(default_factory=lambda: empty_table("downhole"))
    geotech: pd.DataFrame = field(default_factory=lambda: empty_table("geotech"))
    water_quality: pd.DataFrame = field(default_factory=lambda: empty_table("water_quality"))
    survey: pd.DataFrame = field(default_factory=lambda: empty_table("survey"))
    assays: pd.DataFrame = field(default_factory=lambda: empty_table("assays"))

    @property
    def has_elevation(self) -> bool:
        return pd.notna(self.elevation)

    @property
    def depth(self) -> float:
        """Deepest known depth: total depth, else deepest logged value."""
        cands = [self.total_depth]
        if len(self.lithology):
            cands.append(self.lithology["to"].max())
        if len(self.construction):
            cands.append(self.construction["to"].max())
        if len(self.downhole):
            cands.append(self.downhole["depth"].max())
        if len(self.geotech):
            cands.append(self.geotech["to"].max())
        if len(self.assays):
            cands.append(self.assays["to"].max())
        cands = [c for c in cands if pd.notna(c)]
        return float(max(cands)) if cands else 0.0

    def path(self, depths=None) -> np.ndarray:
        """Compute true 3D spatial (X, Y, Z) coordinates along the borehole path."""
        from .survey import interpolate_path, minimum_curvature

        x = self.x if pd.notna(self.x) else 0.0
        y = self.y if pd.notna(self.y) else 0.0
        z = self.elevation if self.has_elevation else 0.0
        stations = minimum_curvature(x, y, z, self.survey)
        if depths is None:
            return np.array([[st.x, st.y, st.z] for st in stations])
        return interpolate_path(stations, depths)


@dataclass
class Project:
    boreholes: pd.DataFrame
    lithology: pd.DataFrame
    construction: pd.DataFrame
    water_levels: pd.DataFrame
    downhole: pd.DataFrame
    geotech: pd.DataFrame = field(default_factory=lambda: empty_table("geotech"))
    water_quality: pd.DataFrame = field(default_factory=lambda: empty_table("water_quality"))
    survey: pd.DataFrame = field(default_factory=lambda: empty_table("survey"))
    assays: pd.DataFrame = field(default_factory=lambda: empty_table("assays"))
    fractures: pd.DataFrame = field(default_factory=lambda: empty_table("fractures"))
    legend: Legend = field(default_factory=Legend)
    name: str = "LithoLog project"

    @property
    def ids(self) -> list[str]:
        return list(self.boreholes["borehole_id"])

    def borehole(self, bid: str) -> Borehole:
        rows = self.boreholes[self.boreholes["borehole_id"] == bid]
        if rows.empty:
            raise KeyError(f"Borehole '{bid}' is not in the Boreholes table")
        row = rows.iloc[0].to_dict()
        core = TABLE_COLUMNS["boreholes"]
        info = {k: v for k, v in row.items() if k not in core and _present(v)}

        def sub(df, sort):
            if "borehole_id" not in df.columns:
                return df
            return df[df["borehole_id"] == bid].sort_values(sort).reset_index(drop=True)

        return Borehole(
            id=bid,
            x=row.get("x", np.nan),
            y=row.get("y", np.nan),
            elevation=row.get("elevation", np.nan),
            total_depth=row.get("total_depth", np.nan),
            info=info,
            lithology=sub(self.lithology, "from"),
            construction=sub(self.construction, "from"),
            water_levels=sub(self.water_levels, "date"),
            downhole=sub(self.downhole, ["parameter", "depth"]),
            geotech=sub(self.geotech, "from") if len(self.geotech) else empty_table("geotech"),
            water_quality=sub(self.water_quality, "date") if len(self.water_quality) else empty_table("water_quality"),
            survey=sub(self.survey, "depth") if len(self.survey) else empty_table("survey"),
            assays=sub(self.assays, "from") if len(self.assays) else empty_table("assays"),
        )

    def __iter__(self):
        return (self.borehole(b) for b in self.ids)

    def __len__(self) -> int:
        return len(self.boreholes)

    def __getitem__(self, item):
        if isinstance(item, int):
            return self.borehole(self.ids[item])
        return self.borehole(str(item))

    def __contains__(self, item) -> bool:
        return str(item) in self.ids

    @property
    def borehole_ids(self) -> list[str]:
        return self.ids

    @property
    def lithology_codes(self) -> list[str]:
        if "code" in self.lithology.columns:
            return sorted([str(c) for c in self.lithology["code"].dropna().unique().tolist()])
        return []

    @property
    def has_water_table(self) -> bool:
        return len(self.water_levels) > 0

    @property
    def total_depth(self) -> float:
        if "total_depth" in self.boreholes.columns:
            td = self.boreholes["total_depth"].dropna().sum()
            if pd.notna(td) and td > 0:
                return float(td)
        if "to" in self.lithology.columns:
            return float(self.lithology["to"].dropna().max() or 0.0)
        return 0.0

    def to_excel(self, path):
        from .io import write_project
        return write_project(self, path)

    def load_legend(self, path):
        from .patterns import load_legend
        self.legend = load_legend(path)

    def export_pdf_logs(self, out_path):
        from .striplog import save_striplog
        from matplotlib.backends.backend_pdf import PdfPages
        import matplotlib.pyplot as plt
        from pathlib import Path
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with PdfPages(p) as pdf:
            for bh in self:
                fig, ax = plt.subplots(figsize=(8.5, 11))
                save_striplog(bh, ax=ax, legend=self.legend)
                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)


def _present(v) -> bool:
    if v is None:
        return False
    if isinstance(v, float) and np.isnan(v):
        return False
    return str(v).strip() != "" and v is not pd.NaT
