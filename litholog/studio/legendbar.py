"""Horizontal, editable legend under the 3D view, and the Layer Properties dialog."""
from __future__ import annotations

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from . import theme


def pattern_preview(lith=None, w=120, h=40) -> QPixmap:
    """The 2D fill pattern as it prints on logs and sections."""
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from ..patterns import draw_interval

    fig = Figure(figsize=(w / 100, h / 100), dpi=100)
    FigureCanvasAgg(fig)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(1, 0)
    ax.set_axis_off()
    if lith is not None:
        draw_interval(ax, 0, 1, 0, 1, lith)
    fig.canvas.draw()
    buf = fig.canvas.buffer_rgba()
    img = QImage(bytes(buf), int(fig.bbox.width), int(fig.bbox.height), QImage.Format_RGBA8888)
    return QPixmap.fromImage(img.copy())


class LegendBar(QWidget):
    edit_requested = Signal(str)
    visibility_changed = Signal(str, bool)
    updated = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.items = []
        self.title = "Lithology"
        self.show_volumes = True
        self.subtitle = ""
        self._hits = []
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        self.hide()

    def set_items(self, items: list, subtitle: str = ""):
        self.items = list(items)
        self.subtitle = subtitle
        if self.items:
            self.show()
        else:
            self.hide()
        self.updateGeometry()
        self.update()

    def set_enabled_bar(self, on: bool):
        self.setVisible(bool(on) and bool(self.items))

    def set_visible_code(self, code: str, visible: bool):
        for it in self.items:
            if getattr(it, "code", "") == code:
                it.visible = visible
        self.update()

    def _label(self, it) -> str:
        code = getattr(it, "code", "")
        name = getattr(it, "name", code)
        return f"{name} ({code})" if name and name != code else code

    def sizeHint(self) -> QSize:
        return QSize(400, 38)

    def minimumSizeHint(self) -> QSize:
        return QSize(200, 32)

    def paintEvent(self, e):
        if not self.items:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(theme.PANEL))

        # Draw items
        x = 12
        y = 8
        box_w = 20
        box_h = 18
        self._hits = []

        fm = p.fontMetrics()
        for it in self.items:
            code = getattr(it, "code", "")
            lbl = self._label(it)
            color = getattr(it, "color", "#888888")
            vis = getattr(it, "visible", True)

            text_w = fm.horizontalAdvance(lbl)
            item_w = box_w + 6 + text_w + 16

            if x + item_w > self.width() - 12:
                break

            rect = QRectF(x, y, box_w, box_h)
            p.fillRect(rect, QColor(color) if vis else QColor(theme.PANEL_DIM))
            p.setPen(QColor(theme.BORDER if not vis else theme.TEXT))
            p.drawRect(rect)

            p.setPen(QColor(theme.TEXT if vis else theme.TEXT_DIM))
            p.drawText(int(x + box_w + 6), int(y + 14), lbl)

            self._hits.append((QRectF(x, y, item_w, box_h), code, vis))
            x += item_w

        p.end()

    def _code_at(self, pos: QPoint) -> tuple[str, bool] | None:
        for r, code, vis in self._hits:
            if r.contains(pos):
                return code, vis
        return None

    def mouseReleaseEvent(self, e):
        hit = self._code_at(e.position().toPoint())
        if hit and e.button() == Qt.LeftButton:
            code, vis = hit
            self._toggle(code, not vis)

    def mouseDoubleClickEvent(self, e):
        hit = self._code_at(e.position().toPoint())
        if hit:
            code, _ = hit
            self.edit_requested.emit(code)

    def contextMenuEvent(self, e):
        hit = self._code_at(e.position().toPoint())
        menu = QMenu(self)
        if hit:
            code, vis = hit
            menu.addAction("Edit Properties...", lambda: self.edit_requested.emit(code))
            menu.addAction("Show Only This Unit", lambda: self._only(code))
        menu.addAction("Show All Units", self._show_all)
        menu.exec(e.globalPos())

    def _toggle(self, code: str, vis: bool):
        self.set_visible_code(code, vis)
        self.visibility_changed.emit(code, vis)

    def _only(self, code: str):
        for it in self.items:
            c = getattr(it, "code", "")
            self._toggle(c, c == code)

    def _show_all(self):
        for it in self.items:
            c = getattr(it, "code", "")
            self._toggle(c, True)


class LayerPropertiesDialog(QDialog):
    def __init__(self, legend=None, codes=None, state=None, current=None, volumes=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Layer Properties")
        self.resize(720, 480)
        self.legend = list(legend or [])
        self.codes = list(codes or [])
        self.volumes = dict(volumes or {})
        self.edits = {}
        self.loaded_legend = None

        h = QHBoxLayout(self)
        self.list = QListWidget()
        self.list.setMinimumWidth(220)
        h.addWidget(self.list)

        right = QVBoxLayout()
        form = QFormLayout()

        self.code_lbl = QLabel()
        self.name_edit = QLineEdit()
        self.color_btn = QPushButton("Choose Color...")
        self.color_btn.clicked.connect(self._pick_color)
        self.pattern_combo = QComboBox()
        self.pattern_combo.setEditable(False)
        self.pattern_combo.addItems([
            "default", "sand", "clay", "gravel", "silt", "limestone",
            "shale", "sandstone", "granite", "basalt", "breccia"
        ])
        self.visible_chk = QCheckBox("Visible in 3D Scene")
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.vol_lbl = QLabel("N/A")

        form.addRow("Code:", self.code_lbl)
        form.addRow("Name:", self.name_edit)
        form.addRow("Color:", self.color_btn)
        form.addRow("Pattern:", self.pattern_combo)
        form.addRow("Visibility:", self.visible_chk)
        form.addRow("Opacity (%):", self.opacity_slider)
        form.addRow("Volume / Area:", self.vol_lbl)
        right.addLayout(form)

        # Buttons
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        right.addWidget(btns)
        h.addLayout(right)

        # Fill list
        for it in self.legend:
            code = getattr(it, "code", "")
            item = QListWidgetItem(f"{getattr(it, 'name', code)} ({code})")
            item.setData(Qt.UserRole, code)
            self.list.addItem(item)
            self.edits[code] = {
                "name": getattr(it, "name", code),
                "color": getattr(it, "color", "#888888"),
                "pattern": getattr(it, "pattern", "default"),
                "visible": getattr(it, "visible", True),
                "opacity": 1.0,
            }

        self.list.currentRowChanged.connect(self._show)
        if self.list.count() > 0:
            self.list.setCurrentRow(0)

    def _show(self, row: int):
        item = self.list.item(row)
        if not item:
            return
        code = item.data(Qt.UserRole)
        data = self.edits.get(code, {})
        self.code_lbl.setText(code)
        self.name_edit.setText(data.get("name", code))
        self.color_btn.setStyleSheet(f"background-color: {data.get('color', '#888888')};")
        self.visible_chk.setChecked(data.get("visible", True))
        self.opacity_slider.setValue(int(data.get("opacity", 1.0) * 100))
        vol = self.volumes.get(code, "N/A")
        self.vol_lbl.setText(str(vol))

    def _pick_color(self):
        item = self.list.currentItem()
        if not item:
            return
        code = item.data(Qt.UserRole)
        cur = self.edits[code].get("color", "#888888")
        col = QColorDialog.getColor(QColor(cur), self, "Select Layer Color")
        if col.isValid():
            self.edits[code]["color"] = col.name()
            self.color_btn.setStyleSheet(f"background-color: {col.name()};")

    def rows(self) -> dict:
        return self.edits
