@echo off
chcp 65001 >nul
echo =====================================================
echo  Auto-Clipper AI - Compilador de .exe
echo =====================================================

REM -- Verificar logo.ico
if not exist "logo.ico" (
    echo [ERROR] No se encontro logo.ico en esta carpeta.
    echo         Coloca logo.ico junto a este .bat e intentalo de nuevo.
    pause & exit /b 1
)

REM -- Instalar PyInstaller
echo.
echo [1/3] Instalando PyInstaller...
pip install -q pyinstaller
if errorlevel 1 (
    echo [ERROR] No se pudo instalar PyInstaller.
    pause & exit /b 1
)

REM -- Buscar ruta de Streamlit
echo.
echo [2/3] Buscando la ruta de Streamlit...
FOR /F "tokens=*" %%g IN ('python -c "import streamlit, os; print(os.path.dirname(streamlit.__file__))"') do (SET STREAMLIT_PATH=%%g)

if not defined STREAMLIT_PATH (
    echo [ERROR] No se pudo encontrar Streamlit. Asegurate de tenerlo instalado:
    echo         pip install streamlit
    pause & exit /b 1
)
echo        Streamlit encontrado en: %STREAMLIT_PATH%

REM -- Compilar con PyInstaller
echo.
echo [3/3] Compilando la aplicacion en .exe...
echo       Esto puede tardar varios minutos, por favor espera...
echo.

echo [*] Limpiando residuos de compilaciones anteriores (build / dist)...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
echo.

pyinstaller --noconfirm --clean --onedir --console ^
    --icon=logo.ico ^
    --log-level WARN ^
    --collect-all streamlit ^
    --collect-all imageio_ffmpeg ^
    --collect-all faster_whisper ^
    --collect-all ctranslate2 ^
    --collect-all librosa ^
    --collect-all cv2 ^
    --add-data "%STREAMLIT_PATH%;./streamlit" ^
    --add-data "gui.py;." ^
    --add-data "main.py;." ^
    --add-data "transcriber.py;." ^
    --add-data "analyzer.py;." ^
    --add-data "subtitle_generator.py;." ^
    --add-data "video_editor.py;." ^
    run_gui.py

if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller fallo durante la compilacion.
    echo         Revisa los mensajes de error de arriba.
    pause & exit /b 1
)

REM -- Verificar que se genero el exe
if not exist "dist\run_gui\run_gui.exe" (
    echo.
    echo [ERROR] La compilacion termino pero no se encontro dist\run_gui\run_gui.exe.
    pause & exit /b 1
)

echo.
echo =======================================================
echo  Compilacion completada con exito.
echo  Tu programa esta en la carpeta "dist\run_gui".
echo  Ahora puedes compilar el instalador con instalador.iss
echo  usando Inno Setup.
echo =======================================================
pause