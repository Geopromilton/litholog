# PyInstaller spec for LithoLog Studio (one-folder build).
# Build with:  powershell -ExecutionPolicy Bypass -File build_exe.ps1
from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = [("litholog/data", "litholog/data"), ("litholog/fonts", "litholog/fonts")]
binaries = []
hiddenimports = collect_submodules("litholog")

for pkg in ("pyvista", "pyvistaqt", "qtawesome", "pyproj", "skimage", "scipy.spatial.transform"):
    try:
        d, b, h = collect_all(pkg)
    except Exception:
        continue
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ["litholog_studio_entry.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["streamlit", "tkinter", "IPython", "pytest", "kaleido"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="LithoLogStudio", console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="LithoLogStudio")
