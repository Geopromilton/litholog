"""Headless self-test: start the window, load the demo, build the model, draw, quit."""
from __future__ import annotations

from pathlib import Path
import sys
import time


def run(timeout: float = 300) -> int:
    from PySide6.QtWidgets import QApplication
    from . import theme
    from .mainwindow import DEMO, MainWindow

    app = QApplication.instance() or QApplication(sys.argv)
    theme.apply("dark")
    w = MainWindow()
    w.show()
    w.load(DEMO)

    t0 = time.time()
    while time.time() - t0 < 3.0:
        app.processEvents()
        time.sleep(0.05)

    w.close()
    return 0


def check(report_path: str = "litholog_check.txt") -> int:
    lines = ["LithoLog Studio Self-Check Report", "=" * 40]
    ok = True

    try:
        from PySide6.QtWidgets import QApplication
        from .mainwindow import DEMO, MainWindow
        app = QApplication.instance() or QApplication(sys.argv)
        w = MainWindow()
        w.load(DEMO)
        t0 = time.time()
        while w.project is None and time.time() - t0 < 120:
            app.processEvents()
            time.sleep(0.05)
        if w.project is None:
            raise RuntimeError("demo project did not load within 120 s")
        lines.append(f"PASS: MainWindow initialized with {len(w.project)} boreholes")
        w.close()
    except Exception as e:
        lines.append(f"FAIL: MainWindow test failed: {e}")
        ok = False

    try:
        # Model-building path: catches broken/missing modules that only load when a model is built.
        from .. import aquifer, constraints, strat, validation  # noqa: F401
        from .. import io as lio
        from ..grid import Interp
        from ..horizons import build_horizon_model, horizon_volumes
        p = lio.load_project(DEMO)
        for meth in ("idw", "kriging"):
            m = build_horizon_model(p, 25.0, 1.0, method=Interp(method=meth), boundary=None, dem=None, constraints=None)
            n = len(horizon_volumes(m))
            if not n:
                raise RuntimeError("horizon model has no horizons")
            lines.append(f"PASS: horizon model ({meth}) built with {n} horizons")
    except Exception as e:
        lines.append(f"FAIL: horizon model test failed: {e}")
        ok = False

    Path(report_path).write_text("\n".join(lines) + f"\n\nRESULT: {'PASS' if ok else 'FAIL'}\n", encoding="utf-8")
    return 0 if ok else 1
