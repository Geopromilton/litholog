"""Digital Elevation Model (DEM) ingestion, sampling and coordinate transformations.

Supported formats:
  - GeoTIFF (.tif, .tiff), via `tifffile` (float32 / int16, geokeys or tags)
  - SRTM tiles (.hgt, compressed as .hgt.gz or .zip): big-endian int16, 1 or 3 arc-sec
  - ESRI ASCII grid (.asc, .txt): standard 6-line header + row-major values
  - Copernicus GLO-30 download via AWS open data for any bounding box.

A DEM can sample ground elevation at any (x, y) point, reproject on the fly if
pyproj is installed, and drape raster contours onto the block model.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import numpy as np


@dataclass
class DEM:
    z: np.ndarray
    x0: float
    y0: float
    dx: float
    dy: float
    crs: object = None
    name: str = "dem"


MODEL_CRS = {"crs": None}


def load_dem(path) -> DEM:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    name = path.name.lower()
    if name.endswith((".hgt", ".hgt.gz")) or (name.endswith(".zip") and ".hgt" in name):
        return _load_hgt(path)
    if path.suffix.lower() in (".asc", ".txt"):
        return _load_ascii(path)
    if path.suffix.lower() in (".tif", ".tiff"):
        return _load_geotiff(path)
    raise ValueError(
        f"{path.name}: DEM must be a GeoTIFF (.tif), SRTM tile (.hgt, .hgt.gz, .zip) or ESRI ASCII grid (.asc)"
    )


def _load_hgt(path=None):
    """SRTM .hgt tile (1 or 3 arc-second, big-endian int16, named after its SW corner, e.g. N08E077)."""
    import gzip
    import math
    import re
    import zipfile
    from pyproj import CRS

    name = path.name.lower()
    if name.endswith(".gz"):
        with gzip.open(path, "rb") as gz:
            data = gz.read()
    elif name.endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            member = next(n for n in z.namelist() if n.lower().endswith(".hgt"))
            data = z.read(member)
    else:
        data = path.read_bytes()
    raw = np.frombuffer(data, dtype=">i2")
    n = int(round(np.sqrt(raw.size)))
    if n * n != raw.size:
        raise ValueError(f"{path.name}: not an SRTM .hgt tile")
    m = re.search(r"([ns])(\d{2})([ew])(\d{3})", name)
    if not m:
        raise ValueError(f"{path.name}: SRTM tiles must keep their name (e.g. N08E077.hgt)")
    lat = int(m.group(2)) * (1 if m.group(1) == "n" else -1)
    lon = int(m.group(4)) * (1 if m.group(3) == "e" else -1)
    z = raw.reshape((n, n)).astype(float)
    z[z <= -32768] = np.nan
    step = 1.0 / (n - 1)
    return DEM(z, float(lon), float(lat + 1), step, step, CRS.from_epsg(4326), path.name.split(".")[0])


COPERNICUS = "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_{ns}{lat:02d}_00_{ew}{lon:03d}_00_DEM/Copernicus_DSM_COG_10_{ns}{lat:02d}_00_{ew}{lon:03d}_00_DEM.tif"


def download_copernicus(
    lon0, lon1=None, lat0=None, lat1=None, folder=None, progress=None
) -> Path:
    """Download the Copernicus GLO-30 DEM (30 m, free; ESA / AWS open data) for a lon/lat box and save it as
    one GeoTIFF clipped to the box. Returns the file path."""
    import math
    import urllib.request

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    tiles = []
    for la in range(math.floor(lat0), math.floor(lat1) + 1):
        for lo in range(math.floor(lon0), math.floor(lon1) + 1):
            url = COPERNICUS.format(
                ns="N" if la >= 0 else "S",
                lat=abs(la),
                ew="E" if lo >= 0 else "W",
                lon=abs(lo),
            )
            dst = folder / url.rsplit("/", 1)[1]
            if not dst.exists():
                if progress:
                    progress(f"Downloading {dst.name} …")
                try:
                    urllib.request.urlretrieve(url, dst)
                except Exception as e:
                    if progress:
                        progress(f"  tile {dst.name} not available ({e})")
                    continue
            tiles.append(load_dem(dst))
    if not tiles:
        raise RuntimeError("No DEM tiles could be downloaded (check the internet connection)")
    step = tiles[0].dx
    xs = np.arange(lon0, lon1 + step, step)
    ys = np.arange(lat1, lat0 - step, -step)
    X, Y = np.meshgrid(xs, ys)
    z = np.full(X.shape, np.nan)
    for t in tiles:
        v = sample(t, X.ravel(), Y.ravel()).reshape(X.shape)
        z = np.where(np.isfinite(v), v, z)
    out = folder / f"copernicus_dem_{lat0:.2f}_{lon0:.2f}.tif"
    write_geotiff(out, z, xs[0], ys[0], step, step, 4326)
    return out


def write_geotiff(path, z, x0, y0=None, dx=None, dy=None, epsg: int = 4326):
    """Minimal GeoTIFF writer (float32, pixel centres x0/y0 of the first column/row, north up)."""
    import tifffile

    geokeys = (
        1, 1, 0, 4,
        1024, 0, 1, 2 if epsg == 4326 else 1,
        1025, 0, 1, 1,
        2048 if epsg == 4326 else 3072, 0, 1, epsg,
        4096, 0, 1, 5773,
    )
    tifffile.imwrite(
        path,
        np.where(np.isfinite(z), z, -9999).astype(np.float32),
        compression="zlib",
        extratags=[
            (33550, "d", 3, (dx, dy, 0)),
            (33922, "d", 6, (0, 0, 0, x0 - dx / 2, y0 + dy / 2, 0)),
            (34735, "H", len(geokeys), geokeys),
            (42113, "s", 6, "-9999\x00"),
        ],
    )
    return path


def _load_ascii(path=None):
    head = {}
    with open(path) as f:
        for _ in range(6):
            pos = f.tell()
            line = f.readline().split()
            if len(line) == 2 and line[0].replace("_", "").isalpha():
                head[line[0].lower()] = float(line[1])
                continue
            f.seek(pos)
            break
        z = np.loadtxt(f, dtype=float)
    nd = head.get("nodata_value", -9999)
    z[z == nd] = np.nan
    cs = head["cellsize"]
    x0 = head.get("xllcenter", head.get("xllcorner", 0) + cs / 2)
    yll = head.get("yllcenter", head.get("yllcorner", 0) + cs / 2)
    y0 = yll + (z.shape[0] - 1) * cs
    crs = None
    prj = path.with_suffix(".prj")
    if prj.exists():
        from pyproj import CRS

        crs = CRS.from_wkt(prj.read_text())
    return DEM(z, x0, y0, cs, cs, crs, path.stem)


def _load_geotiff(path=None):
    import tifffile
    from pyproj import CRS

    with tifffile.TiffFile(path) as tf:
        page = tf.pages[0]
        z = page.asarray().astype(float)
        if z.ndim == 3:
            z = z[..., 0]
        tags = {t.code: t.value for t in page.tags.values()}

    scale = tags.get(33550)
    tie = tags.get(33922)
    if scale is None or tie is None:
        raise ValueError(f"{path.name}: not a georeferenced GeoTIFF (no pixel scale / tie point)")
    sx = float(scale[0])
    sy = float(scale[1])
    i, j, _, X, Y, _ = (float(v) for v in tie[:6])
    geokeys = tags.get(34735, ())
    if len(geokeys) >= 4:
        keys = {geokeys[k]: geokeys[k + 3] for k in range(4, len(geokeys) - 3, 4)}
    else:
        keys = {}
    pixel_is_point = keys.get(1025) == 2
    x0 = X - i * sx + (0 if pixel_is_point else sx / 2)
    y0 = Y + j * sy - (0 if pixel_is_point else sy / 2)
    nod = tags.get(42113)
    if nod is not None:
        try:
            z[z == float(str(nod).strip("\x00 "))] = np.nan
        except ValueError:
            pass
    z[z < -10000.0] = np.nan
    crs = None
    epsg = keys.get(3072) or keys.get(2048)
    if epsg and epsg != 32767:
        crs = CRS.from_epsg(int(epsg))
    return DEM(z, x0, y0, sx, sy, crs, path.stem)


def sample(dem=None, xs=None, ys=None, crs=None):
    """Bilinear DEM values at points (in ``crs``; default: the DEM's own system)."""
    xs = np.asarray(xs, float)
    ys = np.asarray(ys, float)
    if crs and dem.crs and (crs != dem.crs):
        import pyproj

        t = pyproj.Transformer.from_crs(crs, dem.crs, always_xy=True)
        xs, ys = t.transform(xs, ys)

    c = (xs - dem.x0) / dem.dx
    r = (dem.y0 - ys) / dem.dy
    rows, cols = dem.z.shape
    c0 = np.floor(c).astype(int)
    r0 = np.floor(r).astype(int)
    ok = (c0 >= 0) & (r0 >= 0) & (c0 < cols - 1) & (r0 < rows - 1)
    out = np.full(xs.shape, np.nan)
    c0_sub, r0_sub = c0[ok], r0[ok]
    fc = c[ok] - c0_sub
    fr = r[ok] - r0_sub
    z = dem.z
    out[ok] = (
        z[r0_sub, c0_sub] * (1 - fc) * (1 - fr)
        + z[r0_sub, c0_sub + 1] * fc * (1 - fr)
        + z[r0_sub + 1, c0_sub] * (1 - fc) * fr
        + z[r0_sub + 1, c0_sub + 1] * fc * fr
    )
    return out


def _utm_of(dem):
    from litholog.aquifer import utm_epsg

    lon = dem.x0 + (dem.z.shape[1] * dem.dx) / 2
    lat = dem.y0 - (dem.z.shape[0] * dem.dy) / 2
    return f"EPSG:{utm_epsg(lon, lat)}"


def sample_on_grid(dem, model, crs=None):
    X, Y = np.meshgrid(model.x, model.y)
    crs = crs or MODEL_CRS["crs"]
    if dem.crs is not None and crs is None and dem.crs.is_geographic:
        from litholog.aquifer import utm_epsg

        lon = dem.x0 + (dem.z.shape[1] * dem.dx) / 2
        lat = dem.y0 - (dem.z.shape[0] * dem.dy) / 2
        crs = f"EPSG:{utm_epsg(lon, lat)}"
    return sample(dem, X.ravel(), Y.ravel(), crs).reshape(X.shape)


def rectify_collars(project, dem, crs=None, replace: bool = False):
    import pandas as pd

    b = project.boreholes
    ok = b["x"].notna() & b["y"].notna()
    z = np.full(len(b), np.nan)
    z[ok.to_numpy()] = sample(dem, b.loc[ok, "x"], b.loc[ok, "y"], crs or MODEL_CRS["crs"])
    rep = pd.DataFrame({
        "borehole_id": b["borehole_id"],
        "collar": b["elevation"],
        "dem": z,
        "difference": b["elevation"] - z,
    })
    if replace:
        project.boreholes["elevation"] = np.where(np.isfinite(z), z, b["elevation"])
    return rep
