# Source Generated with Decompyle++
# File: strat.pyc (Python 3.12)

'''Stratigraphic (layer-cake) model: ordered formation surfaces → solids and volumes.

For layered sequences where each formation occurs once, in a known order
(alluvium, sedimentary basins, weathering profiles). Each borehole gives the
top of every formation; a formation missing in a hole has zero thickness there
(its top = the top of the next formation present below). The top surfaces are
gridded, forced into stratigraphic order (no crossing), and the space between
them fills the block model. The result is a normal BlockModel, so volumes,
smooth solids, views and exports all work unchanged.
'''
from __future__ import annotations
import numpy as np
import pandas as pd
from .correlate import units
from .grid import hull_mask, interpolate, make_axes
from .model3d import BlockModel

def formation_tops(project = None, order = None):
    '''Top elevation of each formation in each hole (NaN below the drilled depth).'''
    rows = []
# WARNING: Decompyle incomplete


def build_strat_model(project, order, cell = None, dz = None, method = None, boundary = (None, None, 'idw', None, 70), target = ('cell', 'float | None', 'dz', 'float | None', 'method', 'str', 'target', 'int', 'return', 'BlockModel')):
    pass
# WARNING: Decompyle incomplete

