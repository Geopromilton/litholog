# LithoLog Studio

Borehole logging, cross-sections, 3D lithology and aquifer models for hydrogeology and geotechnics, with
geotechnical, hydrochemical and mining-geology add-ons. Version 5.2.0.

LithoLog reads one Excel workbook (or GMS, LAS and Surpac files) and produces strip logs, correlated
cross-sections with well construction, fence diagrams, contour maps, smooth lithology solids with saturated
aquifer storage, and DXF, Google Earth and Surpac exports. It is available three ways:

| Interface | Start it with | Needs |
|---|---|---|
| **Desktop studio** (Qt + VTK, ribbon interface) | `litholog studio`, `python -m litholog.studio`, or `LithoLogStudio.bat` | `pip install -e ".[gui]"` |
| **Command line** | `litholog ...` or `python -m litholog ...` | `pip install -e .` |
| **Browser app** (Streamlit, six pages) | `litholog app` | `pip install -e ".[app]"` |

On Windows, `LithoLogStudio.exe` and `portable\LithoLogStudio\` hold a packaged build of the desktop studio.
It is built separately from this source tree.

## Install

```bash
pip install -e .            # library and command line
pip install -e ".[gui]"     # desktop studio (PySide6, PyVista)
pip install -e ".[dev]"     # tests
python -m pytest            # run the test suite
```

Logs go to `%LOCALAPPDATA%\LithoLog Studio` (or `~/.litholog`) and exports to
`Documents\LithoLog Studio\exports`. Set `LITHOLOG_HOME` to put both somewhere else.

## Quick start

```bash
litholog template my_site.xlsx         # input workbook with example rows
# fill in my_site.xlsx
litholog validate my_site.xlsx         # overlaps, gaps, bad depths, unknown codes
litholog striplog my_site.xlsx         # strip logs in ./striplogs
litholog section my_site.xlsx -b BH-01 BH-02 BH-03
litholog dxf my_site.xlsx              # 3D boreholes to AutoCAD DXF (R12)
litholog kmz my_site.xlsx --crs EPSG:32643
litholog piper my_site.xlsx            # needs a WaterQuality sheet
```

## Input workbook

| Sheet | One row per | Key columns |
|---|---|---|
| Boreholes | borehole | Borehole ID, X, Y, Elevation, Total depth |
| Lithology | interval | Borehole ID, From, To, Code, Description |
| Construction | well element | Borehole ID, From, To, Element (casing, screen, gravel pack, seal), Diameter |
| WaterLevels | water level | Borehole ID, Date, Depth to water |
| Downhole | reading | Borehole ID, Depth, Parameter, Value, Unit |
| Geotech | test interval | Borehole ID, From, To, SPT N, RQD, USCS, Recovery |
| WaterQuality | sample | Borehole ID, Date, Ca, Mg, Na, K, HCO3, SO4, Cl, NO3, pH, EC |
| Survey | station | Borehole ID, Depth, Dip, Azimuth |
| Assays | interval | Borehole ID, From, To, grades, Density |
| Legend | lithology code | Code, Name, Color, Pattern |

## Commands

| Command | Does |
|---|---|
| `template`, `validate`, `convert` | create, check, or convert (GMS text, CSV folder) to a workbook |
| `striplog`, `section`, `fence` | strip logs, cross-sections with well construction, 3D fence diagrams |
| `map` | contour maps and ESRI ASCII grids (IDW or kriging) |
| `model` | 3D lithology solids, volumes and saturated storage |
| `dxf`, `kmz` | AutoCAD DXF and Google Earth exports |
| `piper`, `stiff` | hydrochemical diagrams |
| `legend` | print or draw the lithology legend |
| `app`, `studio` | open the browser app or the desktop studio |

## Python

```python
from litholog import load_project, export_boreholes_dxf, export_kmz, save_piper

project = load_project("my_site.xlsx")
export_boreholes_dxf(project, "site.dxf")
export_kmz(project, "site.kmz", crs="EPSG:32643")
if len(project.water_quality):
    save_piper(project, "piper.png")
```

## Maturity

| Area | State |
|---|---|
| Logs, sections, fences, maps, solids, aquifer storage, DXF, KMZ, hydrochemistry | Covered by the test suite and used on the sample data |
| Minimum-curvature surveys, cut and fill, charge-balance error, SPT correction | Checked against exact analytical results (`tests/test_numerics.py`) |
| SPT N60 and (N1)60 correction | Checked against the published factor tables (`tests/test_numerics.py`). Hammer energy, rod length, borehole and sampler factors are applied; overburden stress assumes dry soil unless you supply sigma'v |
| 3D kriging, grade block models, grade-tonnage, Surpac `.str` and `.dtm` | Experimental. Not yet validated against GSLIB or commercial software |

Treat anything in the experimental rows as a screening tool.

## Repository layout

```
litholog/            library, command line, browser app (app.py)
litholog/studio/     desktop studio (PySide6 + PyVista)
tests/               pytest suite (tests/data holds the small reference workbook)
examples/            sample workbook and tutorial data
docs/                user manual
```

## Licence

MIT. RockWorks, GMS and Surpac are trademarks of their owners. LithoLog Studio is independent software, and
it reads and writes some of their file formats.
