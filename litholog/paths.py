"""Per-user locations for logs and exports (no hard-coded drive letters).

``LITHOLOG_HOME`` overrides the base folder. Otherwise logs go to
``%LOCALAPPDATA%\\LithoLog Studio`` on Windows and ``~/.litholog`` elsewhere,
and exports go to ``~/Documents/LithoLog Studio/exports``.
"""
from __future__ import annotations

import os
from pathlib import Path


def app_data_dir() -> Path:
    env = os.environ.get("LITHOLOG_HOME")
    if env:
        base = Path(env)
    elif os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        base = Path(os.environ["LOCALAPPDATA"]) / "LithoLog Studio"
    else:
        base = Path.home() / ".litholog"
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return base


def debug_log_path() -> Path:
    return app_data_dir() / "studio_debug.log"


def crash_log_path() -> Path:
    return app_data_dir() / "crash_log.txt"


def exports_dir() -> Path:
    env = os.environ.get("LITHOLOG_HOME")
    base = Path(env) / "exports" if env else Path.home() / "Documents" / "LithoLog Studio" / "exports"
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError:
        base = app_data_dir() / "exports"
        base.mkdir(parents=True, exist_ok=True)
    return base
