# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
from pathlib import Path


hiddenimports = []
for package in ["base58", "requests", "solana", "solders", "spl"]:
    hiddenimports += collect_submodules(package)

datas = []
for path in Path("isolated_scripts").rglob("*.py"):
    datas.append((str(path), str(path.parent)))
for path in Path("ts_actions").rglob("*.ts"):
    datas.append((str(path), str(path.parent)))
for path in Path("Roots").glob("*.py"):
    datas.append((str(path), "Roots"))
for path in [
    Path("install_dependencies.py"),
    Path("isolated_scripts/README.md"),
    Path("ts_actions/README.md"),
    Path(".env.example"),
    Path("README.md"),
    Path("requirements.txt"),
    Path("package.json"),
    Path("tsconfig.json"),
]:
    datas.append((str(path), str(path.parent)))


a = Analysis(
    ["solana_tools_dashboard.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Solana Tools",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Solana Tools",
)
