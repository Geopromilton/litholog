from pathlib import Path
import zipfile
import pytest

from litholog import load_project, export_boreholes_dxf, export_section_dxf, export_contours_dxf, export_kmz
from litholog.cli import main
from litholog.model3d import build_model
from litholog.section import through_boreholes, save_section
from litholog.grid import grid_attribute

SAMPLE = Path(__file__).parent / "data" / "sample_project.xlsx"


def test_saturated_storage_in_model():
    proj = load_project(SAMPLE)
    # SAMPLE has water levels in WaterLevels sheet for multiple boreholes
    m = build_model(proj, cell=100, dz=2.0)
    assert m.water_table is not None
    assert m.sat_expected is not None

    vols = m.volumes(sy={"FGRA": 0.03, "FGN": 0.02})
    assert "sat_volume_m3" in vols.columns
    assert "unsat_volume_m3" in vols.columns
    assert "sat_storage_m3" in vols.columns

    for _, r in vols.iterrows():
        assert r["sat_volume_m3"] <= r["volume_m3"] + 1e-5
        if r["code"] in ("FGRA", "FGN"):
            assert r["sat_storage_m3"] <= r["storage_m3"] + 1e-5


def test_dxf_export(tmp_path):
    proj = load_project(SAMPLE)

    # 1. 3D Borehole sticks DXF
    dxf_bh = tmp_path / "boreholes.dxf"
    export_boreholes_dxf(proj, dxf_bh)
    assert dxf_bh.exists()
    content = dxf_bh.read_text(encoding="ascii")
    assert "AC1009" in content
    assert "COLLARS" in content
    assert "BOREHOLES" in content
    assert "LITH_" in content

    # 2. Cross-section DXF
    line = through_boreholes(proj, ["BW-01", "BW-02", "BW-03"], "A-A'")
    dxf_sec = tmp_path / "section_A.dxf"
    export_section_dxf(proj, line, dxf_sec, ve=5.0)
    assert dxf_sec.exists()
    sec_content = dxf_sec.read_text(encoding="ascii")
    assert "GROUND_SURFACE" in sec_content
    assert "BASE_OF_LOGS" in sec_content
    assert "LITH_" in sec_content

    # 3. Contours DXF
    grid, _ = grid_attribute(proj, "ground", cell=100)
    dxf_cnt = tmp_path / "contours.dxf"
    export_contours_dxf(grid, dxf_cnt)
    assert dxf_cnt.exists()
    cnt_content = dxf_cnt.read_text(encoding="ascii")
    assert "CONTOURS" in cnt_content
    assert "POLYLINE" in cnt_content


def test_kmz_export(tmp_path):
    proj = load_project(SAMPLE)
    kmz_path = tmp_path / "boreholes.kmz"
    export_kmz(proj, kmz_path, crs="EPSG:32643")
    assert kmz_path.exists()
    assert zipfile.is_zipfile(kmz_path)

    with zipfile.ZipFile(kmz_path) as zf:
        assert "doc.kml" in zf.namelist()
        kml_text = zf.read("doc.kml").decode("utf-8")
        assert "<kml" in kml_text
        assert "BW-01" in kml_text
        assert "<altitudeMode>absolute</altitudeMode>" in kml_text
        assert "style_RSOIL" in kml_text


def test_cli_dxf_and_kmz(tmp_path):
    dxf_out = tmp_path / "cli_out.dxf"
    kmz_out = tmp_path / "cli_out.kmz"

    assert main(["dxf", str(SAMPLE), "-o", str(dxf_out)]) == 0
    assert dxf_out.exists()

    assert main(["kmz", str(SAMPLE), "-o", str(kmz_out), "--crs", "EPSG:32643"]) == 0
    assert kmz_out.exists()


def test_section_with_well_construction(tmp_path):
    proj = load_project(SAMPLE)
    line = through_boreholes(proj, ["BW-01", "BW-03", "TW-06"], "TestSec")
    sec_pdf = tmp_path / "sec_with_well.pdf"
    res = save_section(proj, line, sec_pdf)
    assert res.exists()
    assert res.stat().st_size > 10000
