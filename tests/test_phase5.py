"""Tests for Phase 5: Streamlit Web Studio & Enterprise Dossier Exports."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from litholog.dxf import export_boreholes_dxf
from litholog.io import load_project
from litholog.kmz import export_kmz
from litholog.model3d import build_model
from litholog.surpac import SurpacString, write_surpac_str


def test_saturated_volume_columns(tmp_path):
    demo = Path(__file__).parents[1] / "litholog" / "data" / "sample_project.xlsx"
    p = load_project(demo)
    m = build_model(p, cell=100.0, dz=5.0)
    vols = m.volumes(sy={"SILT": 0.05, "CLAY": 0.02})
    assert "volume_mcm" in vols.columns
    assert "percent" in vols.columns
    assert "storage_mcm" in vols.columns
    if m.water_table is not None:
        assert "sat_volume_mcm" in vols.columns
        assert "unsat_volume_mcm" in vols.columns
        assert "sat_storage_mcm" in vols.columns


def test_project_dossier_zip_archive(tmp_path):
    demo = Path(__file__).parents[1] / "litholog" / "data" / "sample_project.xlsx"
    project = load_project(demo)

    dxf_p = tmp_path / "boreholes.dxf"
    export_boreholes_dxf(project, dxf_p)
    assert dxf_p.exists() and dxf_p.stat().st_size > 500

    kmz_p = tmp_path / "boreholes.kmz"
    export_kmz(project, kmz_p)
    assert kmz_p.exists() and kmz_p.stat().st_size > 500

    str_p = tmp_path / "boreholes.str"
    s_list = []
    for sid, bh in enumerate(project, 1):
        if pd.notna(bh.x) and pd.notna(bh.y):
            el = bh.elevation if bh.has_elevation else 0.0
            s_list.append(SurpacString(sid, [(bh.x, bh.y, el), (bh.x, bh.y, el - (bh.depth or 1.0))], desc=bh.id))
    write_surpac_str(str_p, s_list, title=project.name)
    assert str_p.exists() and str_p.stat().st_size > 100

    # Build ZIP archive
    dossier_buf = io.BytesIO()
    with zipfile.ZipFile(dossier_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("PROJECT_SUMMARY.md", f"# {project.name} Dossier\nBoreholes: {len(project.boreholes)}")
        zf.writestr("boreholes.csv", project.boreholes.to_csv(index=False))
        zf.writestr("lithology.csv", project.lithology.to_csv(index=False))
        zf.write(dxf_p, "boreholes_3d.dxf")
        zf.write(kmz_p, "boreholes.kmz")
        zf.write(str_p, "boreholes.str")

    zip_bytes = dossier_buf.getvalue()
    assert len(zip_bytes) > 2000

    # Verify contents of zip
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z_check:
        names = z_check.namelist()
        assert "PROJECT_SUMMARY.md" in names
        assert "boreholes.csv" in names
        assert "lithology.csv" in names
        assert "boreholes_3d.dxf" in names
        assert "boreholes.kmz" in names
        assert "boreholes.str" in names


def test_launchers_and_entry_points():
    root = Path(__file__).parents[1]
    assert (root / "LithoLogStudio.bat").exists()
    # python -m litholog / python -m litholog.studio must be runnable
    assert (root / "litholog" / "__main__.py").exists()
    assert (root / "litholog" / "studio" / "__main__.py").exists()
    from litholog.cli import main
    assert callable(main)


def test_user_paths_are_not_drive_specific(tmp_path, monkeypatch):
    monkeypatch.setenv("LITHOLOG_HOME", str(tmp_path))
    from litholog import paths

    assert paths.app_data_dir() == tmp_path
    assert paths.debug_log_path().parent == tmp_path
    assert paths.exports_dir() == tmp_path / "exports"
    assert paths.exports_dir().is_dir()


def test_no_hardcoded_drive_paths_in_package():
    src = Path(__file__).parents[1] / "litholog"
    offenders = [str(p) for p in src.rglob("*.py")
                 if "D:\\LithoLog" in p.read_text(encoding="utf-8", errors="ignore")]
    assert not offenders, offenders


def test_studio_window_class_importable():
    pytest.importorskip("PySide6")
    pytest.importorskip("pyvistaqt")
    from litholog.studio import mainwindow  # noqa: F401
