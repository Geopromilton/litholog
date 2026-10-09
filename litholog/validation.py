# Source Generated with Decompyle++
# File: validation.pyc (Python 3.12)

"""Model validation: leave-one-out cross-validation, method comparison and model uncertainty.

Each borehole is removed in turn, its log is predicted at its location from the remaining
boreholes, and the prediction is scored against the real log:

* lithology match: share of the drilled depth where the predicted unit is the logged unit;
* per unit: detection rate (logged occurrences that the prediction also shows there), false
  alarms (predicted occurrences the hole does not have), error in the depth of each occurrence's
  top, and error in the total thickness;
* methods compared: horizon model (IDW and kriging), voxel (indicator) model and — as the
  baseline any model must beat — simply copying the nearest borehole.

Model uncertainty: unit volumes from the different methods (their spread is a practical
uncertainty range) and the distance from every point of the study area to the nearest borehole.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from .correlate import units
METHODS = {
    'horizons_custom': 'Horizons · your settings',
    'horizons_idw': 'Horizons · IDW',
    'horizons_kriging': 'Horizons · kriging',
    'voxel': 'Voxel · indicator IDW',
    'nearest': 'Nearest borehole (baseline)' }

def _log(bh):
    '''[(top_depth, bottom_depth, code)] of a borehole.'''
    pass
# WARNING: Decompyle incomplete


def _subset(project, drop_id):
    import copy
    p = copy.copy(project)
    p.boreholes = project.boreholes[project.boreholes['borehole_id'] != drop_id]
    p.lithology = project.lithology[project.lithology['borehole_id'] != drop_id]
    return p


def _voxel_log(others, x, y, dz, power = (0.5, 2)):
    '''Indicator-IDW prediction at a point (depth datum), as in the voxel model.'''
    pass
# WARNING: Decompyle incomplete


def predict(project, bid, method, interp, constraints = (None, None)):
    pass
# WARNING: Decompyle incomplete


def _codes_at(log, depths):
    out = np.full(len(depths), '', dtype = object)
    for t, b, c in log:
        out[(depths >= t) & (depths < b)] = c
    return out


def _occurrences(log, code):
    '''Contiguous occurrences of a unit (adjacent intervals of the same code merged).'''
    occ = []
    for t, b, c in log:
        if c != code:
            continue
        if occ and abs(occ[-1][1] - t) < 1e-06:
            occ[-1] = (occ[-1][0], b)
            continue
        occ.append((t, b))
    return occ


def score(actual, pred, codes, dz = (0.25,)):
    pass
# WARNING: Decompyle incomplete


def cross_validate(project, methods, progress, interp, constraints = (('horizons_idw', 'horizons_kriging', 'voxel', 'nearest'), None, None, None)):
    '''Leave-one-out cross-validation. Returns (per_hole, per_unit) tables.'''
    pass
# WARNING: Decompyle incomplete


def summarise(per_hole, per_unit, legend = (None,)):
    pass
# WARNING: Decompyle incomplete


def volumes_by_method(project, boundary, sy, interp, constraints = (None, None, None, None)):
    pass
# WARNING: Decompyle incomplete


def distance_grid(project, boundary=None, cell=None):
    from scipy.spatial import cKDTree
    from litholog.grid import hull_mask, make_axes
    b = project.boreholes.dropna(subset = [
        'x',
        'y'])
    hy = b['y'].to_numpy(float)
    hx = b['x'].to_numpy(float)
# WARNING: Decompyle incomplete


def report_figure(per_hole, summary, per_unit, dist, legend, title='', target=None, boundary=None, volumes=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from litholog.typeface import use_in_matplotlib
    use_in_matplotlib()
    navy = '#1F3A5F'
    fig = plt.figure(figsize = (16.5354, 11.6929))
    fig.text(0.04, 0.955, f'''MODEL VALIDATION{' – ' + title if title else ''}''', fontsize = 16, fontweight = 'bold', color = navy)
    n = per_hole['borehole_id'].nunique()
    fig.text(0.04, 0.925, f'''Leave-one-out cross-validation: each of {n} boreholes hidden in turn and predicted from the others''', fontsize = 10, color = '#444444')
    ms = list(summary['method'])
# WARNING: Decompyle incomplete


def validation_report(project, out, methods, boundary, target, title, volumes, progress, interp, constraints = (None, None, None, '', True, None, None, None)):
    '''Run the cross-validation and write tables, a one-page PDF/PNG and a text summary to ``out``.'''
    pass
# WARNING: Decompyle incomplete

