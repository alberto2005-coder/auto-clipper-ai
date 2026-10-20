<div align="center">

# 🎬 Auto-Clipper AI

**Transforma videos largos en clips verticales virales (TikTok, YouTube Shorts, Instagram Reels) usando Inteligencia Artificial.**

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.66-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Faster-Whisper](https://img.shields.io/badge/Faster--Whisper-STT-412991?style=for-the-badge&logo=openai&logoColor=white)](https://github.com/SYSTRAN/faster-whisper)
[![uv](https://img.shields.io/badge/managed%20by-uv-DE5FE9?style=for-the-badge&logo=astral&logoColor=white)](https://github.com/astral-sh/uv)
[![Inno Setup](https://img.shields.io/badge/Inno%20Setup-7-0078D7?style=for-the-badge&logo=windows&logoColor=white)](https://jrsoftware.org/isinfo.php)
[![License](https://img.shields.io/badge/license-GPL--3.0-blue.svg?style=for-the-badge)](LICENSE)

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
Ejecuta el script de compilación (desde la terminal o con doble clic):
```cmd
scripts\crear_exe.bat
```
- Utiliza **PyInstaller** con una configuración optimizada y portable ([scripts/run_gui.spec](scripts/run_gui.spec)).
- Empaqueta el paquete modular `src/autoclipper` y los recursos de `assets/`.
- Genera la carpeta distribuible con todas las librerías en `dist\run_gui\`.

### Paso 2: Crear el Instalador con Inno Setup 7
1. Abre [installer/instalador.iss](installer/instalador.iss) en **Inno Setup 7**.
2. Haz clic en **Compile** (`Ctrl + F9`).
3. Se generará el instalador `dist\Instalador_AutoClipperAI.exe` con:
   - Asistente moderno y redimensionable (`WizardStyle=modern`).
   - Soporte para arquitecturas de 64 bits (`x64compatible`).
   - Acceso directo en el Escritorio y Menú Inicio con icono oficial ([assets/logo.ico](assets/logo.ico)).
   - Soporte multilingüe (Español e Inglés).
   - Desinstalador integrado.

---

## 📂 Estructura del Repositorio

```text
auto-clipper-ai/
├── .streamlit/             # Configuración del servidor y temas de Streamlit
├── assets/                 # Recursos gráficos (iconos, logos)
│   └── logo.ico
├── installer/              # Archivos de empaquetado para distribución
│   └── instalador.iss      # Script del instalador para Inno Setup 7
├── scripts/                # Scripts de automatización y compilación
│   ├── crear_acceso.ps1    # Generador de acceso directo en escritorio
│   ├── crear_exe.bat       # Compilador a ejecutable portable
│   └── run_gui.spec        # Especificación de empaquetado PyInstaller
├── src/                    # Código fuente del paquete principal
│   └── autoclipper/
│       ├── __init__.py     # Exportaciones principales del paquete
│       ├── analyzer.py     # Lógica de análisis de transcripción y LLMs
│       ├── subtitle_generator.py # Generación de subtítulos dinámicos ASS
│       ├── transcriber.py  # Extracción de audio y Whisper STT
│       └── video_editor.py # Edición, reencuadre vertical 9:16 y mezcla
├── tests/                  # Pruebas unitarias y de integración
│   ├── __init__.py
│   └── test_analyzer_retry.py
├── .gitignore              # Reglas de exclusión para Git
├── ejecutar.bat            # Lanzador rápido raíz en 1 clic
├── gui.py                  # Interfaz gráfica interactiva (Streamlit)
├── LICENSE                 # Licencia GPL-3.0
├── main.py                 # Punto de entrada para el modo CLI
├── packages.txt            # Dependencias del sistema (Streamlit Cloud / Debian)
├── README.md               # Documentación oficial del proyecto
├── requirements.txt        # Dependencias de Python
├── run_gui.py              # Bootstrap del ejecutable compilado
└── setup.py                # Instalación como paquete de Python (src-layout)
```

---

## 🧪 Pruebas

Para ejecutar las pruebas del sistema de análisis y tolerancia a fallos del LLM:

```bash
python tests/test_analyzer_retry.py
```

---

## 📄 Licencia

Este proyecto está bajo la **Licencia GPL-3.0**:
- ✅ **Uso permitido**: Gratuito para uso personal, educativo, pruebas, desarrollo y también comercial.
- 🔁 **Forks y modificaciones**: Permitidos; si distribuyes versiones modificadas, publica su código fuente bajo GPL-3.0 (copyleft).
- 👤 **Atribución**: Conserva el crédito a **Alberto** y el enlace al repositorio original.

Consulta el archivo [LICENSE](LICENSE) para consultar los términos completos.


# 🎬 Auto-Clipper AI

**Turn long videos into viral vertical clips (TikTok, YouTube Shorts, Instagram Reels) using Artificial Intelligence.**

---

## 🌟 Key Features

* 🎙️ **Smart Transcription**: Fast local transcription powered by `faster-whisper` (supports GPU/CUDA or CPU) or via Cloud APIs (Groq / OpenAI Whisper).
* 🧠 **Viral Moment Detection**: Semantic analysis using LLMs to pinpoint high-hook moments, complete with explanations and virality scores.
* 💬 **Dynamic ASS Subtitles**: Automated TikTok/Shorts-style word-by-word synced subtitles with highlighted fonts.
* 📱 **9:16 Vertical Reframing**: Automatic conversion from horizontal to vertical format, ready for social media.
* 💻 **Dual Mode Support**: Intuitive **Streamlit** web dashboard and automated **Command Line Interface (CLI)**.
* 📦 **Windows Distribution Ready**: Preconfigured scripts to compile to `.exe` (PyInstaller) and generate professional installers with **Inno Setup 7**.

---

## 🚀 Prerequisites

* **Python**: Version 3.8 or higher (3.10 – 3.13 recommended).
* **FFmpeg**: Handled automatically via `imageio-ffmpeg` (included in `requirements.txt`). Alternatively, you can have `ffmpeg` installed in your system's `PATH`.
* **uv** *(Optional but highly recommended)*: Ultra-fast Python package and environment manager.

---

## 📥 Installation

### Option 1: Using `uv` (Recommended - Ultra-fast)

```bash
# 1. Clone the repository
git clone https://github.com/alberto2005-coder/auto-clipper-ai.git
cd auto-clipper-ai

# 2. Create the virtual environment
uv venv

# 3. Install dependencies
uv pip install -r requirements.txt

```

### Option 2: Using standard `pip`

```bash
# 1. Clone the repository
git clone https://github.com/alberto2005-coder/auto-clipper-ai.git
cd auto-clipper-ai

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate the environment
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

```

---

## 🖥️ Usage

### 1. Graphical User Interface (Streamlit)

The easiest way on Windows is to double-click **`ejecutar.bat`**. This script:

1. Automatically detects and activates the virtual environment (`.venv`).
2. Checks for required dependencies.
3. Offers to create a desktop shortcut with the official app icon.
4. Launches the visual dashboard in your browser (`http://localhost:8501`).

If you prefer launching from the terminal:

```bash
# With the virtual environment activated:
streamlit run gui.py

```

#### Dashboard Features:

* Upload local video files or specify paths on disk.
* Select Whisper model sizes (`tiny`, `base`, `small`, `medium`, `large-v3`).
* Choose LLM providers (Local Ollama, Groq, or OpenAI).
* Preview cut segments and download final 9:16 vertical clips.

---

### 2. Command Line Interface (CLI)

Ideal for batch processing or pipeline scripting:

```bash
python main.py path/to/video.mp4 --output_dir output_clips

```

#### Available Parameters:

| Parameter | Description | Default Value |
| --- | --- | --- |
| `video_path` | Path to the source input video | *(Required)* |
| `--output_dir` | Directory where output clips are saved | `output_clips` |
| `--model` | Whisper model size (`tiny`, `base`, `small`, `medium`) | `small` |
| `--lang` | ISO language code of the video | `es` |
| `--provider` | LLM provider (`ollama`, `groq`, `openai`) | `ollama` |
| `--api_url` | LLM provider API endpoint URL | `http://localhost:11434/api/generate` |
| `--api_key` | API Key (for Groq or OpenAI) | `None` / Environment Var |
| `--llm_model` | LLM model name to query | `llama3` / `llama-3.3-70b-versatile` |

#### CLI Examples:

**Using Ollama (100% Local and Free):**

```bash
python main.py podcast.mp4 --output_dir clips --provider ollama --llm_model llama3

```

**Using Groq (Ultra-fast Cloud Inference):**

```bash
python main.py podcast.mp4 --output_dir clips --provider groq --api_key YOUR_GROQ_API_KEY

```

---

## 🏗️ Building Executable & Installer (Windows)

This repository includes everything required to package the app into a standalone Windows application:

### Step 1: Build the Executable (`.exe`)

Run the build script (via terminal or double-click):

```cmd
scripts\crear_exe.bat

```

* Uses **PyInstaller** with an optimized, portable configuration ([scripts/run_gui.spec](https://www.google.com/search?q=scripts/run_gui.spec)).
* Packages the `src/autoclipper` modular package and resources from `assets/`.
* Generates the standalone distribution folder containing all libraries at `dist\run_gui\`.

### Step 2: Create the Installer with Inno Setup 7

1. Open [installer/instalador.iss](https://www.google.com/search?q=installer/instalador.iss) in **Inno Setup 7**.
2. Click **Compile** (`Ctrl + F9`).
3. An installer executable `dist\Instalador_AutoClipperAI.exe` will be produced with:
* Modern, resizable UI wizard (`WizardStyle=modern`).
* 64-bit architecture support (`x64compatible`).
* Desktop and Start Menu shortcuts using the official icon ([assets/logo.ico](https://www.google.com/search?q=assets/logo.ico)).
* Multi-language support (Spanish and English).
* Built-in uninstaller.



---

## 📂 Repository Structure

```text
auto-clipper-ai/
├── .streamlit/             # Streamlit server and theme configuration
├── assets/                 # Graphical assets (icons, logos)
│   └── logo.ico
├── installer/              # Distribution packaging files
│   └── instalador.iss      # Inno Setup 7 installer script
├── scripts/                # Automation and build scripts
│   ├── crear_acceso.ps1    # Desktop shortcut generator
│   ├── crear_exe.bat       # Portable executable compiler
│   └── run_gui.spec        # PyInstaller specification file
├── src/                    # Main package source code
│   └── autoclipper/
│       ├── __init__.py     # Core package exports
│       ├── analyzer.py     # Transcript analysis and LLM logic
│       ├── subtitle_generator.py # Dynamic ASS subtitle generator
│       ├── transcriber.py  # Audio extraction and Whisper STT
│       └── video_editor.py # Editing, 9:16 vertical reframing, and mixing
├── tests/                  # Unit and integration tests
│   ├── __init__.py
│   └── test_analyzer_retry.py
├── .gitignore              # Git ignore rules
├── ejecutar.bat            # One-click root launcher
├── gui.py                  # Interactive graphical dashboard (Streamlit)
├── LICENSE                 # GPL-3.0 License
├── main.py                 # CLI entry point
├── packages.txt            # System dependencies (Streamlit Cloud / Debian)
├── README.md               # Official project documentation
├── requirements.txt        # Python dependencies
├── run_gui.py              # Compiled executable bootstrap
└── setup.py                # Python package setup (src-layout)

```

---

## 🧪 Testing

To run tests for the analysis engine and LLM fallback/retry mechanisms:

```bash
python tests/test_analyzer_retry.py

```

---

## 📄 License

This project is licensed under the **GPL-3.0 License**:

* ✅ **Permitted use**: Free for personal use, educational purposes, testing, development, and commercial use.
* 🔁 **Forks and modifications**: Allowed; modified distributions must be open-sourced under the GPL-3.0 copyleft terms.
* 👤 **Attribution**: Retain proper credit to **Alberto** and the link to the original repository.

Refer to the [LICENSE](https://www.google.com/search?q=LICENSE) file for full terms and conditions.
