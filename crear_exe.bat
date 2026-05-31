@echo off
chcp 65001 >nul
echo Instalando PyInstaller...
pip install pyinstaller

echo.
echo Buscando la ruta de Streamlit en tu sistema...
FOR /F "tokens=*" %%g IN ('python -c "import streamlit, os; print(os.path.dirname(streamlit.__file__))"') do (SET STREAMLIT_PATH=%%g)

echo.
echo Compilando la aplicacion en un .exe...
echo Esto puede tardar varios minutos, por favor espera...

pyinstaller --noconfirm --clean --onedir --console --icon=NONE --collect-all streamlit --collect-all imageio_ffmpeg --collect-all faster_whisper --collect-all ctranslate2 --collect-all librosa --add-data "%STREAMLIT_PATH%;./streamlit" --add-data "gui.py;." --add-data "main.py;." --add-data "transcriber.py;." --add-data "analyzer.py;." --add-data "subtitle_generator.py;." --add-data "video_editor.py;." run_gui.py

echo.
echo =======================================================
echo Proceso completado. Tu programa esta en la carpeta "dist\run_gui".
pause