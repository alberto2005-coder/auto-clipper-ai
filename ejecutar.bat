@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
chcp 65001 >nul

echo Comprobando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo Python no encontrado. Abriendo python.org...
    start https://www.python.org/downloads/
    pause
    exit
)

echo Instalando/verificando dependencias...
pip install -q -r requirements.txt

echo.
set "ESCRITORIO="
for /f "usebackq delims=" %%i in (`powershell -Command "[System.Environment]::GetFolderPath('Desktop')"`) do set "ESCRITORIO=%%i"
set "ACCESO=%ESCRITORIO%\Auto-Clipper AI.lnk"

if exist "%ACCESO%" (
    echo El acceso directo ya existe en el escritorio, omitiendo...
) else (
    set /p crear="¿Crear acceso directo en el escritorio? (s/n): "
    if /i "!crear!"=="s" (
        powershell -ExecutionPolicy Bypass -File "%~dp0crear_acceso.ps1" "%~f0" "%~dp0"
    )
)

echo.
echo Iniciando Auto-Clipper AI...
streamlit run gui.py --server.port=8501
pause