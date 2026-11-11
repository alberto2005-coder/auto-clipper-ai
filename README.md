# 🎬 Auto-Clipper AI

[Español](#español) · [English](#english)

---

## Español

### Índice

- [Descripción](#descripción)
- [Características](#características)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Uso: interfaz gráfica](#uso-interfaz-gráfica)
- [Uso: línea de comandos](#uso-línea-de-comandos)
- [Compilar ejecutable e instalador](#compilar-ejecutable-e-instalador)
- [Estructura del repositorio](#estructura-del-repositorio)
- [Pruebas](#pruebas)
- [Licencia](#licencia)

### Descripción

**Auto-Clipper AI** transforma vídeos largos en **clips verticales** listos para TikTok, YouTube Shorts e Instagram Reels usando inteligencia artificial. El programa transcribe el audio, analiza la transcripción para localizar los momentos con más gancho, genera subtítulos animados y recorta en 9:16.

Todo el procesamiento puede hacerse **en local** con `faster-whisper` y Ollama, o apoyarse en APIs en la nube (Groq u OpenAI) si se prefiere velocidad.

### Características

- 🎙️ **Transcripción rápida** con `faster-whisper` (GPU/CUDA o CPU) o por API (Groq / OpenAI Whisper).
- 🧠 **Detección de momentos virales** con LLM: explica el porqué de cada corte y le asigna una puntuación de viralidad.
- 💬 **Subtítulos ASS dinámicos** estilo TikTok, sincronizados palabra por palabra y con fuentes destacadas.
- 📱 **Reencuadre vertical 9:16** automático desde el formato horizontal.
- 💻 **Doble modo**: panel visual en Streamlit y modo automatizado por línea de comandos.
- 📦 **Listo para Windows**: scripts para compilar a `.exe` con PyInstaller y generar un instalador con Inno Setup 7.

### Requisitos

- **Python 3.8+** (recomendado 3.10 – 3.13).
- **FFmpeg**: se gestiona solo mediante `imageio-ffmpeg`, incluido en `requirements.txt`. También puedes tener `ffmpeg` en el `PATH`.
- **uv** (opcional pero recomendado): gestor rápido de entornos y paquetes.

### Instalación

**Opción 1 — con `uv` (recomendada)**

```bash
git clone https://github.com/alberto2005-coder/auto-clipper-ai.git
cd auto-clipper-ai
uv venv
uv pip install -r requirements.txt
```

**Opción 2 — con `pip`**

```bash
git clone https://github.com/alberto2005-coder/auto-clipper-ai.git
cd auto-clipper-ai
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### Uso: interfaz gráfica

En Windows, haz doble clic en **`ejecutar.bat`**. El script activa el entorno virtual, comprueba las dependencias, ofrece crear un acceso directo con el icono oficial y abre la interfaz en el navegador (`http://localhost:8501`).

Desde la terminal:

```bash
streamlit run gui.py
```

El panel permite:

- Subir vídeos locales o indicar rutas en disco.
- Elegir el tamaño del modelo de Whisper (`tiny`, `base`, `small`, `medium`, `large-v3`).
- Elegir proveedor de IA: Ollama local, Groq u OpenAI.
- Previsualizar los cortes y descargar los clips en 9:16.

### Uso: línea de comandos

```bash
python main.py ruta/del/video.mp4 --output_dir clips_salida
```

| Parámetro | Descripción | Valor por defecto |
|---|---|---|
| `video_path` | Vídeo de entrada | *(obligatorio)* |
| `--output_dir` | Carpeta de salida de los clips | `output_clips` |
| `--model` | Modelo Whisper (`tiny`, `base`, `small`, `medium`) | `small` |
| `--lang` | Código ISO del idioma del vídeo | `es` |
| `--provider` | Proveedor del LLM (`ollama`, `groq`, `openai`) | `ollama` |
| `--api_url` | URL de la API del LLM | `http://localhost:11434/api/generate` |
| `--api_key` | Clave API (Groq u OpenAI) | `None` / variable de entorno |
| `--llm_model` | Modelo del LLM | `llama3` / `llama-3.3-70b-versatile` |

**Con Ollama (100 % local y gratis)**

```bash
python main.py podcast.mp4 --output_dir clips --provider ollama --llm_model llama3
```

**Con Groq (nube, muy rápido)**

```bash
python main.py podcast.mp4 --output_dir clips --provider groq --api_key TU_GROQ_API_KEY
```

### Compilar ejecutable e instalador

**Paso 1 — generar el `.exe`**

```cmd
scripts\crear_exe.bat
```

Usa **PyInstaller** con la configuración de `scripts/run_gui.spec`, empaqueta `src/autoclipper` y los recursos de `assets/`, y deja la distribución en `dist\run_gui\`.

**Paso 2 — crear el instalador**

1. Abre `installer/instalador.iss` en **Inno Setup 7**.
2. Pulsa **Compile** (`Ctrl + F9`).
3. Se genera `dist\Instalador_AutoClipperAI.exe` con asistente moderno, soporte de 64 bits, accesos directos con el icono oficial, varios idiomas (español e inglés) y desinstalador.

### Estructura del repositorio

```text
auto-clipper-ai/
├── .streamlit/             # Configuración del servidor y temas de Streamlit
├── assets/
│   └── logo.ico
├── installer/
│   └── instalador.iss      # Script de Inno Setup 7
├── scripts/
│   ├── crear_acceso.ps1    # Generador de acceso directo
│   ├── crear_exe.bat       # Compilador a ejecutable portable
│   └── run_gui.spec        # Especificación de PyInstaller
├── src/
│   └── autoclipper/
│       ├── analyzer.py            # Análisis de transcripción y LLM
│       ├── subtitle_generator.py  # Subtítulos ASS
│       ├── transcriber.py         # Extracción de audio y Whisper
│       └── video_editor.py        # Reencuadre 9:16 y mezcla
├── tests/
│   └── test_analyzer_retry.py
├── ejecutar.bat            # Lanzador en un clic
├── gui.py                  # Interfaz Streamlit
├── main.py                 # Entrada de la CLI
├── packages.txt            # Dependencias del sistema
├── requirements.txt
├── run_gui.py              # Bootstrap del ejecutable
├── setup.py
├── LICENSE                 # GPL-3.0
└── README.md
```

### Pruebas

```bash
python tests/test_analyzer_retry.py
```

Comprueba el motor de análisis y la tolerancia a fallos del LLM.

### Licencia

**GPL-3.0**:

- ✅ **Uso**: gratuito para uso personal, educativo, pruebas, desarrollo y también comercial.
- 🔁 **Forks y modificaciones**: permitidos; si distribuyes versiones modificadas, publica el código bajo GPL-3.0 (copyleft).
- 👤 **Atribución**: conserva el crédito a **Alberto** y el enlace al repositorio original.

Consulta [LICENSE](LICENSE) para los términos completos.

---

## English

### Table of contents

- [Overview](#overview)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [GUI usage](#gui-usage)
- [CLI usage](#cli-usage)
- [Building the executable and installer](#building-the-executable-and-installer)
- [Repository structure](#repository-structure)
- [Testing](#testing)
- [License](#license)

### Overview

**Auto-Clipper AI** turns long videos into **vertical clips** ready for TikTok, YouTube Shorts and Instagram Reels using artificial intelligence. It transcribes the audio, analyzes the transcript to find the highest-hook moments, generates animated subtitles and reframes to 9:16.

Everything can run **locally** with `faster-whisper` and Ollama, or lean on cloud APIs (Groq or OpenAI) when speed matters.

### Features

- 🎙️ **Fast transcription** with `faster-whisper` (GPU/CUDA or CPU) or cloud APIs (Groq / OpenAI Whisper).
- 🧠 **Viral moment detection** with an LLM: explains each cut and assigns a virality score.
- 💬 **Dynamic ASS subtitles** in TikTok style, synced word by word with highlighted fonts.
- 📱 **9:16 vertical reframing** from horizontal footage.
- 💻 **Dual mode**: Streamlit dashboard and an automated command-line mode.
- 📦 **Windows-ready**: scripts to build a `.exe` with PyInstaller and an installer with Inno Setup 7.

### Requirements

- **Python 3.8+** (3.10 – 3.13 recommended).
- **FFmpeg**: handled automatically via `imageio-ffmpeg`, bundled in `requirements.txt`. You can also have `ffmpeg` on the `PATH`.
- **uv** (optional but recommended): fast environment and package manager.

### Installation

**Option 1 — with `uv` (recommended)**

```bash
git clone https://github.com/alberto2005-coder/auto-clipper-ai.git
cd auto-clipper-ai
uv venv
uv pip install -r requirements.txt
```

**Option 2 — with `pip`**

```bash
git clone https://github.com/alberto2005-coder/auto-clipper-ai.git
cd auto-clipper-ai
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### GUI usage

On Windows, double-click **`ejecutar.bat`**. The script activates the virtual environment, checks dependencies, offers to create a desktop shortcut with the official icon, and opens the dashboard in your browser (`http://localhost:8501`).

From a terminal:

```bash
streamlit run gui.py
```

The dashboard lets you:

- Upload local videos or point at paths on disk.
- Pick the Whisper model size (`tiny`, `base`, `small`, `medium`, `large-v3`).
- Choose the AI provider: local Ollama, Groq or OpenAI.
- Preview the cuts and download the 9:16 clips.

### CLI usage

```bash
python main.py path/to/video.mp4 --output_dir output_clips
```

| Parameter | Description | Default |
|---|---|---|
| `video_path` | Input video | *(required)* |
| `--output_dir` | Output folder for clips | `output_clips` |
| `--model` | Whisper model (`tiny`, `base`, `small`, `medium`) | `small` |
| `--lang` | ISO language code of the video | `es` |
| `--provider` | LLM provider (`ollama`, `groq`, `openai`) | `ollama` |
| `--api_url` | LLM API endpoint | `http://localhost:11434/api/generate` |
| `--api_key` | API key (Groq or OpenAI) | `None` / environment variable |
| `--llm_model` | LLM model name | `llama3` / `llama-3.3-70b-versatile` |

**With Ollama (100 % local and free)**

```bash
python main.py podcast.mp4 --output_dir clips --provider ollama --llm_model llama3
```

**With Groq (very fast cloud inference)**

```bash
python main.py podcast.mp4 --output_dir clips --provider groq --api_key YOUR_GROQ_API_KEY
```

### Building the executable and installer

**Step 1 — build the `.exe`**

```cmd
scripts\crear_exe.bat
```

It runs **PyInstaller** with `scripts/run_gui.spec`, bundles `src/autoclipper` and the `assets/` resources, and leaves the distribution in `dist\run_gui\`.

**Step 2 — create the installer**

1. Open `installer/instalador.iss` in **Inno Setup 7**.
2. Click **Compile** (`Ctrl + F9`).
3. This produces `dist\Instalador_AutoClipperAI.exe` with a modern wizard, 64-bit support, desktop and Start Menu shortcuts using the official icon, multi-language UI (Spanish and English) and a built-in uninstaller.

### Repository structure

```text
auto-clipper-ai/
├── .streamlit/             # Streamlit server and theme configuration
├── assets/
│   └── logo.ico
├── installer/
│   └── instalador.iss      # Inno Setup 7 script
├── scripts/
│   ├── crear_acceso.ps1    # Desktop shortcut generator
│   ├── crear_exe.bat       # Portable executable compiler
│   └── run_gui.spec        # PyInstaller spec
├── src/
│   └── autoclipper/
│       ├── analyzer.py            # Transcript analysis and LLM logic
│       ├── subtitle_generator.py  # ASS subtitles
│       ├── transcriber.py         # Audio extraction and Whisper
│       └── video_editor.py        # 9:16 reframing and mixing
├── tests/
│   └── test_analyzer_retry.py
├── ejecutar.bat            # One-click launcher
├── gui.py                  # Streamlit dashboard
├── main.py                 # CLI entry point
├── packages.txt            # System dependencies
├── requirements.txt
├── run_gui.py              # Compiled executable bootstrap
├── setup.py
├── LICENSE                 # GPL-3.0
└── README.md
```

### Testing

```bash
python tests/test_analyzer_retry.py
```

Covers the analysis engine and the LLM retry/fallback behavior.

### License

**GPL-3.0**:

- ✅ **Use**: free for personal, educational, testing, development and commercial use.
- 🔁 **Forks and modifications**: allowed; modified distributions must be released under GPL-3.0 (copyleft).
- 👤 **Attribution**: keep the credit to **Alberto** and the link to the original repository.

See [LICENSE](LICENSE) for the full terms.
