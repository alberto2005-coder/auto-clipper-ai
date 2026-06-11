import sys
import os
import socket
import asyncio
import streamlit.web.cli as stcli


if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception as e:
        print(f"[*] Warning: Could not set WindowsSelectorEventLoopPolicy: {e}")


def _find_free_port(start: int = 8501) -> int:
    """Returns the first free TCP port in range [start, start+20)."""
    for port in range(start, start + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", port)) != 0:
                return port
    return start  # fallback: try the default and let Streamlit handle the conflict


def main():
    print("==================================================")
    print("🎬 STARTING AUTO-CLIPPER AI BOOTSTRAP...")
    print("==================================================")
    
    # Determinar el directorio base (funciona tanto en script como compilado en .exe)
    if getattr(sys, "frozen", False):
        bundle_dir = sys._MEIPASS
        print(f"[*] Running in COMPILED (PyInstaller) mode.")
        print(f"[*] Bundle directory (_MEIPASS): {bundle_dir}")
    else:
        bundle_dir = os.path.dirname(os.path.abspath(__file__))
        print(f"[*] Running in SOURCE (development) mode.")
        print(f"[*] Directory: {bundle_dir}")

    gui_path = os.path.join(bundle_dir, "gui.py")
    print(f"[*] Target UI script path: {gui_path}")
    if not os.path.exists(gui_path):
        print(f"[FATAL] Target UI script 'gui.py' not found at expected path!")

    port = _find_free_port(8501)
    print(f"[*] Resolving server port. Selected port: {port}")

    # Configurar los argumentos internos para lanzar Streamlit
    print(f"[*] Starting Streamlit web server on http://localhost:{port} ...")
    os.environ["STREAMLIT_SERVER_PORT"] = str(port)
    sys.argv = [
        "streamlit", "run", gui_path,
        f"--server.port={port}",
        "--global.developmentMode=false",
        "--server.enableWebsocketCompression=false",
    ]

    sys.exit(stcli.main())


if __name__ == "__main__":
    main()