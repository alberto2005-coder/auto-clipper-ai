# -*- mode: python ; coding: utf-8 -*-
import os
import streamlit
from PyInstaller.utils.hooks import collect_all

# Obtener dinamicamente la ruta de streamlit segun el entorno de ejecucion
streamlit_path = os.path.dirname(streamlit.__file__)

datas = [
    (streamlit_path, './streamlit'),
    ('gui.py', '.'),
    ('main.py', '.'),
    ('transcriber.py', '.'),
    ('analyzer.py', '.'),
    ('subtitle_generator.py', '.'),
    ('video_editor.py', '.'),
]

if os.path.exists('logo.ico'):
    datas.append(('logo.ico', '.'))

binaries = []
hiddenimports = []

for package_name in ['streamlit', 'imageio_ffmpeg', 'faster_whisper', 'ctranslate2', 'librosa', 'cv2']:
    tmp_ret = collect_all(package_name)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

a = Analysis(
    ['run_gui.py'],
    pathex=[],
    binaries=binaries,
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
    name='run_gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['logo.ico'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='run_gui',
)
