# Source Generated with Decompyle++
# File: projectfile.pyc (Python 3.12)

'''LithoLog project files (.llproj): JSON with data paths and settings.

Paths are stored relative to the project file when possible, so a project
folder can be copied to another computer.
'''
from __future__ import annotations
import json
import os
from pathlib import Path
FORMAT = 'litholog-project'
VERSION = 1

def _rel(p = None, base = None):
    if not p:
        return None
    
    try:
        return os.path.relpath(Path(p).resolve(), base)
    except ValueError:
        return 



def save(path, name, data, legend, boundary, settings, dem = (None, None, None, None)):
    path = Path(path)
    base = path.resolve().parent
    if not settings:
        settings
    doc = {
        'format': FORMAT,
        'version': VERSION,
        'name': name,
        'data': _rel(data, base),
        'legend': _rel(legend, base),
        'boundary': _rel(boundary, base),
        'dem': _rel(dem, base),
        'settings': { } }
    path.write_text(json.dumps(doc, indent = 2))
    return path


def load(path = None):
    path = Path(path)
    doc = json.loads(path.read_text())
    if doc.get('format') != FORMAT:
        raise ValueError(f'''{path.name} is not a LithoLog project file''')
    base = path.resolve().parent
    for k in ('data', 'legend', 'boundary', 'dem'):
        if not doc.get(k):
            continue
        p = Path(doc[k])
        doc[k] = str(p if p.is_absolute() else (base / p).resolve())
    if not doc.get('data') or Path(doc['data']).exists():
        raise FileNotFoundError(f'''Borehole data not found: {doc.get('data')}''')
    doc.setdefault('settings', { })
    return doc

