"""Rendering helpers for the 3D view: colour enhancement, seamless textures, crisp text."""
from __future__ import annotations

import colorsys
from functools import lru_cache
import numpy as np


def rgb(color: str) -> tuple[float, float, float]:
    from matplotlib.colors import to_rgb
    return to_rgb(color)


def enhance(color: str, saturation: float = 1.15, value: float = 1.05) -> str:
    """A livelier version of a (often pastel) legend colour for 3D display."""
    r, g, b = rgb(color)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    s = min(1.0, max(0.0, s * saturation))
    v = min(1.0, max(0.0, v * value))
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    from matplotlib.colors import to_hex
    return to_hex((r, g, b))


def darker(color: str, f: float = 0.7) -> str:
    r, g, b = rgb(color)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    v *= f
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    from matplotlib.colors import to_hex
    return to_hex((r, g, b))


def _periodic_noise(n: int, seed: int, slope: float) -> np.ndarray:
    """Tileable 1/f noise in [-1, 1] (built in the frequency domain, so it wraps seamlessly)."""
    rng = np.random.default_rng(seed)
    f = np.fft.fftfreq(n)
    k = np.sqrt(f[:, None] ** 2 + f[None, :] ** 2)
    k[0, 0] = 1.0
    spec = (rng.normal(size=(n, n)) + 1j * rng.normal(size=(n, n))) / (k ** slope)
    spec[0, 0] = 0.0
    img = np.real(np.fft.ifft2(spec))
    img -= img.mean()
    return img / (np.abs(img).max() + 1e-12)


@lru_cache(maxsize=64)
def grain_texture(color: str, seed: int = 0, n: int = 256, strength: float = 0.16) -> np.ndarray:
    base = np.array(rgb(color))
    noise = 0.65 * _periodic_noise(n, seed, 1.9) + 0.35 * _periodic_noise(n, seed + 101, 1.1)
    speck = _periodic_noise(n, seed + 7, 0.3)
    shade = 1.0 + strength * noise - 0.08 * (speck > 0.72)
    img = np.clip(base[None, None, :] * shade[..., None], 0.0, 1.0)
    return (img * 255).astype(np.uint8)


@lru_cache(maxsize=64)
def pattern_texture(code: str, name: str, color: str, pattern: str, n: int = 512) -> np.ndarray:
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from ..patterns import LithType, draw_interval

    size_in = 2.3622
    fig = Figure(figsize=(size_in, size_in), dpi=n / size_in)
    FigureCanvasAgg(fig)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(1, 0)
    ax.set_axis_off()
    draw_interval(ax, 0, 1, 0, 1, LithType(code, name, color, pattern), edge=False)
    fig.canvas.draw()
    img = np.asarray(fig.canvas.buffer_rgba())[..., :3].copy().astype(float)
    b = max(2, n // 64)
    w = np.linspace(0, 1, b)[:, None]
    wr = w[:, :, None]
    img[:b] = img[:b] * wr + img[-b:][::-1] * (1.0 - wr)
    wc = w.T[:, :, None]
    img[:, :b] = img[:, :b] * wc + img[:, -b:][:, ::-1] * (1.0 - wc)
    return img.astype(np.uint8)


def triplanar_tcoords(points: np.ndarray, normals: np.ndarray, tile: float, tile_z: float) -> np.ndarray:
    """Texture coordinates projected along each vertex's dominant normal axis."""
    ax = np.abs(normals).argmax(1)
    u = np.where(ax == 0, points[:, 1] / tile, points[:, 0] / tile)
    v = np.where(ax == 2, points[:, 1] / tile, points[:, 2] / tile_z)
    return np.column_stack([u, v]).astype(np.float32)


def style_text(prop, size: int = 11, bold: bool = False, color: str | None = None, weight: str = "semibold"):
    """Use the bundled Inter font for a vtkTextProperty."""
    try:
        from ..typeface import available, path
        if available():
            prop.SetFontFamily(0)
            prop.SetFontFile(str(path(weight if bold else "regular")))
    except Exception:
        pass
    prop.SetFontSize(size)
    prop.SetBold(int(bold))
    if color is not None:
        r, g, b = rgb(color)
        prop.SetColor(r, g, b)


def _text_props(prop) -> list:
    """Every vtkTextProperty a view prop draws with (labels, titles, captions)."""
    out = []
    for getter in ("GetTextProperty", "GetCaptionTextProperty", "GetTitleTextProperty", "GetLabelTextProperty"):
        f = getattr(prop, getter, None)
        if f is None:
            continue
        if getter in ("GetTitleTextProperty", "GetLabelTextProperty") and hasattr(prop, "IsA") and prop.IsA("vtkCubeAxesActor"):
            for i in range(3):
                try:
                    out.append(f(i))
                except (TypeError, Exception):
                    pass
        else:
            try:
                out.append(f())
            except (TypeError, Exception):
                pass
    if hasattr(prop, "GetMapper"):
        mapper = prop.GetMapper()
        if mapper and hasattr(mapper, "GetTextProperty"):
            try:
                out.append(mapper.GetTextProperty())
            except Exception:
                pass
    return [t for t in out if t is not None]


class ScaledProps:
    """Temporarily multiply font sizes and line widths of the given props by ``f`` (for big renders)."""

    def __init__(self, props, f: float):
        self.props = list(props)
        self.f = float(f)
        self.undo = []

    def __enter__(self):
        for p in self.props:
            for tp in _text_props(p):
                sz = tp.GetFontSize()
                if sz > 0:
                    tp.SetFontSize(int(round(sz * self.f)))
                    self.undo.append(lambda tp=tp, sz=sz: tp.SetFontSize(sz))
            if hasattr(p, "GetProperty"):
                pr = p.GetProperty()
                if hasattr(pr, "GetLineWidth"):
                    lw = pr.GetLineWidth()
                    pr.SetLineWidth(lw * self.f)
                    self.undo.append(lambda pr=pr, lw=lw: pr.SetLineWidth(lw))
        return self

    def __exit__(self, *exc):
        for u in reversed(self.undo):
            u()
