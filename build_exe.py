import subprocess
import sys
import os

def build_executable():
    print("[*] Verificando si PyInstaller está instalado...")
    try:
        import PyInstaller
    except ImportError:
        print("[*] Instalando PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        
    print("[*] Iniciando compilación a ejecutable (.exe)...")
    
    # PyInstaller command:
    # --onefile: Compila todo en un único archivo .exe
    # --name: Nombre del ejecutable
    # --clean: Limpia caches antes de compilar
    cmd = [
        "pyinstaller",
        "--onefile",
        "--name=autoclipper",
        "main.py"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("\n[+] Compilación finalizada exitosamente!")
        print("[+] Encontrarás tu ejecutable listo para usar en la carpeta: 'dist/autoclipper.exe'")
        print("[!] Nota: Recuerda que 'ffmpeg' aún debe estar instalado en el sistema o su ejecutable ffmpeg.exe estar en la misma carpeta que autoclipper.exe.")
    except subprocess.CalledProcessError as e:
        print(f"[!] Error al compilar el ejecutable: {e}")

if __name__ == "__main__":
    build_executable()
