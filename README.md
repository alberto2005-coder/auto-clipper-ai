# Auto-Clipper AI

Auto-Clipper AI es una herramienta ligera que automatiza la creación de clips para TikTok y YouTube Shorts a partir de videos largos. Extrae el audio, transcribe el contenido, identifica los mejores momentos con IA y genera clips verticales con subtítulos dinámicos.

## Características

- Transcripción local con `faster-whisper`
- Selección inteligente de momentos virales usando LLMs (Ollama, OpenAI, Groq)
- Generación de subtítulos ASS dinámicos
- Recorte y reencuadre automático a formato vertical 9:16
- Interfaz de línea de comandos y panel gráfico con Streamlit

## Requisitos

- Python 3.8 o superior
- `imageio-ffmpeg` instalado (incluido en `requirements.txt`)
- Si no se dispone de `imageio-ffmpeg`, el proyecto intenta usar el ejecutable `ffmpeg` disponible en el PATH o en el directorio del proyecto

## Instalación

1. Clona o copia el proyecto en tu equipo.
2. Instala las dependencias:

```bash
pip install -r requirements.txt
```

3. Si lo deseas, instala el paquete localmente:

```bash
pip install .
```

## Uso CLI

Ejecuta el script principal con el video de origen:

```bash
python main.py ruta/del/video.mp4 --output_dir clips_salida
```

Opciones principales:

- `--video_path`: Ruta del video original
- `--output_dir`: Carpeta de salida para los clips
- `--model`: Modelo Whisper (`tiny`, `base`, `small`, `medium`)
- `--lang`: Idioma del video (`es` por defecto)
- `--provider`: Proveedor de IA (`ollama`, `openai`, `groq`)
- `--api_url`: URL de la API de Ollama/OpenAI/Groq
- `--api_key`: Clave API para OpenAI o Groq
- `--llm_model`: Modelo LLM para selección de momentos

Ejemplo con proveedor local Ollama:

```bash
python main.py video.mp4 --output_dir output_clips --provider ollama --api_url http://localhost:11434/api/generate
```

Ejemplo con Groq:

```bash
python main.py video.mp4 --output_dir output_clips --provider groq --api_key TU_API_KEY
```

## Uso de la interfaz gráfica

La forma más simple en Windows es ejecutar el archivo batch `ejecutar.bat`, que:

- comprueba que Python esté instalado
- instala las dependencias desde `requirements.txt`
- ofrece crear un acceso directo en el escritorio
- inicia la aplicación Streamlit en el navegador

```bat
ejecutar.bat
```

Si prefieres ejecutar la interfaz manualmente, usa:

```bash
streamlit run gui.py --server.port=8501
```

### Qué permite la interfaz

- Cargar el video desde el navegador o usar una ruta local
- Seleccionar modelo de transcripción y proveedor de IA
- Procesar el video paso a paso
- Descargar los clips generados

## Organización del proyecto

- `main.py`: Lógica principal de la línea de comandos
- `gui.py`: Interfaz gráfica con Streamlit
- `transcriber.py`: Extracción y transcripción de audio
- `analyzer.py`: Selección de mejores momentos usando IA
- `subtitle_generator.py`: Creación de subtítulos ASS
- `video_editor.py`: Recorte, reencuadre y exportación de clips
- `requirements.txt`: Dependencias del proyecto
- `setup.py`: Configuración del paquete Python

## Notas importantes

- Si usas `openAI` o `groq`, asegúrate de tener la API Key correcta o configurarla con `--api_key`.
- Para Ollama, el valor por defecto de `api_url` es `http://localhost:11434/api/generate`.
- El resultado final se guarda en la carpeta indicada por `--output_dir` o en `output_clips_gui` cuando se usa la GUI.
- En Windows, `ejecutar.bat` ya está preparado para iniciar la GUI fácilmente.

## Contacto

Para soporte o ajustes personalizados, puedes adaptar el script o contactarme directamente si necesitas configurar el proyecto para un flujo específico.
