import os
import streamlit as st
import shutil
import tempfile
import uuid
from transcriber import extract_audio, transcribe_audio
from analyzer import select_best_moments_with_llm
from subtitle_generator import generate_ass_subtitles, SUBTITLE_STYLES, AVAILABLE_FONTS
from video_editor import process_video_clip, compute_title_info, TITLE_STYLES, TITLE_FONTS, mix_background_music, is_portrait_video
import json
import datetime


def get_persistent_output_dir():
    home = os.path.expanduser("~")
    videos_dir = os.path.join(home, "Videos")
    path = os.path.join(videos_dir if os.path.exists(videos_dir) else home, "AutoClipperAI")
    os.makedirs(path, exist_ok=True)
    return path


# ─────────────────────────────────────────────────────────────────────────────
# Custom Font Handling & Registration
# ─────────────────────────────────────────────────────────────────────────────
import struct
import ctypes

def get_font_name_from_ttf(path):
    try:
        with open(path, 'rb') as f:
            sfnt_header = f.read(12)
            if len(sfnt_header) < 12:
                return os.path.splitext(os.path.basename(path))[0]
            num_tables = struct.unpack('>H', sfnt_header[4:6])[0]
            
            name_offset = None
            name_length = None
            for _ in range(num_tables):
                table_record = f.read(16)
                if len(table_record) < 16:
                    break
                tag = table_record[0:4].decode('latin-1', errors='ignore')
                if tag == 'name':
                    name_offset = struct.unpack('>I', table_record[8:12])[0]
                    name_length = struct.unpack('>I', table_record[12:16])[0]
                    break
                    
            if name_offset is None or name_length is None:
                return os.path.splitext(os.path.basename(path))[0]
                
            f.seek(name_offset)
            name_table_header = f.read(6)
            if len(name_table_header) < 6:
                return os.path.splitext(os.path.basename(path))[0]
            count, string_offset = struct.unpack('>HH', name_table_header[2:6])
            
            records_start = name_offset + 6
            string_start = name_offset + string_offset
            
            font_family = None
            font_name = None
            
            for i in range(count):
                f.seek(records_start + i * 12)
                record_data = f.read(12)
                if len(record_data) < 12:
                    break
                platform_id, encoding_id, language_id, name_id, length, offset = struct.unpack('>HHHHHH', record_data)
                
                if name_id in (1, 4):
                    f.seek(string_start + offset)
                    s = f.read(length)
                    try:
                        if platform_id == 3 or platform_id == 0:
                            decoded = s.decode('utf-16-be', errors='ignore')
                        else:
                            decoded = s.decode('utf-8', errors='ignore')
                    except Exception:
                        decoded = s.decode('latin-1', errors='ignore')
                    
                    decoded = decoded.strip('\x00').strip()
                    if decoded:
                        if name_id == 1:
                            font_family = decoded
                        elif name_id == 4:
                            font_name = decoded
                            
            if font_family:
                return font_family
            if font_name:
                return font_name
            return os.path.splitext(os.path.basename(path))[0]
    except Exception:
        return os.path.splitext(os.path.basename(path))[0]

def register_font_windows(font_path):
    if os.name != 'nt':
        return False
    try:
        gdi32 = ctypes.WinDLL('gdi32', use_last_error=True)
        res = gdi32.AddFontResourceW(font_path)
        if res > 0:
            user32 = ctypes.WinDLL('user32', use_last_error=True)
            HWND_BROADCAST = 0xFFFF
            WM_FONTCHANGE = 0x001D
            user32.SendNotifyMessageW(HWND_BROADCAST, WM_FONTCHANGE, 0, 0)
            return True
    except Exception as e:
        print(f"Error registering font: {e}")
    return False

WORKSPACE_FONTS_DIR = os.path.join(get_persistent_output_dir(), "fonts")
os.makedirs(WORKSPACE_FONTS_DIR, exist_ok=True)

def download_montserrat_if_needed():
    import urllib.request
    fonts_to_download = {
        "Montserrat-Bold.ttf": "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Bold.ttf",
        "Montserrat-Regular.ttf": "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Regular.ttf",
        "Montserrat-Medium.ttf": "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Medium.ttf",
    }
    for filename, url in fonts_to_download.items():
        dest = os.path.join(WORKSPACE_FONTS_DIR, filename)
        if not os.path.exists(dest):
            try:
                print(f"[*] Downloading {filename} from Google Fonts...")
                urllib.request.urlretrieve(url, dest)
            except Exception as e:
                print(f"[!] Error downloading {filename}: {e}")

def load_and_register_local_fonts():
    import threading
    threading.Thread(target=download_montserrat_if_needed, daemon=True).start()
    
    custom_fonts_found = []
    if os.path.exists(WORKSPACE_FONTS_DIR):
        for filename in os.listdir(WORKSPACE_FONTS_DIR):
            if filename.lower().endswith(('.ttf', '.otf')):
                font_path = os.path.join(WORKSPACE_FONTS_DIR, filename)
                register_font_windows(font_path)
                name = get_font_name_from_ttf(font_path)
                if name and name not in custom_fonts_found:
                    custom_fonts_found.append(name)
    return custom_fonts_found

# Load custom fonts
custom_font_names = load_and_register_local_fonts()

# Combine lists
combined_available_fonts = []
for f in (custom_font_names + AVAILABLE_FONTS):
    if f not in combined_available_fonts:
        combined_available_fonts.append(f)

combined_title_fonts = []
for f in (custom_font_names + TITLE_FONTS):
    if f not in combined_title_fonts:
        combined_title_fonts.append(f)


def get_words_for_range(transcription_data, start, end):
    words = []
    for segment in transcription_data:
        for w in segment.get("words", []):
            w_start = w["start"]
            w_end   = w["end"]
            if (w_start >= start - 0.5 and w_start < end) or (w_end > start and w_end <= end + 0.5):
                words.append({
                    "word": w["word"].strip().upper(),
                    "start": w_start,
                    "end": w_end,
                })
    return words


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════


def load_history(output_dir):
    history_file = os.path.join(output_dir, "historial.json")
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_history(output_dir, history):
    history_file = os.path.join(output_dir, "historial.json")
    try:
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving history: {e}")


def format_seconds_to_time(seconds):
    mins   = int(seconds // 60)
    secs   = int(seconds % 60)
    centis = int(round((seconds % 1) * 100))
    if centis == 100:
        secs  += 1
        centis = 0
    return f"{mins:02d}:{secs:02d}.{centis:02d}"


def render_virality_badge(score, explanation):
    color = "#FF4B4B" if score < 75 else ("#FF8F00" if score < 90 else "#00C853")
    level = "Bajo"    if score < 75 else ("Bueno"   if score < 90 else "Excelente")
    st.markdown(f"""
    <div style='background-color: #1E1E1E; border-radius: 12px; padding: 12px; margin-bottom: 12px; border-left: 5px solid {color}; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
        <div style='display: flex; align-items: center; justify-content: space-between;'>
            <span style='color: #888; font-size: 0.85rem; font-weight: bold;'>SCORE DE VIRALIDAD</span>
            <span style='background-color: {color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8rem; font-weight: bold;'>{level}</span>
        </div>
        <div style='font-size: 1.8rem; font-weight: bold; color: {color}; margin: 5px 0;'>🔥 {score}/100</div>
        <div style='color: #DDD; font-size: 0.85rem; line-height: 1.3;'>{explanation}</div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Auto-Clipper AI",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-title {
        font-size: 3rem;
        background: linear-gradient(45deg, #FF4B4B, #FF8F00);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stButton>button {
        background: linear-gradient(45deg, #FF4B4B, #FF8F00) !important;
        color: white !important;
        border: none !important;
        font-weight: bold !important;
        padding: 0.5rem 2rem !important;
        border-radius: 10px !important;
        transition: transform 0.2s;
    }
    .stButton>button:hover { transform: scale(1.02); }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🎬 Auto-Clipper AI</div>', unsafe_allow_html=True)
st.markdown(
    "<p style='text-align: center; color: #888;'>"
    "Corta, re-encuadra y genera subtítulos dinámicos de forma automática "
    "para TikTok, Shorts, YouTube y más."
    "</p>",
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE INIT
# ══════════════════════════════════════════════════════════════════════════════

if "pipeline_done"  not in st.session_state: st.session_state.pipeline_done  = False
if "pipeline_clips" not in st.session_state: st.session_state.pipeline_clips = []
if "pipeline_fmt"   not in st.session_state: st.session_state.pipeline_fmt   = "9:16"
if "pipeline_style" not in st.session_state: st.session_state.pipeline_style = "tiktok"
if "output_dir_ss"  not in st.session_state: st.session_state.output_dir_ss  = ""
if "video_analyzed" not in st.session_state: st.session_state.video_analyzed = False
if "transcription_data" not in st.session_state: st.session_state.transcription_data = None
if "clips" not in st.session_state: st.session_state.clips = []
if "video_to_process" not in st.session_state: st.session_state.video_to_process = ""

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

st.sidebar.header("⚙️ Configuración del Sistema")

whisper_model = st.sidebar.selectbox(
    "Modelo Whisper (Transcripción)",
    ["tiny", "base", "small", "medium"],
    index=2,
    help="'small' ofrece el mejor equilibrio velocidad/precisión en CPU.",
)

lang = st.sidebar.text_input("Idioma del video", "es")

use_cloud_transcription = st.sidebar.checkbox(
    "☁️ Transcripción en la Nube (Groq/OpenAI)",
    value=False,
    help="Transcribe en segundos con Groq/OpenAI. Ideal para videos largos (> 5 min).",
)

use_gpu = st.sidebar.checkbox(
    "🚀 Usar aceleración por GPU (NVIDIA CUDA)",
    value=False,
    help="Utiliza la GPU para una transcripción local y renderizado ultra rápidos.",
)

st.sidebar.markdown("---")

# ── 🎞️ Formato de video ──────────────────────────────────────────────────────
st.sidebar.header("🎞️ Formato de Video")

video_format = st.sidebar.radio(
    "Tipo de video de salida",
    options=["9:16", "16:9", "1:1"],
    index=0,
    help="**9:16** → TikTok / Shorts / Reels\n\n**16:9** → YouTube horizontal\n\n**1:1** → Instagram Feed",
)

camera_tracking = st.sidebar.checkbox(
    "🎥 Seguimiento inteligente de rostros",
    value=True,
    help="Centra la cámara en la cara detectada. Se desactiva automáticamente si el video ya es vertical.",
)

fade_effect = st.sidebar.checkbox(
    "🎬 Animación de Entrada/Salida (Fade)",
    value=True,
    help="Aplica una suave transición de desvanecimiento al inicio y final de cada clip.",
)

FORMAT_LABELS = {
    "9:16": "📱 Vertical (9:16)",
    "16:9": "🖥️ Horizontal (16:9)",
    "1:1":  "⬛ Cuadrado (1:1)",
}

st.sidebar.markdown("---")

# ── 🎨 Subtítulos ────────────────────────────────────────────────────────────
st.sidebar.header("🎨 Estilo de Subtítulos")

enable_subtitles = st.sidebar.checkbox(
    "✏️ Añadir subtítulos dinámicos",
    value=True,
    help="Desactiva si el video ya tiene subtítulos o no quieres añadirlos.",
)

if enable_subtitles:
    subtitle_style_key = st.sidebar.selectbox(
        "Estilo de color",
        options=list(SUBTITLE_STYLES.keys()),
        format_func=lambda k: SUBTITLE_STYLES[k]["label"],
        index=0,
    )
    sub_font_name = st.sidebar.selectbox(
        "Tipo de letra (subtítulos)",
        options=combined_available_fonts,
        index=0,
    )
    sub_font_size = st.sidebar.slider(
        "Tamaño de letra (subtítulos)",
        min_value=40, max_value=130, value=75, step=5,
    )
    sub_words_per_line = st.sidebar.slider(
        "Palabras por bloque",
        min_value=1, max_value=8, value=3, step=1,
        help="Cuántas palabras se muestran al mismo tiempo en pantalla. Menos palabras hace que los subtítulos sean más rápidos y cortos."
    )
    os.environ["SUBTITLE_CHUNK_SIZE"] = str(sub_words_per_line)
    subtitle_position = st.sidebar.radio(
        "Posición de los subtítulos",
        options=["bottom", "center", "top"],
        format_func=lambda p: {"bottom": "⬇️ Abajo", "center": "↔️ Centro", "top": "⬆️ Arriba"}[p],
        index=0,
    )
else:
    subtitle_style_key = "tiktok"
    sub_font_name      = "Arial Black"
    sub_font_size      = 75
    os.environ["SUBTITLE_CHUNK_SIZE"] = "3"
    subtitle_position  = "bottom"

st.sidebar.markdown("---")

# ── 🏷️ Título ─────────────────────────────────────────────────────────────────
st.sidebar.header("🏷️ Título en el Video")

show_title = st.sidebar.checkbox(
    "📌 Quemar título en el video",
    value=True,
    help="Muestra el título recomendado por la IA como texto quemado en el clip.",
)

if show_title:
    title_style_key = st.sidebar.selectbox(
        "Estilo del título",
        options=list(TITLE_STYLES.keys()),
        format_func=lambda k: TITLE_STYLES[k]["label"],
        index=0,
    )
    title_font = st.sidebar.selectbox("Tipo de letra (título)", options=combined_title_fonts, index=0)
    title_font_size = st.sidebar.slider(
        "Tamaño de letra (título)",
        min_value=40, max_value=160, value=90, step=5,
    )
    title_position = st.sidebar.radio(
        "Posición del título",
        options=["top", "center", "bottom"],
        format_func=lambda p: {"top": "⬆️ Arriba", "center": "↔️ Centro", "bottom": "⬇️ Abajo"}[p],
        index=0,
    )
else:
    title_style_key = "clasico"
    title_font      = "Arial Bold"
    title_font_size = 90
    title_position  = "top"

st.sidebar.markdown("---")
st.sidebar.header("🔤 Fuentes Personalizadas")
uploaded_fonts = st.sidebar.file_uploader(
    "Sube tus propios archivos de fuente (.ttf, .otf)",
    type=["ttf", "otf"],
    accept_multiple_files=True,
    key="font_uploader"
)
if uploaded_fonts:
    new_fonts_uploaded = False
    for f in uploaded_fonts:
        dest = os.path.join(WORKSPACE_FONTS_DIR, f.name)
        if not os.path.exists(dest):
            with open(dest, "wb") as dest_f:
                dest_f.write(f.read())
            new_fonts_uploaded = True
    if new_fonts_uploaded:
        st.rerun()

st.sidebar.markdown("---")

# ── 🤖 IA ─────────────────────────────────────────────────────────────────────
st.sidebar.header("🤖 Inferencia AI (Selección de Momentos)")

provider = st.sidebar.selectbox("Proveedor de IA", ["ollama", "openai", "groq"], index=0)

api_key = ""
if provider in ["openai", "groq"]:
    api_key = st.sidebar.text_input("Clave API (API Key)", type="password")

default_model = (
    "llama3.2:3b" if provider == "ollama"
    else ("gpt-4o-mini" if provider == "openai" else "llama-3.3-70b-versatile")
)
llm_model = st.sidebar.text_input("Modelo de IA", default_model)

max_clips = st.sidebar.slider("Número máximo de clips", min_value=1, max_value=20, value=10, step=1)
min_clips = st.sidebar.slider(
    "Número mínimo de clips",
    min_value=1, max_value=max_clips, value=min(3, max_clips), step=1,
)
clip_type = st.sidebar.text_input(
    "Tipo de clips a buscar",
    value="virales, entretenidos, informativos o con un gancho (hook) muy fuerte",
)

# Resolve API URL
if provider == "groq":
    api_url = "https://api.groq.com/openai/v1/chat/completions"
    resolved_provider = "openai"
elif provider == "openai":
    api_url = "https://api.openai.com/v1/chat/completions"
    resolved_provider = "openai"
else:
    api_url = "http://localhost:11434/api/generate"
    resolved_provider = "ollama"

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════

tab_proc, tab_edit, tab_lib = st.tabs(["🚀 Procesador de Clips", "✂️ Editor de Clips", "📚 Biblioteca"])

# ──────────────────────────────────────────────────────────────────────────────
# TAB 1: PROCESADOR
# ──────────────────────────────────────────────────────────────────────────────
with tab_proc:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📹 Cargar Video")
        uploaded_file = st.file_uploader(
            "Selecciona un video (MP4/MKV/MOV)",
            type=["mp4", "mkv", "mov"],
            max_upload_size=10240,
        )
        st.info("💡 Paso 1: Analizar el video para detectar los mejores momentos. Paso 2: Editar y renderizar los clips.")
        local_path = st.text_input("O introduce la ruta de un archivo local (más rápido):")

    with col2:
        st.subheader("📋 Acciones del Pipeline")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            analyze_btn = st.button("🔍 1. Analizar Video", use_container_width=True)
        with col_btn2:
            render_btn = st.button("🎬 2. Procesar Clips", disabled=not st.session_state.get("video_analyzed", False), use_container_width=True)
        
        status_area  = st.empty()
        progress_bar = st.progress(0)

    # ── 1. ACTION: ANALYZE VIDEO ──────────────────────────────────────────────
    if analyze_btn:
        # Reset state so previous results don't linger
        st.session_state.pipeline_done  = False
        st.session_state.pipeline_clips = []
        st.session_state.video_analyzed = False
        st.session_state.clips = []
        st.session_state.transcription_data = None
        st.session_state.video_to_process = ""

        video_to_process   = ""
        temp_uploaded_path = None

        if uploaded_file is not None:
            output_dir = get_persistent_output_dir()
            temp_uploads_dir = os.path.join(output_dir, "temp_uploads")
            os.makedirs(temp_uploads_dir, exist_ok=True)
            temp_uploaded_path = os.path.join(
                temp_uploads_dir,
                f"temp_uploaded_{uuid.uuid4().hex}.mp4",
            )
            with open(temp_uploaded_path, "wb") as f:
                CHUNK_SIZE = 8 * 1024 * 1024
                while True:
                    chunk = uploaded_file.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    f.write(chunk)
            if not os.path.exists(temp_uploaded_path):
                st.error("❌ No se pudo guardar el video temporal. Intenta usar la ruta local.")
            else:
                file_size = os.path.getsize(temp_uploaded_path)
                status_area.write(f"✅ Video guardado en temp_uploads ({file_size // (1024*1024)} MB)")
                video_to_process = temp_uploaded_path
        elif local_path:
            if os.path.exists(local_path):
                video_to_process = local_path
            else:
                st.error(f"❌ La ruta local '{local_path}' no existe.")

        if video_to_process:
            temp_dir   = os.path.join(tempfile.gettempdir(), f"temp_gui_{uuid.uuid4().hex}")
            os.makedirs(temp_dir,   exist_ok=True)
            temp_audio = os.path.join(temp_dir, "extracted_audio.wav")

            try:
                # ── Paso 1: Audio ──────────────────────────────────────────
                status_area.write("⏳ Paso 1/3: Extrayendo audio del video...")
                progress_bar.progress(15)
                extract_audio(video_to_process, temp_audio)

                # ── Paso 2: Transcripción ──────────────────────────────────
                if use_cloud_transcription and provider in ["groq", "openai"] and api_key:
                    status_area.write(f"⏳ Paso 2/3: Transcribiendo en la nube con {provider}...")
                    progress_bar.progress(40)
                    from transcriber import transcribe_audio_cloud
                    trans_api_url = None
                    if provider == "openai" and api_url and "completions" not in api_url:
                        trans_api_url = api_url
                    transcription_data = transcribe_audio_cloud(
                        temp_audio, api_key=api_key, provider=provider,
                        api_url=trans_api_url, language=lang,
                    )
                else:
                    status_area.write("⏳ Paso 2/3: Transcribiendo localmente con Whisper...")
                    progress_bar.progress(40)
                    transcription_data = transcribe_audio(
                        temp_audio, model_size=whisper_model, language=lang, use_gpu=use_gpu,
                    )

                # ── Paso 3: IA selecciona momentos ────────────────────────
                status_area.write("⏳ Paso 3/3: La IA está buscando los mejores momentos...")
                progress_bar.progress(75)
                clips = select_best_moments_with_llm(
                    transcription_data,
                    provider=resolved_provider,
                    api_url=api_url,
                    api_key=api_key if api_key else None,
                    model=llm_model,
                    max_clips=max_clips,
                    min_clips=min_clips,
                    clip_type=clip_type,
                )

                # Post-processing helper function to get words for each clip
                for idx, clip in enumerate(clips):
                    clip["words"] = get_words_for_range(transcription_data, clip["start"], clip["end"])
                    clip["prev_start"] = clip["start"]
                    clip["prev_end"] = clip["end"]

                st.session_state.transcription_data = transcription_data
                st.session_state.clips = clips
                st.session_state.video_to_process = video_to_process
                st.session_state.video_analyzed = True

                progress_bar.progress(100)
                status_area.success(f"🎉 ¡Análisis completo! Se encontraron {len(clips)} clips. Edítalos abajo antes de renderizar.")
                st.rerun()

            except Exception as e:
                st.error(f"❌ Error en el análisis: {e}")
                import traceback
                st.code(traceback.format_exc())
            finally:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
        else:
            st.warning("⚠️ Sube un video o ingresa la ruta de un archivo local válido.")

    # ── 2. EDITING SECTION (BETWEEN STEPS) ────────────────────────────────────
    if st.session_state.get("video_analyzed", False):
        st.write("---")
        st.subheader("📝 Edita los Clips y Subtítulos antes del Renderizado")
        st.info("💡 Modifica los textos, el título o los tiempos abajo. Cuando termines, haz clic en '🎬 2. Procesar Clips' arriba para generar el video.")

        for idx, clip in enumerate(st.session_state.clips):
            with st.expander(f"🎬 Clip {idx+1}: {clip.get('hook_title', 'Sin título')}", expanded=True):
                col_t, col_s, col_e = st.columns([2, 1, 1])
                with col_t:
                    clip["hook_title"] = st.text_input(
                        "Título (Hook)",
                        value=clip.get("hook_title", ""),
                        key=f"edit_title_{idx}"
                    )
                with col_s:
                    clip["start"] = st.number_input(
                        "Inicio (segundos)",
                        min_value=0.0,
                        value=float(clip.get("start", 0)),
                        step=0.5,
                        key=f"edit_start_{idx}"
                    )
                with col_e:
                    clip["end"] = st.number_input(
                        "Fin (segundos)",
                        min_value=clip["start"] + 0.5,
                        value=float(clip.get("end", 0)),
                        step=0.5,
                        key=f"edit_end_{idx}"
                    )
                
                # Auto-update words if range changes
                if "prev_start" not in clip:
                    clip["prev_start"] = clip["start"]
                if "prev_end" not in clip:
                    clip["prev_end"] = clip["end"]
                
                if clip["start"] != clip["prev_start"] or clip["end"] != clip["prev_end"]:
                    clip["words"] = get_words_for_range(st.session_state.transcription_data, clip["start"], clip["end"])
                    clip["prev_start"] = clip["start"]
                    clip["prev_end"] = clip["end"]
                    st.rerun()
                
                clip["social_description"] = st.text_area(
                    "Descripción sugerida para redes sociales",
                    value=clip.get("social_description", ""),
                    key=f"edit_desc_{idx}",
                    rows=3
                )
                
                # Render subtitle words editor
                current_words = clip.get("words", [])
                current_text = " ".join([w["word"] for w in current_words])
                
                edited_text = st.text_area(
                    "Subtítulos (Edita el texto directamente. Separado por espacios)",
                    value=current_text,
                    key=f"edit_subs_{idx}",
                    help="Puedes corregir errores de escritura. Si cambias la cantidad de palabras, la duración del clip se dividirá equitativamente entre las palabras."
                )
                
                if edited_text.strip() != current_text.strip():
                    new_word_strings = edited_text.strip().split()
                    if len(new_word_strings) == len(current_words):
                        for i, w_str in enumerate(new_word_strings):
                            current_words[i]["word"] = w_str.upper()
                        clip["words"] = current_words
                    else:
                        num_new = len(new_word_strings)
                        if num_new > 0:
                            clip_duration = clip["end"] - clip["start"]
                            word_dur = clip_duration / num_new
                            new_words = []
                            for i, w_str in enumerate(new_word_strings):
                                w_start = clip["start"] + i * word_dur
                                w_end = clip["start"] + (i + 1) * word_dur
                                new_words.append({
                                    "word": w_str.upper(),
                                    "start": w_start,
                                    "end": w_end
                                })
                            clip["words"] = new_words
                        else:
                            clip["words"] = []

    # ── 3. ACTION: RENDER CLIPS ───────────────────────────────────────────────
    if render_btn:
        video_to_process = st.session_state.video_to_process
        clips = st.session_state.clips
        temp_dir   = os.path.join(tempfile.gettempdir(), f"temp_gui_{uuid.uuid4().hex}")
        output_dir = get_persistent_output_dir()
        os.makedirs(temp_dir,   exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        try:
            status_area.write(f"🎬 Comenzando renderizado de {len(clips)} clips...")
            progress_bar.progress(0)

            # Pre-compute portrait detection ONCE for all clips of this source video
            source_is_portrait = is_portrait_video(video_to_process) if camera_tracking else False

            for idx, clip in enumerate(clips):
                start      = clip["start"]
                end        = clip["end"]
                clip_title = clip.get("hook_title", f"clip_{idx+1}")
                safe_title = "".join(
                    c for c in clip_title.replace(" ", "_").lower()
                    if c.isalnum() or c in ("_", "-")
                )
                clip_output_name = f"clip_{idx+1}_{safe_title}_{subtitle_style_key}.mp4"
                clip_output_path = os.path.join(output_dir, clip_output_name)

                status_area.write(f"⏳ Paso 4/4: Procesando clip {idx+1}/{len(clips)}: {clip_title}...")

                # Offset subtítulos si comparten borde con el título
                subtitle_margin_override = None
                if show_title and clip_title and enable_subtitles and title_position == subtitle_position:
                    anchor_px, title_h = compute_title_info(
                        clip_title, video_format, title_position, title_font_size
                    )
                    subtitle_margin_override = anchor_px + title_h + 20

                # Generar ASS
                ass_path = None
                if enable_subtitles:
                    ass_path = os.path.join(temp_dir, f"subtitles_{idx+1}.ass")
                    generate_ass_subtitles(
                        st.session_state.transcription_data, start, end, ass_path,
                        subtitle_position=subtitle_position,
                        font_name=sub_font_name,
                        font_size=sub_font_size,
                        subtitle_style=subtitle_style_key,
                        margin_override=subtitle_margin_override,
                        words_override=clip.get("words"),
                    )

                progress_percent = int(100 * (idx / max(len(clips), 1)))
                progress_bar.progress(progress_percent)

                process_video_clip(
                    video_to_process, start, end, ass_path, clip_output_path,
                    video_format=video_format,
                    hook_title=clip_title if show_title else "",
                    title_position=title_position,
                    title_font_size=title_font_size,
                    title_style=title_style_key,
                    title_font=title_font,
                    subtitle_position=subtitle_position,
                    camera_tracking=camera_tracking,
                    fade_effect=fade_effect,
                    use_gpu=use_gpu,
                    source_is_portrait=source_is_portrait,
                )

            progress_bar.progress(100)
            status_area.success("🎉 ¡Todo listo! Clips creados correctamente.")

            # ── Guardar en historial ───────────────────────────────────
            history = load_history(output_dir)
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for idx, clip in enumerate(clips):
                clip_title = clip.get("hook_title", f"Clip {idx+1}")
                safe_title = "".join(
                    c for c in clip_title.replace(" ", "_").lower()
                    if c.isalnum() or c in ("_", "-")
                )
                clip_output_name = f"clip_{idx+1}_{safe_title}_{subtitle_style_key}.mp4"
                clip_path        = os.path.join(output_dir, clip_output_name)
                if os.path.exists(clip_path):
                    if not any(item.get("clip_path") == clip_path for item in history):
                        history.append({
                            "clip_name":             clip_output_name,
                            "clip_path":             clip_path,
                            "title":                 clip_title,
                            "start":                 clip.get("start", 0),
                            "end":                   clip.get("end", 0),
                            "social_description":    clip.get("social_description", ""),
                            "virality_score":        clip.get("virality_score", 85),
                            "virality_explanation":  clip.get("virality_explanation", "Estructura narrativa sólida."),
                            "created_at":            now_str,
                            "video_format":          video_format,
                        })
            save_history(output_dir, history)

            # Cache results in session state to avoid re-running on widget interactions
            st.session_state.pipeline_done  = True
            st.session_state.pipeline_clips = clips
            st.session_state.pipeline_fmt   = video_format
            st.session_state.pipeline_style = subtitle_style_key
            st.session_state.output_dir_ss  = output_dir
            st.rerun()

        except Exception as e:
            st.error(f"❌ Error en el procesamiento: {e}")
            import traceback
            st.code(traceback.format_exc())
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            # We don't remove the temp video until process is done
            if video_to_process and "temp_uploaded_" in video_to_process and os.path.exists(video_to_process):
                try:
                    os.remove(video_to_process)
                except Exception:
                    pass

    # ── Mostrar resultados cacheados (persisten entre widgets) ─────────────────
    if st.session_state.pipeline_done and st.session_state.pipeline_clips:
        clips      = st.session_state.pipeline_clips
        output_dir = st.session_state.output_dir_ss
        _fmt       = st.session_state.pipeline_fmt
        _style     = st.session_state.pipeline_style

        st.write("---")
        st.subheader("🎉 Clips Creados")

        VIDEO_WIDTH_MAP = {"9:16": 320, "16:9": 560, "1:1": 420}
        result_cols = st.columns(min(max(len(clips), 1), 3))

        for idx, clip in enumerate(clips):
            start      = clip.get("start", 0)
            end        = clip.get("end", 0)
            clip_title = clip.get("hook_title", f"Clip {idx+1}")
            safe_title = "".join(
                c for c in clip_title.replace(" ", "_").lower()
                if c.isalnum() or c in ("_", "-")
            )
            clip_output_name = f"clip_{idx+1}_{safe_title}_{_style}.mp4"
            clip_path        = os.path.join(output_dir, clip_output_name)

            if os.path.exists(clip_path):
                with result_cols[idx % 3]:
                    st.markdown(f"### {clip_title}")
                    st.markdown(
                        f"⏱️ **Original:** `{format_seconds_to_time(start)}` → `{format_seconds_to_time(end)}`"
                    )
                    st.caption(FORMAT_LABELS.get(_fmt, _fmt))
                    render_virality_badge(
                        clip.get("virality_score", 85),
                        clip.get("virality_explanation", "Excelente gancho y estructura narrativa."),
                    )
                    with st.expander("📺 Reproducir Clip", expanded=False):
                        st.video(clip_path)

                    st.info(f"✍️ **Copy sugerido:**\n\n{clip.get('social_description', '¡Mira este clip!')}")

                    with st.expander("🎵 Mezclar Música de Fondo"):
                        sub_audio_file = st.file_uploader(
                            "Audio (.mp3, .wav, .m4a, .aac, .ogg)",
                            type=["mp3", "wav", "m4a", "aac", "ogg"],
                            key=f"audio_proc_{idx}_{safe_title}",
                        )
                        sub_audio_vol = st.slider(
                            "Volumen de la música",
                            min_value=0.01, max_value=0.50, value=0.10, step=0.01,
                            key=f"vol_proc_{idx}_{safe_title}",
                        )
                        if st.button("🎛️ Combinar Audio", key=f"btn_proc_{idx}_{safe_title}"):
                            if sub_audio_file is not None:
                                temp_sub_path = os.path.join(
                                    tempfile.gettempdir(),
                                    f"temp_sub_{uuid.uuid4().hex}_{sub_audio_file.name}",
                                )
                                with open(temp_sub_path, "wb") as f_sub:
                                    f_sub.write(sub_audio_file.read())
                                with st.spinner("Mezclando audio..."):
                                    try:
                                        mix_background_music(clip_path, temp_sub_path, sub_audio_vol, clip_path)
                                        st.success("✅ ¡Música mezclada con éxito!")
                                    except Exception as mix_err:
                                        st.error(f"Error mezclando: {mix_err}")
                                    finally:
                                        if os.path.exists(temp_sub_path):
                                            os.remove(temp_sub_path)
                            else:
                                st.warning("Por favor, sube un archivo de audio primero.")

                    with open(clip_path, "rb") as file:
                        st.download_button(
                            label="⬇️ Descargar Clip",
                            data=file,
                            file_name=clip_output_name,
                            mime="video/mp4",
                            key=f"dl_proc_{idx}_{safe_title}",
                        )


# ──────────────────────────────────────────────────────────────────────────────
# TAB 2: EDITOR DE CLIPS
# ──────────────────────────────────────────────────────────────────────────────
with tab_edit:
    st.subheader("✂️ Editor de Clips")
    st.markdown(
        "Recorta con precisión cualquier clip existente en tu biblioteca. "
        "Puedes ajustar los tiempos de inicio y fin para quedarte con la parte exacta que necesitas."
    )

    output_dir_edit = get_persistent_output_dir()
    history_edit    = load_history(output_dir_edit)
    valid_clips     = [
        item for item in history_edit
        if item.get("clip_path") and os.path.exists(item["clip_path"])
    ]

    if not valid_clips:
        st.info("📂 Aún no tienes clips en tu biblioteca. Procesa un video primero en la pestaña '🚀 Procesador de Clips'.")
    else:
        clip_options = {
            f"{item.get('title', 'Sin título')} ({item.get('created_at', '')})" : item
            for item in reversed(valid_clips)
        }
        selected_label = st.selectbox("Selecciona un clip para editar:", options=list(clip_options.keys()))
        selected_item  = clip_options[selected_label]
        clip_path_edit = selected_item["clip_path"]

        # Detect duration of the selected clip
        try:
            import cv2 as _cv2
            _cap = _cv2.VideoCapture(clip_path_edit)
            _fps  = _cap.get(_cv2.CAP_PROP_FPS) or 30.0
            _fc   = _cap.get(_cv2.CAP_PROP_FRAME_COUNT)
            clip_duration_edit = _fc / _fps if _fps > 0 else 0.0
            _cap.release()
        except Exception:
            clip_duration_edit = 60.0

        st.markdown(f"**Clip seleccionado:** `{os.path.basename(clip_path_edit)}`")
        st.markdown(f"**Duración total:** `{format_seconds_to_time(clip_duration_edit)}`")

        with st.expander("📺 Previsualizar clip original", expanded=False):
            st.video(clip_path_edit)

        st.write("---")
        st.markdown("### ✂️ Ajustar Tiempos de Recorte")

        col_start, col_end = st.columns(2)
        with col_start:
            trim_start = st.number_input(
                "⏩ Inicio del recorte (segundos)",
                min_value=0.0,
                max_value=max(clip_duration_edit - 1.0, 0.0),
                value=0.0,
                step=0.5,
                format="%.1f",
            )
        with col_end:
            trim_end = st.number_input(
                "⏹️ Fin del recorte (segundos)",
                min_value=trim_start + 1.0,
                max_value=clip_duration_edit,
                value=clip_duration_edit,
                step=0.5,
                format="%.1f",
            )

        trim_duration = trim_end - trim_start
        st.info(f"📏 Duración del recorte: **{format_seconds_to_time(trim_duration)}**")

        if trim_duration < 1.0:
            st.warning("⚠️ El recorte es demasiado corto. Define al menos 1 segundo de duración.")
        else:
            new_clip_name = st.text_input(
                "Nombre del nuevo clip (sin extensión):",
                value=f"{os.path.splitext(os.path.basename(clip_path_edit))[0]}_trim",
            )

            if st.button("✂️ Exportar Clip Recortado", key="export_trim"):
                output_trim_path = os.path.join(output_dir_edit, f"{new_clip_name}.mp4")

                try:
                    from video_editor import get_ffmpeg_path
                    import subprocess
                    ffmpeg_bin = get_ffmpeg_path()

                    with st.spinner(f"Exportando recorte de {format_seconds_to_time(trim_duration)}..."):
                        cmd = [
                            ffmpeg_bin, "-y",
                            "-ss", str(trim_start),
                            "-to", str(trim_end),
                            "-i", clip_path_edit,
                            "-c:v", "libx264",
                            "-preset", "veryfast",
                            "-crf", "22",
                            "-c:a", "aac",
                            "-b:a", "192k",
                            output_trim_path,
                        ]
                        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                    if result.returncode == 0 and os.path.exists(output_trim_path):
                        st.success(f"✅ Clip exportado: `{os.path.basename(output_trim_path)}`")

                        # Add to history
                        history_new = load_history(output_dir_edit)
                        now_str     = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        history_new.append({
                            "clip_name":            f"{new_clip_name}.mp4",
                            "clip_path":            output_trim_path,
                            "title":                f"{selected_item.get('title','Clip')} [Recorte]",
                            "start":                trim_start,
                            "end":                  trim_end,
                            "social_description":   selected_item.get("social_description", ""),
                            "virality_score":       selected_item.get("virality_score", 85),
                            "virality_explanation": selected_item.get("virality_explanation", ""),
                            "created_at":           now_str,
                            "video_format":         selected_item.get("video_format", "9:16"),
                        })
                        save_history(output_dir_edit, history_new)

                        with open(output_trim_path, "rb") as f_trim:
                            st.download_button(
                                label="⬇️ Descargar Clip Recortado",
                                data=f_trim,
                                file_name=f"{new_clip_name}.mp4",
                                mime="video/mp4",
                                key="dl_trim_result",
                            )
                    else:
                        st.error(f"❌ Error al exportar el clip:\n```\n{result.stderr[-1000:]}\n```")

                except Exception as trim_err:
                    st.error(f"❌ Error inesperado al recortar: {trim_err}")
                    import traceback
                    st.code(traceback.format_exc())


# ──────────────────────────────────────────────────────────────────────────────
# TAB 3: BIBLIOTECA
# ──────────────────────────────────────────────────────────────────────────────
with tab_lib:
    output_dir = get_persistent_output_dir()
    st.subheader("📚 Biblioteca y Historial de Clips")
    st.markdown(f"📁 **Carpeta de guardado:** `{output_dir}`")

    if st.button("📂 Abrir Carpeta en el Explorador"):
        try:
            os.startfile(output_dir)
        except Exception as e:
            st.error(f"No se pudo abrir la carpeta: {e}")

    st.write("---")

    history = load_history(output_dir)
    valid_history = [item for item in history if item.get("clip_path") and os.path.exists(item["clip_path"])]

    if not valid_history:
        st.info("Aún no tienes clips en tu biblioteca. ¡Procesa un video para empezar!")
    else:
        valid_history = list(reversed(valid_history))

        for idx, item in enumerate(valid_history):
            c_path  = item.get("clip_path",  "")
            c_name  = item.get("clip_name",  "")
            c_title = item.get("title",      "Clip Sin Título")
            c_start = item.get("start",      0)
            c_end   = item.get("end",        0)
            c_desc  = item.get("social_description", "")
            c_date  = item.get("created_at", "")
            c_fmt   = item.get("video_format", "9:16")

            with st.container():
                col_info, col_vid = st.columns([3, 2])
                with col_info:
                    st.markdown(f"### {c_title}")
                    st.markdown(
                        f"⏱️ **Original:** `{format_seconds_to_time(c_start)}` → "
                        f"`{format_seconds_to_time(c_end)}` ({c_fmt})"
                    )
                    st.caption(f"📅 Creado el: {c_date}")
                    render_virality_badge(
                        item.get("virality_score", 85),
                        item.get("virality_explanation", "Estructura narrativa sólida y gancho inicial de impacto."),
                    )
                    st.info(f"✍️ **Copy sugerido:**\n\n{c_desc}")

                    with st.expander("🎵 Mezclar Música de Fondo"):
                        lib_audio_file = st.file_uploader(
                            "Audio (.mp3, .wav, .m4a, .aac, .ogg)",
                            type=["mp3", "wav", "m4a", "aac", "ogg"],
                            key=f"audio_lib_{idx}_{c_name}",
                        )
                        lib_audio_vol = st.slider(
                            "Volumen de la música",
                            min_value=0.01, max_value=0.50, value=0.10, step=0.01,
                            key=f"vol_lib_{idx}_{c_name}",
                        )
                        if st.button("🎛️ Combinar Audio", key=f"btn_lib_{idx}_{c_name}"):
                            if lib_audio_file is not None:
                                temp_lib_path = os.path.join(
                                    tempfile.gettempdir(),
                                    f"temp_lib_{uuid.uuid4().hex}_{lib_audio_file.name}",
                                )
                                with open(temp_lib_path, "wb") as f_lib:
                                    f_lib.write(lib_audio_file.read())
                                with st.spinner("Mezclando audio..."):
                                    try:
                                        mix_background_music(c_path, temp_lib_path, lib_audio_vol, c_path)
                                        st.success("✅ ¡Música mezclada con éxito!")
                                    except Exception as mix_err:
                                        st.error(f"Error mezclando: {mix_err}")
                                    finally:
                                        if os.path.exists(temp_lib_path):
                                            os.remove(temp_lib_path)
                            else:
                                st.warning("Por favor, sube un archivo de audio primero.")

                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        try:
                            with open(c_path, "rb") as f:
                                st.download_button(
                                    label="⬇️ Descargar",
                                    data=f,
                                    file_name=c_name,
                                    mime="video/mp4",
                                    key=f"dl_{idx}_{c_name}",
                                )
                        except Exception:
                            st.error("Archivo no accesible.")
                    with col_b2:
                        if st.button("🗑️ Eliminar", key=f"del_{idx}_{c_name}"):
                            try:
                                if os.path.exists(c_path):
                                    os.remove(c_path)
                            except Exception as e:
                                st.warning(f"No se pudo borrar el archivo físico: {e}")
                            raw_history = load_history(output_dir)
                            raw_history = [x for x in raw_history if x.get("clip_path") != c_path]
                            save_history(output_dir, raw_history)
                            # Invalidate pipeline cache if the deleted clip was there
                            if st.session_state.output_dir_ss == output_dir:
                                st.session_state.pipeline_clips = [
                                    c for c in st.session_state.pipeline_clips
                                    if c.get("clip_path") != c_path
                                ]
                            st.success("Clip eliminado correctamente.")

                with col_vid:
                    with st.expander("📺 Reproducir Video", expanded=False):
                        st.video(c_path)

            st.markdown("---")
