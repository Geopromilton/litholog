"""LithoLog Studio v5.2.0 Enterprise Native x64: Geological borehole logging and 3D modeling."""
__version__ = '5.2.0'

from .io import load_gms, load_legend, load_project, write_project, write_template
from .patterns import DEFAULT_LEGEND, Legend, LithType
from .project import Borehole, Project
from .striplog import Style, save_striplog, striplog_pages
from .validate import Issue, validate
from .assay import composite_assays
from .dxf import export_boreholes_dxf, export_contours_dxf, export_section_dxf
from .earthworks import calculate_cut_fill
from .geostat import SearchEllipsoid, idw_3d, ordinary_kriging_3d
from .geotech import classify_uscs, correct_spt_n, rqd_quality
from .grade_model import build_grade_model
from .grid import Grid
from .hydrochem import charge_balance_error, piper_figure, save_piper, stiff_figure, to_meq, water_type
from .kmz import export_kmz
from .las import read_las
from .surpac import SurpacString, read_surpac_str, write_surpac_dtm, write_surpac_str
from .survey import minimum_curvature
try:
    from .typeface import use_in_matplotlib
    use_in_matplotlib()
except Exception:
    pass

__all__ = [
    'Grid',
    'SearchEllipsoid',
    'SurpacString',
    'build_grade_model',
    'calculate_cut_fill',
    'charge_balance_error',
    'classify_uscs',
    'composite_assays',
    'correct_spt_n',
    'export_boreholes_dxf',
    'export_contours_dxf',
    'export_kmz',
    'export_section_dxf',
    'idw_3d',
    'minimum_curvature',
    'ordinary_kriging_3d',
    'piper_figure',
    'read_las',
    'read_surpac_str',
    'rqd_quality',
    'save_piper',
    'stiff_figure',
    'to_meq',
    'water_type',
    'write_surpac_dtm',
    'write_surpac_str',
    'Borehole',
    'DEFAULT_LEGEND',
    'Issue',
    'Legend',
    'LithType',
    'Project',
    'Style',
    'load_gms',
    'load_legend',
    'load_project',
    'write_project',
    'save_striplog',
    'striplog_pages',
    'validate',
    'write_template',
]
