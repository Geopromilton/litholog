# Source Generated with Decompyle++
# File: horizons.pyc (Python 3.12)

'''Horizon-based layer model (GMS-style "horizons → solids").

Why: an indicator (voxel) model decides each voxel by the lithology most
boreholes have *at that depth*. A thin layer that occurs at different depths in
different holes (e.g. a water-bearing fracture zone) rarely wins that vote and
breaks into isolated lenses, although it is present in almost every hole.

How:
1. Horizons: every layer occurrence is matched across all boreholes by
   progressive multiple-sequence alignment of the borehole logs (the same
   sequence/depth correlation used for cross-sections). Repeated units become
   separate horizons ("Fractured layer · zone 1", "· zone 2", ...).
2. The thickness of each horizon is interpolated as a continuous surface: zero
   where the horizon is absent in a hole (pinch-out), unknown below the drilled
   depth.
3. Horizons are stacked from the ground surface (DEM or collars) downwards, so
   surfaces never cross; the base of drilling truncates the stack.
4. Volumes are integrated exactly from the thickness grids; solids are meshed
   directly from the horizon surfaces (smooth, no voxel steps).
'''
from __future__ import annotations
import numpy as np
import pandas as pd
from .correlate import Unit, align, units
from .grid import hull_mask, interpolate, make_axes
from .model3d import BlockModel

def _depth_units(bh):
    '''Units with depths (top/bot positive downwards) in the Unit fields as negatives.'''
    return units(bh, datum = 'depth')


def assign_horizons(project = None, scale = None):
    '''Master horizon sequence and, per borehole, the horizon index of each unit.

    Returns (horizons, assignment) where horizons is a list of dicts
    {code, top, bot, n} (mean depths, number of holes) ordered top→bottom and
    assignment is {borehole_id: [(horizon_index, Unit), ...]}.
    '''
    pass
# WARNING: Decompyle incomplete


def _merge_equivalent(master, assignment):
    """Merge same-code horizons that never occur together in one hole, when that keeps every
    hole's order (the aligner may have opened two slots for what is one layer)."""
    pass
# WARNING: Decompyle incomplete


def horizon_labels(horizons, legend):
    """Readable names: repeated codes get 'zone 1, 2, ...' top to bottom."""
    total = { }
    seen = { }
    for h in horizons:
        total[h['code']] = total.get(h['code'], 0) + 1
    out = []
    for h in horizons:
        seen[h['code']] = seen.get(h['code'], 0) + 1
        name = legend.get(h['code']).name
        out.append(name if total[h['code']] == 1 else f'''{name} · zone {seen[h['code']]}''')
    return out


def horizon_table(project = None, horizons = None, assignment = None):
    '''Thickness of every horizon in every hole (0 = absent, NaN = below drilled depth).'''
    rows = []
    for bh in project:
        if bh.id not in assignment:
            continue
        got = set(assignment[bh.id])
        last = max(got) if got else -1
        us = _depth_units(bh)
        row = {
            'borehole_id': bh.id,
            'x': bh.x,
            'y': bh.y,
            'ground': bh.elevation if bh.has_elevation else np.nan,
            'depth': -(us[-1].bot) if us else np.nan }
        for k in range(len(horizons)):
            if k in got:
                row[f'''h{k}'''] = got[k].thick
                continue
            row[f'''h{k}'''] = 0 if k < last else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def horizon_thickness(tab, n, gx = None, gy = None, method = None, constraints = ('idw', None, None), horizons = ('tab', 'pd.DataFrame', 'n', 'int', 'return', 'list')):
    '''Thickness grid of each of ``n`` horizons from the per-hole table (see ``horizon_table``).

    ``method``: a name or ``grid.Interp`` (influence settings). ``constraints``: pinch-out lines,
    thickness points and absent areas added to the data of the horizons they name.
    '''
    hy0 = tab['y'].to_numpy(float)
    hx0 = tab['x'].to_numpy(float)
    shape = (len(gy), len(gx))
# WARNING: Decompyle incomplete


def predict_log(project, x = None, y = None, method = None, scale = ('idw', 25, None), constraints = ('x', 'float', 'y', 'float', 'scale', 'float')):
    '''Predicted log at (x, y) from the boreholes of ``project``: [(top_depth, bottom_depth, code)].'''
    (horizons, assignment) = assign_horizons(project, scale)
    tab = horizon_table(project, horizons, assignment)
    gy = np.array([
        float(y)])
    gx = np.array([
        float(x)])
    hy = tab['y'].to_numpy(float)
    hx = tab['x'].to_numpy(float)
    base = float(np.clip(interpolate(hx, hy, tab['depth'], gx, gy, 'linear'), 0, None)[(0, 0)])
# WARNING: Decompyle incomplete


def build_horizon_model(project, cell, dz, method, boundary = None, dem = None, target = None, scale = (None, None, 'idw', None, None, 120, 25, None), constraints = ('cell', 'float | None', 'dz', 'float | None', 'target', 'int', 'scale', 'float', 'return', 'BlockModel')):
    (horizons, assignment) = assign_horizons(project, scale)
    tab = horizon_table(project, horizons, assignment)
    hy = tab['y'].to_numpy(float)
    hx = tab['x'].to_numpy(float)
# WARNING: Decompyle incomplete


def horizon_volumes(model = None, legend = None):
    rows = []
    for h, lab, v in enumerate(zip(model.horizons, model.h_labels, model.h_volumes)):
        t = model.h_top[k] - model.h_bot[k]
        present = np.nanmean(np.where(model.inside, t > 0.01, np.nan)) * 100
        rows.append({
            'horizon': k + 1,
            'code': h['code'],
            'layer': lab,
            'holes_present': h['n'],
            'mean_thickness_m': float(np.nanmean(np.where(model.inside & (t > 0.01), t, np.nan))),
            'area_present_pct': float(present),
            'volume_mcm': v / 1e+06 })
    return pd.DataFrame(rows)


def _layer_mesh(x, y, top, bot, active_nodes, cell_ok):
    '''Closed mesh of the layer between top and bot over active grid cells.'''
    (ny, nx) = top.shape
    (X, Y) = np.meshgrid(x, y)
    nn = ny * nx
    verts = np.vstack([
        np.column_stack([
            X.ravel(),
            Y.ravel(),
            np.nan_to_num(top).ravel()]),
        np.column_stack([
            X.ravel(),
            Y.ravel(),
            np.nan_to_num(bot).ravel()])])
    idx = np.arange(nn).reshape(ny, nx)
    (cj, ci) = np.nonzero(cell_ok)
    b = idx[(cj, ci + 1)]
    a = idx[(cj, ci)]
    d = idx[(cj + 1, ci)]
    c = idx[(cj + 1, ci + 1)]
    faces = [
        np.column_stack([
            a,
            b,
            c]),
        np.column_stack([
            a,
            c,
            d]),
        np.column_stack([
            a + nn,
            c + nn,
            b + nn]),
        np.column_stack([
            a + nn,
            d + nn,
            c + nn])]
    pad = np.pad(cell_ok, 1, constant_values=False)
    for (dj, di), (p, q) in {
        (-1, 0): ((0, 0), (0, 1)),
        (1, 0): ((1, 1), (1, 0)),
        (0, -1): ((1, 0), (0, 0)),
        (0, 1): ((0, 1), (1, 1)),
    }.items():
        nb = pad[1 + dj : 1 + dj + cell_ok.shape[0], 1 + di : 1 + di + cell_ok.shape[1]]
        wj, wi = np.nonzero(cell_ok & ~nb)
        p0 = idx[wj + p[0], wi + p[1]]
        p1 = idx[wj + q[0], wi + q[1]]
        faces += [
            np.column_stack([p0, p1, p1 + nn]),
            np.column_stack([p0, p1 + nn, p0 + nn]),
        ]
    faces = np.vstack(faces) if faces else np.zeros((0, 3), int)
    del active_nodes
    return (verts, faces)


def horizon_solids(model=None, cutaway=None, only=None, per_horizon: bool = False):
    '''Solids meshed from the horizon surfaces: one per lithology code (its horizons merged),
    or with ``per_horizon`` one per horizon (``Solid.horizon`` = its index).'''
    from litholog.solid import Solid
    (ny, nx) = model.inside.shape
    cells_in = (
        model.inside[:-1, :-1]
        & model.inside[1:, :-1]
        & model.inside[:-1, 1:]
        & model.inside[1:, 1:]
    )
    if cutaway:
        ym = np.median(model.y)
        xm = np.median(model.x)
        cx = (model.x[:-1] + model.x[1:]) / 2
        cy = (model.y[:-1] + model.y[1:]) / 2
        (CX, CY) = np.meshgrid(cx, cy)
        quad = ((CX < xm) if 'w' in cutaway else (CX > xm)) & ((CY < ym) if 's' in cutaway else (CY > ym))
        cells_in &= ~quad
    per_code = {}
    for k, h in enumerate(model.horizons):
        if only and h['code'] not in only:
            continue
        b = model.h_bot[k]
        t = model.h_top[k]
        th = np.nan_to_num(t - b)
        cell_ok = cells_in & (
            th[:-1, :-1] + th[1:, :-1] + th[:-1, 1:] + th[1:, 1:] > 0.02
        )
        if not cell_ok.any():
            continue
        (v, f) = _layer_mesh(model.x, model.y, t, b, None, cell_ok)
        per_code.setdefault(k if per_horizon else h['code'], []).append((v, f))
    solids = []
    for key, parts in per_code.items():
        code = model.horizons[key]['code'] if per_horizon else key
        off = 0
        fs = []
        vs = []
        for v, f in parts:
            vs.append(v)
            fs.append(f + off)
            off += len(v)
        F = np.vstack(fs)
        V = np.vstack(vs)
        used = np.unique(F)
        remap = np.full(len(V), -1)
        remap[used] = np.arange(len(used))
        solids.append(Solid(code, V[used], remap[F].astype(np.int32), key if per_horizon else None))
    return solids

