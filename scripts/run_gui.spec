# -*- mode: python ; coding: utf-8 -*-
import os
import streamlit
from PyInstaller.utils.hooks import collect_all

# Determinar rutas absolutas basandose en la ubicacion del spec
spec_dir = os.path.dirname(os.path.abspath(SPEC)) if 'SPEC' in globals() else os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(spec_dir, "..")) if os.path.basename(spec_dir).lower() == 'scripts' else spec_dir

# Obtener dinamicamente la ruta de streamlit segun el entorno de ejecucion
streamlit_path = os.path.dirname(streamlit.__file__)

run_gui_script = os.path.join(project_root, 'run_gui.py')
gui_script = os.path.join(project_root, 'gui.py')
main_script = os.path.join(project_root, 'main.py')
src_dir = os.path.join(project_root, 'src')
assets_dir = os.path.join(project_root, 'assets')
icon_path = os.path.join(assets_dir, 'logo.ico')

datas = [
    (streamlit_path, './streamlit'),
    (gui_script, '.'),
    (main_script, '.'),
    (src_dir, './src'),
    (os.path.join(src_dir, 'autoclipper'), './autoclipper'),
]

if os.path.exists(assets_dir):
    datas.append((assets_dir, './assets'))

if os.path.exists(icon_path):
    datas.append((icon_path, '.'))

binaries = []
hiddenimports = [
    'autoclipper',
    'autoclipper.analyzer',
    'autoclipper.subtitle_generator',
    'autoclipper.transcriber',
    'autoclipper.video_editor',
    'soundfile',
    'scipy',
    'tqdm',
    'requests',
]

for package_name in ['streamlit', 'imageio_ffmpeg', 'faster_whisper', 'ctranslate2', 'librosa', 'cv2']:
    tmp_ret = collect_all(package_name)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

a = Analysis(
    [run_gui_script],
    pathex=[src_dir, project_root],
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
    icon=[icon_path] if os.path.exists(icon_path) else None,
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
