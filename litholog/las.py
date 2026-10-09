"""Log ASCII Standard (LAS 2.0 / 3.0) parser for wireline geophysical logs.

Reads LAS files (CWLS standard) containing downhole geophysical curves
(Gamma Ray, Resistivity, Caliper, Density, Sonic, SP) and converts them
into LithoLog downhole tables.
"""

from __future__ import annotations

import io
import re
from pathlib import Path

import numpy as np
import pandas as pd


class LasFile:
    """Parsed Log ASCII Standard (LAS) file."""

    def __init__(self, well_info: dict, curves: list[dict], data: pd.DataFrame):
        self.well = well_info
        self.curves = curves
        self.data = data

    @property
    def well_name(self) -> str:
        return self.well.get("WELL", self.well.get("UWI", "Unknown"))

    def to_downhole_table(self, borehole_id: str | None = None) -> pd.DataFrame:
        """Convert LAS curve channels into LithoLog downhole long-format table.

        Output columns: borehole_id, depth, parameter, value, unit.
        """
        bid = borehole_id or self.well_name
        depth_col = next((c["name"] for c in self.curves if c["name"].upper() in ("DEPT", "DEPTH", "MD")), self.data.columns[0])
        rows = []
        depths = self.data[depth_col]
        for c in self.curves:
            cname = c["name"]
            if cname == depth_col:
                continue
            unit = c.get("unit", "")
            vals = self.data[cname]
            valid = vals.notna() & np.isfinite(vals)
            sub_df = pd.DataFrame({
                "borehole_id": bid,
                "depth": depths[valid],
                "parameter": cname,
                "value": vals[valid],
                "unit": unit,
            })
            rows.append(sub_df)
        if not rows:
            return pd.DataFrame(columns=["borehole_id", "depth", "parameter", "value", "unit"])
        return pd.concat(rows, ignore_index=True)


def read_las(path: Path | str) -> LasFile:
    """Read a LAS 2.0 / 3.0 wireline log file."""
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="replace")

    well_info: dict[str, str] = {}
    curves: list[dict] = []
    current_section = ""
    data_lines = []

    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("~"):
            current_section = s[1].upper()
            continue

        if current_section == "V":
            # Version section
            pass
        elif current_section == "W":
            # Well section: MNEM.UNIT VALUE: DESCRIPTION
            m = re.match(r"^([^.]+)\.([^ ]*)\s+([^:]*):(.*)$", s)
            if m:
                mnem = m.group(1).strip().upper()
                val = m.group(3).strip()
                well_info[mnem] = val
        elif current_section == "C":
            # Curve section: MNEM.UNIT DESCRIPTION
            m = re.match(r"^([^.]+)\.([^ ]*)\s+(.*)$", s)
            if m:
                mnem = m.group(1).strip()
                unit = m.group(2).strip()
                desc = m.group(3).strip()
                curves.append({"name": mnem, "unit": unit, "desc": desc})
        elif current_section == "A":
            # ASCII log data section
            data_lines.append(s)

    if not curves:
        raise ValueError(f"{p.name}: No ~C (Curve) section found in LAS file")

    col_names = [c["name"] for c in curves]
    null_val = float(well_info.get("NULL", -999.25))

    # Read data matrix
    raw_data = " ".join(data_lines)
    arr = np.fromstring(raw_data, sep=" ")
    n_cols = len(col_names)
    if len(arr) % n_cols != 0:
        # Wrap may be enabled, reshape dynamically
        arr = arr[: (len(arr) // n_cols) * n_cols]
    matrix = arr.reshape(-1, n_cols)
    df = pd.DataFrame(matrix, columns=col_names)

    # Mask null values
    df = df.replace(null_val, np.nan)
    return LasFile(well_info, curves, df)
