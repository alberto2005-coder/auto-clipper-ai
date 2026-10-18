<div align="center">

# 🎬 Auto-Clipper AI

**Transforma videos largos en clips verticales virales (TikTok, YouTube Shorts, Instagram Reels) usando Inteligencia Artificial.**

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.66-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Faster-Whisper](https://img.shields.io/badge/Faster--Whisper-STT-412991?style=for-the-badge&logo=openai&logoColor=white)](https://github.com/SYSTRAN/faster-whisper)
[![uv](https://img.shields.io/badge/managed%20by-uv-DE5FE9?style=for-the-badge&logo=astral&logoColor=white)](https://github.com/astral-sh/uv)
[![Inno Setup](https://img.shields.io/badge/Inno%20Setup-7-0078D7?style=for-the-badge&logo=windows&logoColor=white)](https://jrsoftware.org/isinfo.php)
[![License](https://img.shields.io/badge/License-Custom%20NC--Attribution-orange.svg?style=for-the-badge)](LICENSE)

</div>

---

## 🌟 Características Principales

- 🎙️ **Transcripción Inteligente**: Transcripción rápida local mediante `faster-whisper` (soporta GPU/CUDA o CPU) o vía API Cloud (Groq / OpenAI Whisper).
- 🧠 **Detección de Momentos Virales**: Análisis semántico con LLMs para encontrar los momentos con mayor gancho, explicando el porqué y asignando puntuaciones de viralidad.
- 💬 **Subtítulos Dinámicos ASS**: Generación automática de subtítulos estilo TikTok/Shorts sincronizados palabra por palabra con fuentes destacadas.
- 📱 **Reencuadre Vertical 9:16**: Ajuste automático del formato horizontal a vertical listo para publicar en redes sociales.
- 💻 **Doble Modo de Uso**: Panel visual intuitivo en **Streamlit** y modo automatizado por **Línea de Comandos (CLI)**.
- 📦 **Listo para Distribución en Windows**: Scripts preparados para compilar a `.exe` (PyInstaller) y generar instaladores profesionales con **Inno Setup 7**.

---

## 🚀 Requisitos Previos

- **Python**: Versión 3.8 o superior (se recomienda 3.10 – 3.13).
- **FFmpeg**: Se gestiona automáticamente mediante `imageio-ffmpeg` (incluido en `requirements.txt`). Si lo prefieres, también puedes tener `ffmpeg` en el `PATH` del sistema.
- **uv** *(Opcional pero muy recomendado)*: Gestor ultra rápido de entornos y paquetes de Python.

---

## 📥 Instalación

### Opción 1: Con `uv` (Recomendado - Ultrarrápido)

```bash
# 1. Clona el repositorio
git clone https://github.com/alberto2005-coder/auto-clipper-ai.git
cd auto-clipper-ai

# 2. Crea el entorno virtual
uv venv

# 3. Instala las dependencias
uv pip install -r requirements.txt
```

### Opción 2: Con `pip` estándar

```bash
# 1. Clona el repositorio
git clone https://github.com/alberto2005-coder/auto-clipper-ai.git
cd auto-clipper-ai

# 2. Crea un entorno virtual
python -m venv .venv

# 3. Activa el entorno
# En Windows (PowerShell):
.venv\Scripts\Activate.ps1
# En Linux/macOS:
source .venv/bin/activate

# 4. Instala las dependencias
pip install -r requirements.txt
```

---

## 🖥️ Uso de la Aplicación

### 1. Interfaz Gráfica (Streamlit)

La forma más sencilla en Windows es hacer doble clic sobre **`ejecutar.bat`**. Este script:
1. Detecta y activa automáticamente el entorno virtual (`.venv`).
2. Comprueba las dependencias necesarias.
3. Te ofrece crear un acceso directo con el icono oficial en el escritorio.
4. Abre la interfaz visual en tu navegador (`http://localhost:8501`).

Si prefieres lanzarlo desde la terminal:

```bash
# Con el entorno virtual activado:
streamlit run gui.py
```

#### Funcionalidades del panel:
- Subir videos locales o indicar rutas en disco.
- Seleccionar tamaño del modelo de Whisper (`tiny`, `base`, `small`, `medium`, `large-v3`).
- Elegir proveedor de IA (Ollama local, Groq o OpenAI).
- Previsualizar los cortes y descargar los clips en 9:16.

---

### 2. Línea de Comandos (CLI)

Ideal para procesamiento por lotes o automatización en scripts:

```bash
python main.py ruta/del/video.mp4 --output_dir clips_salida
```

#### Parámetros disponibles:

| Parámetro | Descripción | Valor por Defecto |
|---|---|---|
| `video_path` | Ruta del video original de entrada | *(Obligatorio)* |
| `--output_dir` | Directorio de salida para los clips | `output_clips` |
| `--model` | Modelo de Whisper (`tiny`, `base`, `small`, `medium`) | `small` |
| `--lang` | Código ISO del idioma del video | `es` |
| `--provider` | Proveedor del LLM (`ollama`, `groq`, `openai`) | `ollama` |
| `--api_url` | URL de la API del proveedor LLM | `http://localhost:11434/api/generate` |
| `--api_key` | Clave API (para Groq u OpenAI) | `None` / Var. Entorno |
| `--llm_model` | Nombre del modelo LLM a consultar | `llama3` / `llama-3.3-70b-versatile` |

#### Ejemplos CLI:

**Con Ollama (100% Local y Gratuito):**
```bash
python main.py podcast.mp4 --output_dir clips --provider ollama --llm_model llama3
```

**Con Groq (Ultrarrápido en la Nube):**
```bash
python main.py podcast.mp4 --output_dir clips --provider groq --api_key TU_GROQ_API_KEY
```

---

## 🏗️ Compilación de Ejecutable e Instalador (Windows)

Este repositorio incluye todo lo necesario para compilar y empaquetar la aplicación como un programa de Windows:

### Paso 1: Generar el Ejecutable (`.exe`)
Ejecuta el script de compilación:
```cmd
crear_exe.bat
```
- Utiliza **PyInstaller** con una configuración optimizada y portable ([run_gui.spec](run_gui.spec)).
- Genera la carpeta distribuible con todas las librerías en `dist\run_gui\`.

### Paso 2: Crear el Instalador con Inno Setup 7
1. Abre [instalador.iss](instalador.iss) en **Inno Setup 7**.
2. Haz clic en **Compile** (`Ctrl + F9`).
3. Se generará el instalador `dist\Instalador_AutoClipperAI.exe` con:
   - Asistente moderno y redimensionable (`WizardStyle=modern`).
   - Soporte para arquitecturas de 64 bits (`x64compatible`).
   - Acceso directo en el Escritorio y Menú Inicio con icono oficial (`logo.ico`).
   - Soporte multilingüe (Español e Inglés).
   - Desinstalador integrado.

---

## 📂 Estructura del Repositorio

```text
auto-clipper-ai/
├── .streamlit/             # Configuración del servidor y temas de Streamlit
├── tests/                  # Pruebas unitarias y de integración
│   └── test_analyzer_retry.py
├── analyzer.py             # Lógica de análisis de transcripción y LLM
├── crear_acceso.ps1        # Script PowerShell para crear acceso directo
├── crear_exe.bat           # Compilador a binario con PyInstaller
├── ejecutar.bat            # Lanzador rápido con detección de .venv
├── gui.py                  # Interfaz gráfica interactiva (Streamlit)
├── instalador.iss          # Script de instalador para Inno Setup 7
├── logo.ico                # Icono de la aplicación
├── main.py                 # Punto de entrada para el modo CLI
├── packages.txt            # Dependencias del sistema (Streamlit Cloud / Debian)
├── requirements.txt        # Dependencias de Python
├── run_gui.py              # Bootstrap para el ejecutable de la GUI
├── run_gui.spec            # Especificación portable de PyInstaller
├── setup.py                # Instalación como paquete de Python
├── subtitle_generator.py   # Creación de subtítulos dinámicos ASS
├── transcriber.py          # Extracción de audio y Whisper STT
└── video_editor.py         # Edición y reencuadre vertical 9:16 con FFmpeg
```

---

## 🧪 Pruebas

Para ejecutar las pruebas del sistema de análisis y tolerancia a fallos del LLM:

```bash
python tests/test_analyzer_retry.py
```

---

## 📄 Licencia

Este proyecto está bajo una **Licencia Personalizada (Uso No Comercial y con Atribución Obligatoria)**:
- ✅ **Uso permitido**: Gratuito para uso personal, educativo, pruebas y desarrollo no comercial.
- ❌ **Prohibida su venta**: Queda terminantemente prohibido vender, revender, alquilar o monetizar este software o cualquier derivado.
- 👤 **Atribución obligatoria**: Cualquier copia, fork o trabajo derivado debe mantener visible y destacada la autoría de **Alberto** y el enlace al repositorio original.

Consulta el archivo [LICENSE](LICENSE) para consultar los términos completos.
