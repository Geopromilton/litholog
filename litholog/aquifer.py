# Source Generated with Decompyle++
# File: aquifer.pyc (Python 3.12)

'''Aquifer model: water table from observation wells, saturated volumes and storage.

Observation-well tables are read in the forms government data usually come in:

* long:  Well, X/Y (or Lat/Lon), Date, Depth to water (m bgl)
* wide:  Well, X/Y (or Lat/Lon), then one column per season/date
         (e.g. "Pre-monsoon 2023", "Post-monsoon 2023", "May-2024")

Latitude/longitude are converted to the project\'s metric coordinate system
(given, or the UTM zone of the wells). Ground elevation is taken from the table
if present, otherwise from the model\'s ground surface at the well.
'''
from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd
from .grid import Grid, interpolate
from .io import normalize
ALIASES = {
    'well_id': [
        'well_id',
        'well',
        'well_no',
        'station',
        'station_name',
        'site',
        'site_name',
        'name',
        'id',
        'borehole_id',
        'borehole',
        'location',
        'village',
        'village_name',
        'well_name',
        'location_name',
        'station_id',
        'site_id'],
    'x': [
        'x',
        'easting',
        'utm_x',
        'east'],
    'y': [
        'y',
        'northing',
        'utm_y',
        'north'],
    'lat': [
        'lat',
        'latitude',
        'lat_dd',
        'y_lat'],
    'lon': [
        'lon',
        'long',
        'longitude',
        'lon_dd',
        'x_lon'],
    'date': [
        'date',
        'measured_on',
        'date_measured',
        'season',
        'period',
        'month'],
    'dtw': [
        'depth_to_water',
        'dtw',
        'water_level',
        'wl',
        'swl',
        'depth',
        'mbgl',
        'water_level_mbgl',
        'depth_to_water_level',
        'dtwl',
        'gw_level'],
    'ground': [
        'ground_elevation',
        'elevation',
        'rl',
        'gl',
        'msl',
        'altitude',
        'mp_elevation',
        'ground_level'],
}

from typing import NamedTuple


class Wells(NamedTuple):
    table: pd.DataFrame
    readings: list
    note: str = ""

    def values(self, col: str | None = None) -> pd.DataFrame:
        return self.table if col is None else self.table[col]


def _find(cols, key):
    for alt in ALIASES[key]:
        for c in cols:
            if not normalize(c) == alt:
                continue
            
            
            return ALIASES[key], cols, c


def utm_epsg(lon = None, lat = None):
    zone = int((lon + 180) // 6) + 1
    if lat >= 0:
        return 32600 + zone
    return None + zone

SERIAL = {
    'no',
    'sl',
    's_n',
    'sno',
    's_no',
    'slno',
    'srno',
    'index',
    'sl_no',
    'sr_no',
    'serial',
    'serial_no'}

def _degrees(v = None):
    v = pd.to_numeric(v, errors = 'coerce').dropna()
    if len(v) > 0:
        len(v) > 0
        if v.abs().max() <= 180:
            v.abs().max() <= 180
    return v.max() - v.min() < 20


def _lonlat_order(a, b, near):
    '''Which of two degree columns is longitude? Returns (lon, lat, note).'''
    pass
# WARNING: Decompyle incomplete


def load_wells(path = None, crs = None, near = None):
    """Read observation wells (CSV/Excel, long or wide format).

    X/Y columns holding degrees are treated as longitude/latitude (in either order; ``near`` = the
    boreholes' (xmin, xmax, ymin, ymax) decides which is which when the values allow both).
    """
    path = Path(path)
    if path.suffix.lower() in ('.xlsx', '.xls'):
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path, sep = None, engine = 'python')
    df = df.dropna(how = 'all')
    cols = list(df.columns)
    c_y = _find(cols, 'y')
    c_x = _find(cols, 'x')
    c_id = _find(cols, 'well_id')
    c_lon = _find(cols, 'lon')
    c_lat = _find(cols, 'lat')
    c_g = _find(cols, 'ground')
    c_dtw = _find(cols, 'dtw')
    c_date = _find(cols, 'date')
# WARNING: Decompyle incomplete


def wells_from_project(project = None):
    '''Latest water level at each borehole (WaterLevels sheet) as Wells.'''
    rows = []
    for bh in project:
        wl = bh.water_levels.dropna(subset = [
            'depth'])
        if not len(wl):
            continue
        if not pd.notna(bh.x):
            continue
        rows.append({
            'well_id': bh.id,
            'x': bh.x,
            'y': bh.y,
            'ground': bh.elevation if bh.has_elevation else np.nan,
            'latest': wl.iloc[-1]['depth'] })
    if not rows:
        return None
    return Wells(pd.DataFrame(rows), [
        'latest'], 'borehole water levels')


def _sample(grid_x, grid_y, z, px, py):
    '''Nearest-cell values of a (ny, nx) grid at points.'''
    i = np.clip(np.searchsorted(grid_x, px) - 1, 0, len(grid_x) - 1)
    j = np.clip(np.searchsorted(grid_y, py) - 1, 0, len(grid_y) - 1)
    i2 = np.clip(i + 1, 0, len(grid_x) - 1)
    j2 = np.clip(j + 1, 0, len(grid_y) - 1)
    i = np.where(np.abs(grid_x[i2] - px) < np.abs(grid_x[i] - px), i2, i)
    j = np.where(np.abs(grid_y[j2] - py) < np.abs(grid_y[j] - py), j2, j)
    return z[(j, i)]
from dataclasses import dataclass


@dataclass
class WaterTable:
    grid: Grid
    dtw: Grid
    wells: pd.DataFrame
    reading: str | None = None


def water_table(model, wells: Wells, reading: str | None = None, method: str = "idw", surface: str = "depth") -> WaterTable:

    '''Water-table surface on the block model\'s grid (never above ground).

    surface="depth": depth to water is interpolated and hung below the ground surface, so the water
    table follows the topography (suits gentle terrain and shallow weathered aquifers).
    surface="elevation": the water-table elevation at the wells is contoured (the usual practice for
    water-table maps); it is capped at the ground, so hills without wells do not lift it.
    '''
    w = wells.values(reading)
    g_at = _sample(model.x, model.y, model.ground, w['x'].to_numpy(), w['y'].to_numpy())
    w['ground'] = w['ground'].fillna(pd.Series(g_at, index = w.index))
    w['wt'] = w['ground'] - w['dtw']
    w = w.dropna(subset = [
        'wt'])
    if len(w) < 2:
        raise ValueError('Fewer than two wells have a usable water level')
    if surface == 'elevation':
        wt = np.minimum(interpolate(w['x'], w['y'], w['wt'], model.x, model.y, method), model.ground)
        dtw = model.ground - wt
    else:
        dtw = interpolate(w['x'], w['y'], w['dtw'], model.x, model.y, method)
        wt = model.ground - np.maximum(dtw, 0)
    mask = model.inside
    wt = np.where(mask, wt, np.nan)
    if not reading:
        reading
    return WaterTable(Grid(model.x, model.y, wt, model.cell, mask, model.boundary, model.coverage), Grid(model.x, model.y, np.where(mask, dtw, np.nan), model.cell, mask, model.boundary, model.coverage), w, wells.readings[-1])


def saturated_volumes(model, wt, sy=None):
    """Total and saturated (below water table) volume of each unit, with storage."""
    sy = sy or {}
    filled = model.lith >= 0
    below = (model.z[:, None, None] < wt.grid.z[None]) & np.isfinite(wt.grid.z)[None]
    v = getattr(model, "voxel_volume", model.cell * model.cell * model.dz)
    rows = []
    tot_vol = filled.sum() * v
    for k, code in enumerate(model.codes):
        mask_k = model.lith == k
        vol_total = mask_k.sum() * v
        sat_mask = mask_k & below
        vol_sat = sat_mask.sum() * v
        unsat_vol = vol_total - vol_sat
        sy_val = sy.get(code, 0.10)
        storage = vol_sat * sy_val
        rows.append({
            "code": code,
            "volume_m3": vol_total,
            "volume_mcm": vol_total / 1e6,
            "sat_volume_m3": vol_sat,
            "sat_volume_mcm": vol_sat / 1e6,
            "unsat_volume_m3": unsat_vol,
            "unsat_volume_mcm": unsat_vol / 1e6,
            "percent": (vol_total / tot_vol * 100.0) if tot_vol > 0 else 0.0,
            "sy": sy_val,
            "storage_m3": storage,
            "storage_mcm": storage / 1e6,
            "sat_storage_mcm": storage / 1e6,
        })
    return pd.DataFrame(rows)


def saturated_thickness(model, wt, code):
    """Saturated thickness (m) of one unit in each column."""
    k = model.codes.index(code)
    below = (model.z[:, None, None] < wt.grid.z[None]) & np.isfinite(wt.grid.z)[None]
    mask = (model.lith == k) & below
    return mask.sum(axis=0) * model.dz



def reading_label(name = None):
    return re.sub('\\s+', ' ', str(name)).strip()

