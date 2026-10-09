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
        lines.append(f"PASS: MainWindow initialized with {len(w.project)} boreholes")
        w.close()
    except Exception as e:
        lines.append(f"FAIL: MainWindow test failed: {e}")
        ok = False

    Path(report_path).write_text("\n".join(lines) + f"\n\nRESULT: {'PASS' if ok else 'FAIL'}\n", encoding="utf-8")
    return 0 if ok else 1
