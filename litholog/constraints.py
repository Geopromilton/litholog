# Source Generated with Decompyle++
# File: constraints.pyc (Python 3.12)

"""Horizon constraints: the geologist's interpretation added to the borehole data (as GMS horizon
coverages).

Three kinds, each for one horizon (by its number, as listed in the model, e.g. 4) or for every
horizon of a unit (by its code, e.g. code 4 = all fracture zones):

* pinchout  – a line along which the layer thins to zero (e.g. the edge of a fracture zone);
* absent    – a polygon where the layer does not exist (eroded, not deposited, dyke …);
* thickness – points of known thickness (from geophysics, a dug well, an outcrop …).

File formats
------------
CSV / Excel: columns ``Horizon, Type, X, Y`` and optionally ``Value`` (thickness, m) and ``Feature``
(an id grouping the vertices of one line or polygon, in order).

KML / KMZ / GeoJSON (e.g. drawn in Google Earth or QGIS): lines, polygons and points whose name is
``<horizon> <type> [value]``, for example ``H4 pinchout``, ``code 4 absent``, ``H7 thickness 6``.
GeoJSON may instead carry ``horizon``, ``type`` and ``value`` properties.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path
import numpy as np
import pandas as pd
KINDS = ('pinchout', 'absent', 'thickness')
@dataclass
class Constraint:
    target: str
    kind: str
    xy: np.ndarray
    value: float = 0.0
    name: str = ""

    def applies_to(self, k: int, code: str) -> bool:
        if self.target.startswith("h"):
            return self.target == f"h{k}"
        elif self.target.startswith("c:"):
            return self.target[2:].upper() == code.upper()
        return False


@dataclass
class Constraints:
    items: list[Constraint] = field(default_factory=list)


def _densify(line, spacing: float = 25.0) -> np.ndarray:
    out = [line[0]]
    for i in range(len(line) - 1):
        p0 = np.array(line[i])
        p1 = np.array(line[i + 1])
        dist = np.hypot(p1[0] - p0[0], p1[1] - p0[1])
        if dist > spacing:
            n = int(np.ceil(dist / spacing))
            for f in np.linspace(0, 1, n + 1)[1:]:
                out.append(p0 + f * (p1 - p0))
        else:
            out.append(p1)
    return np.array(out)


_NAME = re.compile('^\\s*(?:(h|horizon)\\s*#?\\s*(\\d+)|(?:code|c|unit)\\s*[:=]?\\s*([\\w\\-]+))\\s*[:,\\-]?\\s*(pinch-?out|absent|missing|thickness)\\s*[:=]?\\s*([\\d.]+)?', re.I)

def _parse_name(name = None):
    if not name:
        name
    m = _NAME.match('')
    if not m:
        return None
    target = f'''h{int(m.group(2))}''' if m.group(2) else f'''c:{m.group(3).upper()}'''
    kind = m.group(4).lower().replace('-', '')
    kind = 'absent' if kind == 'missing' else kind
    if m.group(5):
        return (target, kind, float(m.group(5)))
    return (None, target, kind)


def _target(value = None):
    v = str(value).strip()
    m = re.match('^(?:h|horizon)\\s*#?\\s*(\\d+)$', v, re.I)
    if m:
        return f'''h{int(m.group(1))}'''
    m = None.match('^(?:code|c|unit)\\s*[:=]?\\s*(.+)$', v, re.I)
    if m:
        return f'''c:{m.group(1).strip().upper()}'''
    if None.match('^\\d+(\\.0)?$', v):
        return f'''h{int(float(v))}'''
    return f'''{v.upper()}'''


def load_constraints(path = None, crs = None, near = None):
    """Read constraints (CSV/Excel table, KML/KMZ or GeoJSON) into the boreholes' coordinates."""
    path = Path(path)
    ext = path.suffix.lower()
    if ext in ('.csv', '.txt', '.xlsx', '.xls'):
        items = _read_table(path)
        src = None
    elif ext in ('.kml', '.kmz'):
        src = 'EPSG:4326'
        items = _read_kml(path)
    elif ext in ('.geojson', '.json'):
        src = 'EPSG:4326'
        items = _read_geojson(path)
    else:
        raise ValueError(f'''{path.name}: constraints must be CSV/Excel, KML/KMZ or GeoJSON''')
    if not items:
        raise ValueError(f'''{path.name}: no constraints found (names like \'H4 pinchout\', \'code 4 absent\', \'H7 thickness 6\')''')
    note = ''
    if src:
        if not crs:
            crs
        dst = _utm_for(items, near)
        from pyproj import Transformer
        t = Transformer.from_crs(src, dst, always_xy=True)
        for c in items:
            c.xy = np.column_stack(t.transform(c.xy[:, 0], c.xy[:, 1]))
        note = f"latitude/longitude → {dst}"
    for c in items:
        if c.kind not in KINDS:
            raise ValueError(f"Unknown constraint type '{c.kind}' (use pinchout, absent or thickness)")
    return Constraints(items)


def _utm_for(items, near=None):
    from .aquifer import utm_epsg
    if near is not None:
        return utm_epsg(near[0], near[1])
    xs = [pt[0] for c in items for pt in c.xy]
    ys = [pt[1] for c in items for pt in c.xy]
    return utm_epsg(float(np.mean(xs)), float(np.mean(ys)))



def _read_table(path=None):
    from litholog.io import normalize
    df = pd.read_excel(path) if path.suffix.lower() in ('.xlsx', '.xls') else pd.read_csv(path, sep=None, engine='python')
# WARNING: Decompyle incomplete


def _coords(text):
    pass
# WARNING: Decompyle incomplete


def _read_kml(path = None):
    pass
# WARNING: Decompyle incomplete


def _read_geojson(path = None):
    import json
    gj = json.loads(path.read_text())
    feats = gj.get('features', [
        gj]) if gj.get('type') in ('FeatureCollection', 'Feature') else []
    items = []
# WARNING: Decompyle incomplete

