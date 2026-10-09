"""Google Earth KMZ export for 3D boreholes, collars, and water table.

Generates georeferenced .kmz archives viewable in Google Earth Desktop & Web.
Boreholes are extruded in true 3D elevation with lithology color coding,
and collar placemarks feature rich HTML description cards.
"""

from __future__ import annotations

import html
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from .patterns import Legend
from .project import Project


def _hex_to_kml_color(hex_str: str, alpha: str = "ff") -> str:
    """Convert #RRGGBB hex to KML aabbggrr format."""
    hex_str = hex_str.lstrip("#")
    if len(hex_str) != 6:
        return f"{alpha}ffffff"
    r = hex_str[0:2]
    g = hex_str[2:4]
    b = hex_str[4:6]
    return f"{alpha}{b}{g}{r}"


def _detect_utm_epsg(x: float, y: float) -> int | None:
    """Guess UTM EPSG from typical coordinate ranges if in Northern hemisphere (or 327XX for South)."""
    # If easting is in 100_000..900_000 and northing is in 0..10_000_000:
    # A rough guess if user didn't specify CRS, or prompt for CRS.
    return None


def export_kmz(project: Project, path: Path | str, crs: str | None = None,
               legend: Legend | None = None) -> Path:
    """Export project boreholes and lithology sticks to a Google Earth KMZ file.

    Parameters
    ----------
    project : Project
        The LithoLog project.
    path : Path or str
        Output file path (must end with .kmz).
    crs : str, optional
        Coordinate reference system of the borehole X/Y, e.g. "EPSG:32643".
        If None, attempts to detect if coordinates are already WGS84 (lon/lat).
    legend : Legend, optional
        Lithology legend for interval colors and names.
    """
    from pyproj import Transformer

    legend = legend or project.legend
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Coordinate transformation
    transformer = None
    if crs:
        transformer = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    else:
        # Check if coordinates look like degrees
        xs = project.boreholes["x"].dropna()
        ys = project.boreholes["y"].dropna()
        if len(xs) and len(ys):
            if xs.min() >= -180 and xs.max() <= 180 and ys.min() >= -90 and ys.max() <= 90:
                transformer = None  # already lon/lat
            else:
                # Common fallback or user should provide CRS
                pass

    kml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>\n',
        '<kml xmlns="http://www.opengis.net/kml/2.2">\n',
        '<Document>\n',
        f'  <name>{html.escape(project.name)}</name>\n',
        '  <open>1</open>\n',
    ]

    # Shared Styles for lithologies
    seen_codes = set()
    for bh in project:
        for c in bh.lithology["code"].dropna():
            seen_codes.add(str(c).strip().upper())

    for code in sorted(seen_codes):
        ltype = legend.get(code)
        kml_col = _hex_to_kml_color(ltype.color)
        kml_parts.append(
            f'  <Style id="style_{code}">\n'
            f'    <LineStyle>\n'
            f'      <color>{kml_col}</color>\n'
            f'      <width>6</width>\n'
            f'    </LineStyle>\n'
            f'    <PolyStyle>\n'
            f'      <color>{kml_col}</color>\n'
            f'    </PolyStyle>\n'
            f'  </Style>\n'
        )

    # Style for collar points
    kml_parts.append(
        '  <Style id="collar_style">\n'
        '    <IconStyle>\n'
        '      <scale>1.1</scale>\n'
        '      <Icon>\n'
        '        <href>http://maps.google.com/mapfiles/kml/shapes/target.png</href>\n'
        '      </Icon>\n'
        '    </IconStyle>\n'
        '  </Style>\n'
    )

    # Folder 1: Collars
    kml_parts.append('  <Folder>\n    <name>Borehole Collars</name>\n')

    for bh in project:
        if pd.isna(bh.x) or pd.isna(bh.y):
            continue
        lon, lat = bh.x, bh.y
        if transformer:
            lon, lat = transformer.transform(bh.x, bh.y)
        elev = bh.elevation if bh.has_elevation else 0.0
        depth = bh.depth or 0.0

        # Construct popup HTML card
        rows_html = [
            f"<tr><td><b>Easting (X):</b></td><td>{bh.x:.2f}</td></tr>",
            f"<tr><td><b>Northing (Y):</b></td><td>{bh.y:.2f}</td></tr>",
            f"<tr><td><b>Elevation:</b></td><td>{elev:.2f} m amsl</td></tr>",
            f"<tr><td><b>Total Depth:</b></td><td>{depth:.2f} m</td></tr>",
        ]
        for k, v in bh.info.items():
            rows_html.append(f"<tr><td><b>{html.escape(str(k))}:</b></td><td>{html.escape(str(v))}</td></tr>")

        wl = bh.water_levels.dropna(subset=["depth"])
        if len(wl):
            dtw = wl.iloc[-1]["depth"]
            wl_elev = elev - dtw if bh.has_elevation else 0.0
            rows_html.append(f"<tr><td><b>Depth to Water:</b></td><td>{dtw:.2f} m bgl</td></tr>")
            rows_html.append(f"<tr><td><b>Water Elevation:</b></td><td>{wl_elev:.2f} m amsl</td></tr>")

        # Lithology table in popup
        lith_rows = []
        for _, r in bh.lithology.iterrows():
            f, t, c, desc = r.get("from"), r.get("to"), str(r.get("code", "")).strip().upper(), r.get("description", "")
            if pd.isna(f) or pd.isna(t):
                continue
            lt = legend.get(c)
            desc_str = f" - {html.escape(str(desc))}" if pd.notna(desc) and str(desc).strip() else ""
            lith_rows.append(f"<tr><td>{f:.1f} - {t:.1f} m</td>"
                             f"<td><span style='color:{lt.color}; font-weight:bold;'>&#9632; {c}</span></td>"
                             f"<td>{html.escape(lt.name)}{desc_str}</td></tr>")

        desc_html = (
            f"<div style='font-family:sans-serif; min-width:260px;'>"
            f"<h3 style='margin:0 0 8px 0; color:#1F3A5F;'>Borehole: {html.escape(bh.id)}</h3>"
            f"<table style='width:100%; border-collapse:collapse; font-size:12px;' border='1' cellpadding='4'>"
            f"{''.join(rows_html)}"
            f"</table>"
        )
        if lith_rows:
            desc_html += (
                f"<h4 style='margin:10px 0 4px 0;'>Lithology Log</h4>"
                f"<table style='width:100%; border-collapse:collapse; font-size:11px;' border='1' cellpadding='3'>"
                f"<tr style='background:#f0f0f0;'><th>Depth</th><th>Code</th><th>Lithology</th></tr>"
                f"{''.join(lith_rows)}"
                f"</table>"
            )
        desc_html += "</div>"

        kml_parts.append(
            f'    <Placemark>\n'
            f'      <name>{html.escape(bh.id)}</name>\n'
            f'      <styleUrl>#collar_style</styleUrl>\n'
            f'      <description><![CDATA[{desc_html}]]></description>\n'
            f'      <Point>\n'
            f'        <altitudeMode>absolute</altitudeMode>\n'
            f'        <coordinates>{lon:.7f},{lat:.7f},{elev:.2f}</coordinates>\n'
            f'      </Point>\n'
            f'    </Placemark>\n'
        )

    kml_parts.append('  </Folder>\n')

    # Folder 2: 3D Lithology Sticks
    kml_parts.append('  <Folder>\n    <name>3D Lithology Sticks</name>\n')

    for bh in project:
        if pd.isna(bh.x) or pd.isna(bh.y):
            continue
        lon, lat = bh.x, bh.y
        if transformer:
            lon, lat = transformer.transform(bh.x, bh.y)
        elev = bh.elevation if bh.has_elevation else 0.0

        for _, r in bh.lithology.iterrows():
            f, t, c = r.get("from"), r.get("to"), str(r.get("code", "")).strip().upper()
            if pd.isna(f) or pd.isna(t) or t <= f:
                continue
            z_top = elev - f
            z_bot = elev - t
            lt = legend.get(c)

            kml_parts.append(
                f'    <Placemark>\n'
                f'      <name>{html.escape(bh.id)}: {c} ({f:.1f}-{t:.1f}m)</name>\n'
                f'      <styleUrl>#style_{c}</styleUrl>\n'
                f'      <LineString>\n'
                f'        <extrude>0</extrude>\n'
                f'        <tessellate>1</tessellate>\n'
                f'        <altitudeMode>absolute</altitudeMode>\n'
                f'        <coordinates>\n'
                f'          {lon:.7f},{lat:.7f},{z_top:.2f}\n'
                f'          {lon:.7f},{lat:.7f},{z_bot:.2f}\n'
                f'        </coordinates>\n'
                f'      </LineString>\n'
                f'    </Placemark>\n'
            )

    kml_parts.append('  </Folder>\n')
    kml_parts.append('</Document>\n</kml>\n')

    kml_str = "".join(kml_parts)

    # Package into a KMZ (zipped archive containing doc.kml)
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("doc.kml", kml_str.encode("utf-8"))

    return out_path
