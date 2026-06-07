import sys
import os
import socket
import streamlit.web.cli as stcli


def _find_free_port(start: int = 8501) -> int:
    """Returns the first free TCP port in range [start, start+20)."""
    for port in range(start, start + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", port)) != 0:
                return port
    return start  # fallback: try the default and let Streamlit handle the conflict


def main():
    # Determinar el directorio base (funciona tanto en script como compilado en .exe)
    if getattr(sys, "frozen", False):
        bundle_dir = sys._MEIPASS
    else:
        bundle_dir = os.path.dirname(os.path.abspath(__file__))

    gui_path = os.path.join(bundle_dir, "gui.py")

    port = _find_free_port(8501)
    if port != 8501:
        print(f"[*] Puerto 8501 ocupado. Usando puerto {port}.")

    # Configurar los argumentos internos para lanzar Streamlit
    os.environ["STREAMLIT_SERVER_PORT"] = str(port)
    sys.argv = [
        "streamlit", "run", gui_path,
        f"--server.port={port}",
        "--global.developmentMode=false",
    ]

    sys.exit(stcli.main())


if __name__ == "__main__":
    main()