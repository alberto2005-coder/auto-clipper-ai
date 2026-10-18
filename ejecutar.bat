@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
chcp 65001 >nul

echo =====================================================
echo   Auto-Clipper AI - Iniciando Aplicacion
echo =====================================================
echo.

REM -- Comprobar y activar entorno virtual
if exist ".venv\Scripts\activate.bat" (
    echo [*] Activando entorno virtual (.venv)...
    call ".venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    echo [*] Activando entorno virtual (venv)...
    call "venv\Scripts\activate.bat"
) else (
    echo [*] Comprobando Python en el sistema...
    python --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python no encontrado en tu equipo.
        echo         Instala Python desde https://www.python.org/downloads/
        pause
        exit /b 1
    )

    echo [*] Verificando dependencias...
    pip install -q -r requirements.txt
)

REM -- Preguntar por acceso directo en el escritorio si no existe
set "ESCRITORIO="
for /f "usebackq delims=" %%i in (`powershell -Command "[System.Environment]::GetFolderPath('Desktop')"`) do set "ESCRITORIO=%%i"
set "ACCESO=%ESCRITORIO%\Auto-Clipper AI.lnk"

if not exist "%ACCESO%" (
    echo.
    set /p crear="¿Deseas crear un acceso directo en el escritorio? (s/n): "
    if /i "!crear!"=="s" (
        powershell -ExecutionPolicy Bypass -File "%~dp0crear_acceso.ps1" "%~f0" "%~dp0"
    )
)

echo.
echo =====================================================
echo   Iniciando interfaz web (Streamlit)...
echo =====================================================
streamlit run gui.py --server.port=8501
if errorlevel 1 (
    echo.
    echo [ERROR] La aplicacion se cerro con errores.
    pause
)