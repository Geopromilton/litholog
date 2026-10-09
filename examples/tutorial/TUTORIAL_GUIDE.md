# LithoLog Studio — Master Tutorial & User Workflow Guide

**Dataset:** Enhanced 16-Borehole Exploration & Hydrogeological Project (`sample_project.xlsx`)  
**Companion Directory:** `D:\LithoLog Studio\examples\tutorial`  
**Application Executable:** `D:\LithoLog Studio\LithoLogStudio.exe`  

---

## 1. Overview & Dataset Architecture

The enhanced tutorial project provides a production-grade, 16-borehole spatial exploration grid (`BH-01` to `BH-16`) spanning $2.4\text{ km} \times 2.4\text{ km}$ across varied topography (120 m to 185 m amsl) with depths ranging up to 110 m.

### Workbook Sheets in `sample_project.xlsx`:

| Sheet Name | Contents | Application Tab Used |
| :--- | :--- | :--- |
| **`Boreholes`** | Collar coordinates (X, Y), ground elevation, total depth, drilling method, diameter, date. | `Home`, `Boreholes`, `3D Model` |
| **`Lithology`** | 112 continuous depth intervals across 7 geological formations (`SOIL`, `CLAY`, `SAND`, `SHLE`, `LST`, `SNDS`, `GRNT`). | `Boreholes`, `Sections`, `3D Model` |
| **`Construction`** | Multi-string well construction intervals (surface casing, bentonite seal, production casing, slotted screen, gravel pack, open hole). | `Boreholes ▸ Strip log`, `Well Casing` |
| **`WaterLevels`** | Multi-season water levels: Pre-monsoon (May 2025) and Post-monsoon (Nov 2025) for all 16 boreholes. | `Analysis ▸ Aquifer`, `Recharge (WTF)` |
| **`Downhole`** | 6,200 continuous geophysical & grade readings (Resistivity $\Omega\cdot\text{m}$, Gamma API, SP mV, Fe %). | `Analysis ▸ Property model` |
| **`Fractures`** | 130 structural discontinuity measurements (depth, dip, dip direction, aperture, water yield, remarks). | `Analysis ▸ Fractures` |
| **`Legend`** | Unit codes, names, hex colors, pattern styles, and geological groups. | `Home ▸ Legend`, `View ▸ Rendering` |
| **`Survey`** | 3D directional drilling survey stations (depth, dip, azimuth). | `Boreholes ▸ 3D Survey` |
| **`Assays`** | 787 downhole 2.0 m bench assay intervals (`Fe%`, `SiO2%`, `Al2O3%`, `LOI%`, `P%`, `Au g/t`, `Cu%`). | `3D Model ▸ Mining & Earthworks` |

---

## 2. Step-by-Step Hands-On Workflow

### Step 1: Loading Data & Setting the Study Area
1. Launch **`LithoLogStudio.exe`**.
2. Click **Home ▸ Tutorial project** (or **Home ▸ Open data** and select `sample_project.xlsx`).
   - *Observation:* The project tree immediately populates with 16 boreholes. The 3D view renders 14 continuous geological solids with voxel marching cubes in $\sim 1.5$ seconds.
3. Click **Home ▸ Boundary** and select `examples\tutorial\boundary.kml` (or `boundary.geojson`).
   - *Observation:* The study area is bounded and clipped to the concession boundaries.
4. Click **Home ▸ DEM** and select `examples\tutorial\dem_surface.asc`.
   - *Observation:* The real digital terrain surface is draped over the subsurface model. Toggle **View ▸ Terrain (DEM)** to inspect subsurface-to-surface alignment.

---

### Step 2: Borehole Striplogs, Casing & Geotechnics
1. In the **Project Panel**, select any borehole (e.g., `BH-03` or `BH-07`).
2. Click **Boreholes ▸ Strip log**.
   - *Observation:* Switches to the **Log** tab. Displays elevation scale, lithology patterns, detailed descriptions, multi-string casing/screen columns, water table line, and fracture depth ticks.
3. Click **Boreholes ▸ All logs (PDF)**.
   - *Observation:* Generates a multi-page PDF book containing striplogs for all 16 boreholes in publication layout.
4. Click **Boreholes ▸ Validate data**.
   - *Observation:* Validates all 112 intervals and collar elevations, confirming project integrity.
5. Explore Geotechnical Loggers:
   - **Boreholes ▸ USCS Soil:** Enter soil sieve percentages (e.g., Fines=15%, Sand=45%, Gravel=40%, LL=32%, PI=12%) -> Classifies ASTM D2487 soil group (`SC-SM`).
   - **Boreholes ▸ SPT N60:** Enter raw blow count $N=18$ at depth $12.5\text{ m}$ -> Computes energy ratio $N_{60}$, overburden $(N_1)_{60}$, and effective stress $\sigma'_v$.
   - **Boreholes ▸ Deere RQD:** Enter core recovery index $78\%$ -> Reports rock mass quality (*Good*).
   - **Boreholes ▸ CWLS LAS:** Open `examples\tutorial\geophysics_BH01.las` -> Loads digital geophysical well log curves (GR, RES, RHOB, NPHI).
   - **Boreholes ▸ 3D Survey:** Calculates 3D minimum-curvature deviation paths for all 16 holes and exports `deviated_trajectories.csv`.

---

### Step 3: Geological Cross-Sections & Fence Diagrams
1. Click **Sections ▸ New section**.
   - Choose a borehole profile: `BH-01 -> BH-06 -> BH-11 -> BH-16` (NW-SE diagonal profile).
   - Select vertical exaggeration $VE = 5.0\times$, style *Stratigraphy*. Click **OK**.
   - *Observation:* Renders a geological section with continuous strata correlations, borehole strip columns, and elevation markers.
2. Click **Sections ▸ Fence diagram**.
   - *Observation:* Calculates the Minimum Spanning Tree (MST) network and generates a 3D multi-panel fence diagram connecting all 16 boreholes.

---

### Step 4: Contour Mapping & Surface Exports
1. Click **Maps ▸ New map**.
   - Attribute: **Ground elevation** (or **Water table** / **Layer thickness**).
   - Method: **Kriging** (or **IDW**). Cell size: $50\text{ m}$. Click **OK**.
   - *Observation:* Generates a high-quality contour map with color ramp, contour lines, and posted borehole locations.
2. Click **Maps ▸ Grid (.asc)** to export the interpolated grid to ESRI ASCII grid format.
3. Click **Maps ▸ Surpac (.str)** and **Maps ▸ Surpac (.dtm)** to export GEOVIA Surpac 3D strings and wireframes.

---

### Step 5: 3D Volumetric Geological & Block Modeling
1. Click **3D Model ▸ Build model**:
   - Select **Method: Horizons** or **Indicator (IDW / Kriging)**.
   - Adjust cell size ($25\text{ m}$) and vertical resolution $dz$ ($1.0\text{ m}$). Click **OK**.
   - *Observation:* Multi-threaded engine computes volumetric solids and updates the 3D viewport.
2. Click **3D Model ▸ Layer properties**:
   - Inspect formation bulk volumes (MCM).
   - Toggle individual unit visibility (e.g. uncheck `SOIL` and `CLAY` to expose the underlying limestone and ore body).
3. Mining & Earthworks:
   - Click **3D Model ▸ Block Model:** Builds a regularized 3D mineral resource block model with estimated grades.
   - Click **3D Model ▸ Grade-Tonnage:** Evaluates cut-off grade vs. recoverable tonnage curves in the **Mining** document tab.
   - Click **3D Model ▸ Cut & Fill:** Calculates prismatic earthworks cut volume, fill volume, and net balance between original topography and a design surface.
   - Click **3D Model ▸ Compositing:** Standardizes downhole assay intervals to 2.0 m benches with 10.0 g/t top-cut capping.
4. Click **3D Model ▸ Cut plane**:
   - Activates an interactive clipping plane slice through the 3D subsurface block.

---

### Step 6: Hydrogeology, Geochemistry & Structural Analysis
1. Groundwater & Storage:
   - Click **Analysis ▸ Aquifer & storage**.
   - Select pre-monsoon reading (`2025-05-15`) or post-monsoon reading (`2025-11-20`).
   - *Observation:* Calculates the phreatic water table surface, overlays it in 3D (light blue), and logs saturated storage volume per formation.
2. Groundwater Recharge:
   - Click **Analysis ▸ Recharge (WTF)**.
   - Select Pre-season: `2025-05-15`, Post-season: `2025-11-20`, Rainfall: $600\text{ mm}$, RIF: $15\%$. Click **OK**.
   - *Observation:* Computes seasonal groundwater recharge via the Water-Table Fluctuation method across all formations.
3. 3D Property Interpolation:
   - Click **Analysis ▸ Property model**.
   - Select parameter: **`Resistivity`**, **`Gamma`**, or **`Fe`**. Click **OK**.
   - *Observation:* Interpolates a continuous 3D scalar property field throughout the volume.
4. Hydrochemistry Analysis:
   - Click **Analysis ▸ Hydrochemistry** and select `examples\tutorial\water_chemistry.csv`.
   - *Observation:* Opens the **Chemistry** document tab. Use the diagram dropdown to switch between **Piper**, **Durov**, **Stiff**, **USSL**, **Wilcox**, and **Gibbs** diagrams with verified ionic balance ($\pm 5\%$).
5. Structural Stereonet:
   - Click **Analysis ▸ Fractures**.
   - *Observation:* Generates an equal-area Schmidt net displaying pole density contours, strike rose diagrams, and fracture yield annotations.
6. Quality Assurance:
   - Click **Analysis ▸ Cross-validation**. Select target unit and output folder.
   - *Observation:* Performs leave-one-out cross-validation across all 16 boreholes and generates a statistical accuracy report.

---

### Step 7: Publishing & Enterprise Exports
1. Viewport Styling (**View Tab**):
   - Switch between **Theme ▸ Dark** and **Light**.
   - Set **3D background ▸ Theme / White / Sky / Black**.
   - Enable **Rendering ▸ Rock texture**, **Contact lines**, and **Studio lighting**.
2. Output Deliverables:
   - **Home ▸ Save image:** 300 DPI publication raster (PNG/JPG/TIFF).
   - **Home ▸ Save page:** Publication vector PDF of the active 2D figure.
   - **3D Model ▸ 3D web page:** Standalone interactive HTML WebGL model viewable in any browser without installing software.
   - **3D Model ▸ Solids (OBJ/STL):** Watertight 3D triangular meshes for CAD, 3D printing, or Blender.
   - **3D Model ▸ ParaView:** Full voxel VTK dataset for advanced visualization in ParaView.
   - **3D Model ▸ AutoCAD DXF:** AutoCAD DXF R12 3D tubes and stratum meshes.
   - **3D Model ▸ Google Earth:** 3D georeferenced KMZ boreholes for Google Earth.
   - **Home ▸ Project Dossier:** 1-Click ZIP bundle assembling Summary Markdown, CSV tables, DXF, KMZ, and Surpac STR files.

---

## 3. Quick Reference: File Locations

- **Master Workbook:** [`sample_project.xlsx`](file:///d:/LithoLog%20Studio/litholog_source_ribbon/data/sample_project.xlsx)
- **Tutorial Directory:** [`D:\LithoLog Studio\examples\tutorial`](file:///d:/LithoLog%20Studio/examples/tutorial)
  - `boundary.kml` / `boundary.geojson`: Concession boundary
  - `dem_surface.asc`: High-resolution digital terrain grid
  - `water_chemistry.csv`: Complete laboratory hydrochemical dataset
  - `geophysics_BH01.las`: CWLS LAS 2.0 well log file
  - `stratigraphic_constraints.csv`: Stratigraphic pinch-out rules
  - `TUTORIAL_GUIDE.md`: This comprehensive workflow guide
