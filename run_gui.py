import sys
import os
import streamlit.web.cli as stcli

def main():
    # Determinar el directorio base (funciona tanto en script como compilado en .exe)
    if getattr(sys, 'frozen', False):
        bundle_dir = sys._MEIPASS
    else:
        bundle_dir = os.path.dirname(os.path.abspath(__file__))
        
    gui_path = os.path.join(bundle_dir, "gui.py")
    
    # Configurar los argumentos internos para lanzar Streamlit
    os.environ["STREAMLIT_SERVER_PORT"] = "8501"
    sys.argv = ["streamlit", "run", gui_path, "--global.developmentMode=false"]
    
    sys.exit(stcli.main())

if __name__ == "__main__":
    main()