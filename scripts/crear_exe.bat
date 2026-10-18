@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0.."
chcp 65001 >nul

echo =====================================================
echo  Auto-Clipper AI - Compilador de Ejecutable (.exe)
echo =====================================================
echo.

REM -- Verificar presencia de icono
if not exist "assets\logo.ico" (
    if not exist "logo.ico" (
        echo [ERROR] No se encontro logo.ico en assets\ ni en la raiz del proyecto.
        pause & exit /b 1
    )
)

REM -- Activar entorno virtual preferente
if exist ".venv\Scripts\activate.bat" (
    echo [*] Activando entorno virtual (.venv)...
    call ".venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    echo [*] Activando entorno virtual (venv)...
    call "venv\Scripts\activate.bat"
)

REM -- Verificar e instalar PyInstaller en el entorno
echo.
echo [1/3] Verificando PyInstaller...
python -m pip install -q pyinstaller
if errorlevel 1 (
    echo [ERROR] No se pudo instalar o encontrar PyInstaller.
    pause & exit /b 1
)

REM -- Limpiar carpetas temporales anteriores
echo.
echo [2/3] Limpiando carpetas de compilaciones anteriores (build / dist)...
if exist "build" rmdir /s /q "build"
if exist "dist\run_gui" rmdir /s /q "dist\run_gui"

REM -- Compilar utilizando el archivo scripts\run_gui.spec portable
echo.
echo [3/3] Compilando la aplicacion con PyInstaller (scripts\run_gui.spec)...
echo       Esto puede tardar varios minutos dependiendo de tu CPU...
echo.

pyinstaller --noconfirm --clean scripts\run_gui.spec

if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller fallo durante la compilacion.
    echo         Revisa los mensajes de error mostrados arriba.
    pause & exit /b 1
)

REM -- Verificar que el ejecutable existe
if not exist "dist\run_gui\run_gui.exe" (
    echo.
    echo [ERROR] La compilacion finalizo pero no se genero dist\run_gui\run_gui.exe.
    pause & exit /b 1
)

echo.
echo =======================================================
echo  [OK] Compilacion completada con exito.
echo  Los archivos generados estan en: "dist\run_gui"
echo.
echo  Siguiente paso:
echo  Puedes compilar el instalador con Inno Setup 7 abriendo:
echo  "installer\instalador.iss"
echo =======================================================
pause