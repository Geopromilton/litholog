"""Start LithoLog Studio."""
from __future__ import annotations
from litholog.paths import crash_log_path, debug_log_path

import os
import sys


def main(argv: list[str] | None = None) -> int:
    import datetime
    dbg_path = str(debug_log_path())
    def dbg(msg: str):
        try:
            with open(dbg_path, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {msg}\n")
        except Exception:
            pass

    dbg("LithoLog Studio main() started")
    try:
        dbg("Setting QT_AUTO_SCREEN_SCALE_FACTOR...")
        os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
        dbg("Importing PySide6.QtCore...")
        from PySide6.QtCore import Qt, QTimer
        dbg("Importing PySide6.QtGui...")
        from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
        dbg("Importing PySide6.QtWidgets...")
        from PySide6.QtWidgets import QApplication, QSplashScreen

        dbg("PySide6 imported successfully")
        from litholog import __version__
        dbg("Importing theme...")
        from . import theme
        dbg("Importing logo...")
        from .logo import app_icon, pixmap

        dbg("Checking QApplication instance...")
        app = QApplication.instance()
        if app is None:
            dbg("Creating QApplication(sys.argv)...")
            app = QApplication(sys.argv if argv is None else argv)
        app.setApplicationName("LithoLog Studio")
        app.setOrganizationName("LithoLog")
        dbg("QApplication instance created")
        
        mode = theme.saved_mode()
        dbg(f"Saved mode: {mode}")
        theme.apply(app, mode)
        dbg("Theme applied")
        
        app.setWindowIcon(app_icon())

        dbg("Building splash pixmap...")
        pm = QPixmap(520, 310)
        pm.fill(QColor(theme.BG))
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(0, 0, 520, 6, QColor(theme.ACCENT))
        p.drawPixmap(42, 40, pixmap(72))
        p.setPen(QColor(theme.TEXT))
        f = QFont("Inter", 24)
        f.setBold(True)
        p.setFont(f)
        p.drawText(130, 85, "LithoLog")
        fm = p.fontMetrics()
        w1 = fm.horizontalAdvance("LithoLog")
        p.setPen(QColor(theme.ACCENT))
        p.drawText(130 + w1 + 10, 85, "Studio")

        p.setPen(QColor(theme.TEXT_DIM))
        p.setFont(QFont("Inter", 11))
        p.drawText(42, 162, "Borehole logs · sections · maps · 3D geological models")
        p.drawText(42, 186, "Geology · hydrogeology · geochemistry · GIS · mining")
        p.drawText(42, 285, f"Version {__version__} · open source (MIT)")
        p.end()

        dbg("Showing splash screen...")
        splash = QSplashScreen(pm)
        splash.show()
        app.processEvents()
        dbg("Splash screen shown")

        dbg("Importing MainWindow...")
        from .mainwindow import MainWindow
        dbg("MainWindow imported. Instantiating MainWindow...")
        w = MainWindow()
        dbg("MainWindow instantiated. Showing MainWindow...")
        w.show()
        splash.finish(w)
        dbg("MainWindow shown and splash finished")

        args = sys.argv[1:] if argv is None else argv[1:]
        if args:
            QTimer.singleShot(200, lambda: w.load(args[0]))

        dbg("Entering app.exec()...")
        ret = app.exec()
        dbg(f"app.exec() exited with code {ret}")
        return ret
    except BaseException as e:
        import traceback
        err_msg = traceback.format_exc()
        dbg(f"CRASH OCCURRED ({type(e).__name__}):\n{err_msg}")
        try:
            with open(crash_log_path(), "w", encoding="utf-8") as f:
                f.write(err_msg)
            from PySide6.QtWidgets import QApplication, QMessageBox
            app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(None, "LithoLog Studio Startup Error", f"Error during startup:\n\n{err_msg}")
        except Exception as e2:
            dbg(f"Failed to show crash dialog: {e2}")
        return 1



if __name__ == "__main__":
    sys.exit(main())
