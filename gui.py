import os
import streamlit as st
import shutil
import tempfile
from transcriber import extract_audio, transcribe_audio
from analyzer import select_best_moments_with_llm
from subtitle_generator import generate_ass_subtitles, SUBTITLE_STYLES, AVAILABLE_FONTS
from video_editor import process_video_clip, compute_title_info, TITLE_STYLES, TITLE_FONTS, mix_background_music
import json
import datetime

def get_persistent_output_dir():
    home = os.path.expanduser("~")
    videos_dir = os.path.join(home, "Videos")
    if os.path.exists(videos_dir):
        path = os.path.join(videos_dir, "AutoClipperAI")
    else:
        path = os.path.join(home, "AutoClipperAI")
    os.makedirs(path, exist_ok=True)
    return path

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


# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Auto-Clipper AI",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
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
    .stButton>button:hover {
        transform: scale(1.02);
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🎬 Auto-Clipper AI</div>', unsafe_allow_html=True)
st.markdown(
    "<p style='text-align: center; color: #888;'>"
    "Corta, re-encuadra y genera subtítulos dinámicos de forma automática "
    "para TikTok, Shorts, YouTube y más."
    "</p>",
    unsafe_allow_html=True
)

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

# ── ⚙️ Sistema ────────────────────────────────────────────────────────────────
st.sidebar.header("⚙️ Configuración del Sistema")

whisper_model = st.sidebar.selectbox(
    "Modelo Whisper (Transcripción)",
    ["tiny", "base", "small", "medium"],
    index=2,
    help="'small' ofrece el mejor equilibrio velocidad/precisión en CPU."
)

lang = st.sidebar.text_input("Idioma del video", "es")

use_cloud_transcription = st.sidebar.checkbox(
    "☁️ Transcripción en la Nube (Groq/OpenAI)",
    value=False,
    help="Transcribe en segundos con Groq/OpenAI. Ideal para videos largos (> 5 min)."
)

st.sidebar.markdown("---")

# ── 🎞️ Formato de video ───────────────────────────────────────────────────────
st.sidebar.header("🎞️ Formato de Video")

video_format = st.sidebar.radio(
    "Tipo de video de salida",
    options=["9:16", "16:9", "1:1"],
    index=0,
    help="**9:16** → TikTok / Shorts / Reels\n\n**16:9** → YouTube horizontal\n\n**1:1** → Instagram Feed / Twitter"
)

FORMAT_LABELS = {
    "9:16": "📱 Vertical (9:16)",
    "16:9": "🖥️ Horizontal (16:9)",
    "1:1":  "⬛ Cuadrado (1:1)",
}

st.sidebar.markdown("---")

# ── 🎨 Subtítulos ─────────────────────────────────────────────────────────────
st.sidebar.header("🎨 Estilo de Subtítulos")

enable_subtitles = st.sidebar.checkbox(
    "✏️ Añadir subtítulos dinámicos",
    value=True,
    help="Desactiva si el video ya tiene subtítulos o no quieres añadirlos."
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
        options=AVAILABLE_FONTS,
        index=0,
    )
    sub_font_size = st.sidebar.slider(
        "Tamaño de letra (subtítulos)",
        min_value=40, max_value=130, value=75, step=5,
    )
    subtitle_position = st.sidebar.radio(
        "Posición de los subtítulos",
        options=["bottom", "center", "top"],
        format_func=lambda p: {
            "bottom": "⬇️ Abajo",
            "center": "↔️ Centro",
            "top":    "⬆️ Arriba",
        }[p],
        index=0,
    )
else:
    subtitle_style_key = "tiktok"
    sub_font_name      = "Arial Black"
    sub_font_size      = 75
    subtitle_position  = "bottom"

st.sidebar.markdown("---")

# ── 🏷️ Título ─────────────────────────────────────────────────────────────────
st.sidebar.header("🏷️ Título en el Video")

show_title = st.sidebar.checkbox(
    "📌 Quemar título en el video",
    value=True,
    help="Muestra el título recomendado por la IA como texto quemado en el clip."
)

if show_title:
    title_style_key = st.sidebar.selectbox(
        "Estilo del título",
        options=list(TITLE_STYLES.keys()),
        format_func=lambda k: TITLE_STYLES[k]["label"],
        index=0,
        help="Formato visual del título. Elige el que mejor encaja con tu contenido."
    )
    title_font = st.sidebar.selectbox(
        "Tipo de letra (título)",
        options=TITLE_FONTS,
        index=0,
    )
    title_font_size = st.sidebar.slider(
        "Tamaño de letra (título)",
        min_value=40, max_value=160, value=90, step=5,
        help="Tamaño en px referenciado a 1920px de alto. Se escala automáticamente."
    )
    title_position = st.sidebar.radio(
        "Posición del título",
        options=["top", "center", "bottom"],
        format_func=lambda p: {
            "top":    "⬆️ Arriba",
            "center": "↔️ Centro",
            "bottom": "⬇️ Abajo",
        }[p],
        index=0,
    )
else:
    title_style_key  = "clasico"
    title_font       = "Arial Bold"
    title_font_size  = 90
    title_position   = "top"

st.sidebar.markdown("---")

# ── 🤖 IA ─────────────────────────────────────────────────────────────────────
st.sidebar.header("🤖 Inferencia AI (Selección de Momentos)")

provider = st.sidebar.selectbox(
    "Proveedor de IA",
    ["ollama", "openai", "groq"],
    index=0
)

api_key = ""
if provider in ["openai", "groq"]:
    api_key = st.sidebar.text_input("Clave API (API Key)", type="password")

default_model = (
    "llama3.2:3b" if provider == "ollama"
    else ("gpt-4o-mini" if provider == "openai" else "llama-3.3-70b-versatile")
)
llm_model = st.sidebar.text_input("Modelo de IA", default_model)
max_clips = st.sidebar.slider(
    "Número máximo de clips a generar",
    min_value=1, max_value=10, value=3, step=1,
    help="Indica a la IA cuántos clips virales como máximo debe buscar."
)
clip_type = st.sidebar.text_input(
    "Tipo de clips a buscar",
    value="virales, entretenidos, informativos o con un gancho (hook) muy fuerte",
    help="Indica qué tipo de contenido o tono debe buscar la IA (por ejemplo: 'polémicos', 'graciosos', 'educativos', 'momentos de tensión')."
)

# Resolve API URL
api_url = "http://localhost:11434/api/generate"
if provider == "groq":
    api_url = "https://api.groq.com/openai/v1/chat/completions"
    resolved_provider = "openai"
elif provider == "openai":
    api_url = "https://api.openai.com/v1/chat/completions"
    resolved_provider = "openai"
else:
    resolved_provider = "ollama"

# ══════════════════════════════════════════════════════════════════════════════
# MAIN AREA
# ══════════════════════════════════════════════════════════════════════════════

tab_proc, tab_lib = st.tabs(["🚀 Procesador de Clips", "📚 Biblioteca de Clips"])

with tab_proc:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📹 Cargar Video")
        uploaded_file = st.file_uploader(
            "Selecciona un video (MP4/MKV/MOV)",
            type=["mp4", "mkv", "mov"],
            max_upload_size=10240
        )
        st.info("💡 Una vez subido el video, haz clic en 'Comenzar Pipeline' para procesar.")
        local_path = st.text_input("O introduce la ruta de un archivo local (más rápido):")

    with col2:
        st.subheader("📋 Consola de Procesamiento")
        process_btn  = st.button("🚀 Comenzar Pipeline")
        status_area  = st.empty()
        progress_bar = st.progress(0)

    # ══════════════════════════════════════════════════════════════════════════════
    # PIPELINE
    # ══════════════════════════════════════════════════════════════════════════════

    if process_btn:
        video_to_process = ""
        temp_uploaded_path = None

        if uploaded_file is not None:
            import uuid
            temp_uploaded_path = os.path.join(
                tempfile.gettempdir(),
                f"temp_uploaded_video_{uuid.uuid4().hex}.mp4"
            )
            with open(temp_uploaded_path, "wb") as f:
                f.write(uploaded_file.read())

            if not os.path.exists(temp_uploaded_path):
                st.error("❌ No se pudo guardar el video temporal. Intenta usar la ruta local.")
            else:
                file_size = os.path.getsize(temp_uploaded_path)
                status_area.write(f"✅ Video temporal guardado en {temp_uploaded_path} ({file_size // (1024*1024)} MB)")
                video_to_process = temp_uploaded_path
        elif local_path:
            if os.path.exists(local_path):
                video_to_process = local_path
            else:
                st.error(f"❌ La ruta local '{local_path}' no existe.")

        if video_to_process:
            temp_dir   = os.path.join(tempfile.gettempdir(), "temp_gui_processing")
            output_dir = get_persistent_output_dir()
            os.makedirs(temp_dir,   exist_ok=True)
            os.makedirs(output_dir, exist_ok=True)
            temp_audio = os.path.join(temp_dir, "extracted_audio.wav")

            try:
                # ── Paso 1: Audio ──────────────────────────────────────────────
                if not os.path.exists(video_to_process):
                    raise FileNotFoundError(f"El archivo de video no existe: {video_to_process}")

                status_area.write("⏳ Paso 1: Extrayendo audio del video...")
                progress_bar.progress(10)
                extract_audio(video_to_process, temp_audio)

                # ── Paso 2: Transcripción ──────────────────────────────────────
                if use_cloud_transcription and provider in ["groq", "openai"] and api_key:
                    status_area.write(
                        f"⏳ Paso 2: Transcribiendo en la nube con {provider} (ultra rápido)..."
                    )
                    progress_bar.progress(30)
                    from transcriber import transcribe_audio_cloud
                    trans_api_url = None
                    if provider == "openai" and api_url and "completions" not in api_url:
                        trans_api_url = api_url
                    transcription_data = transcribe_audio_cloud(
                        temp_audio, api_key=api_key, provider=provider,
                        api_url=trans_api_url, language=lang
                    )
                else:
                    status_area.write("⏳ Paso 2: Transcribiendo localmente con Whisper...")
                    progress_bar.progress(30)
                    transcription_data = transcribe_audio(
                        temp_audio, model_size=whisper_model, language=lang
                    )

                # ── Paso 3: IA selecciona momentos ────────────────────────────
                status_area.write("⏳ Paso 3: Identificando los mejores momentos con IA...")
                progress_bar.progress(60)
                clips = select_best_moments_with_llm(
                    transcription_data,
                    provider=resolved_provider,
                    api_url=api_url,
                    api_key=api_key if api_key else None,
                    model=llm_model,
                    max_clips=max_clips,
                    clip_type=clip_type
                )

                status_area.write(f"✅ Se encontraron {len(clips)} momentos. Creando clips...")
                progress_bar.progress(75)

                # ── Paso 4: Generar clips ──────────────────────────────────────
                for idx, clip in enumerate(clips):
                    start      = clip["start"]
                    end        = clip["end"]
                    clip_title = clip.get("hook_title", f"clip_{idx+1}")
                    safe_title = "".join(
                        c for c in clip_title.replace(" ", "_").lower()
                        if c.isalnum() or c in ("_", "-")
                    )
                    clip_output_name = f"clip_{idx+1}_{safe_title}.mp4"
                    clip_output_path = os.path.join(output_dir, clip_output_name)

                    # ── Calcular offset si título y subtítulos comparten borde ──
                    subtitle_margin_override = None
                    if show_title and clip_title and enable_subtitles and title_position == subtitle_position:
                        anchor_px, title_h = compute_title_info(
                            clip_title, video_format, title_position, title_font_size
                        )
                        subtitle_margin_override = anchor_px + title_h + 20

                    # ── Generar ASS ────────────────────────────────────────────
                    ass_path = None
                    if enable_subtitles:
                        ass_path = os.path.join(temp_dir, f"subtitles_{idx+1}.ass")
                        generate_ass_subtitles(
                            transcription_data, start, end, ass_path,
                            subtitle_position=subtitle_position,
                            font_name=sub_font_name,
                            font_size=sub_font_size,
                            subtitle_style=subtitle_style_key,
                            margin_override=subtitle_margin_override,
                        )

                    # ── Procesar clip con FFmpeg ───────────────────────────────
                    status_area.write(
                        f"🎬 Procesando {idx+1}/{len(clips)}: '{clip_title}'..."
                    )
                    process_video_clip(
                        video_to_process, start, end, ass_path, clip_output_path,
                        video_format=video_format,
                        hook_title=clip_title if show_title else "",
                        title_position=title_position,
                        title_font_size=title_font_size,
                        title_style=title_style_key,
                        title_font=title_font,
                        subtitle_position=subtitle_position,
                    )

                progress_bar.progress(100)
                status_area.success("🎉 ¡Todo listo! Clips creados correctamente.")

                # ── Guardar en el historial ─────────────────────────────────────
                history = load_history(output_dir)
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for idx, clip in enumerate(clips):
                    clip_title     = clip.get("hook_title", f"Clip {idx+1}")
                    safe_title     = "".join(
                        c for c in clip_title.replace(" ", "_").lower()
                        if c.isalnum() or c in ("_", "-")
                    )
                    clip_output_name = f"clip_{idx+1}_{safe_title}.mp4"
                    clip_path        = os.path.join(output_dir, clip_output_name)
                    if os.path.exists(clip_path):
                        if not any(item.get("clip_path") == clip_path for item in history):
                            history.append({
                                "clip_name": clip_output_name,
                                "clip_path": clip_path,
                                "title": clip_title,
                                "start": clip.get("start", 0),
                                "end": clip.get("end", 0),
                                "social_description": clip.get("social_description", ""),
                                "created_at": now_str,
                                "video_format": video_format
                            })
                save_history(output_dir, history)

                # ── Mostrar resultados ─────────────────────────────────────────
                st.write("---")
                st.subheader("🎉 Clips Creados")

                n_clips      = max(len(clips), 1)
                result_cols  = st.columns(min(n_clips, 3))
                VIDEO_WIDTH_MAP = {"9:16": 320, "16:9": 560, "1:1": 420}
                player_width = VIDEO_WIDTH_MAP.get(video_format, 400)
                def format_seconds_to_time(seconds):
                    mins = int(seconds // 60)
                    secs = int(seconds % 60)
                    centis = int(round((seconds % 1) * 100))
                    if centis == 100:
                        secs += 1
                        centis = 0
                    return f"{mins:02d}:{secs:02d}.{centis:02d}"

                for idx, clip in enumerate(clips):
                    start          = clip.get("start", 0)
                    end            = clip.get("end", 0)
                    clip_title     = clip.get("hook_title", f"Clip {idx+1}")
                    safe_title     = "".join(
                        c for c in clip_title.replace(" ", "_").lower()
                        if c.isalnum() or c in ("_", "-")
                    )
                    clip_output_name = f"clip_{idx+1}_{safe_title}.mp4"
                    clip_path        = os.path.join(output_dir, clip_output_name)

                    if os.path.exists(clip_path):
                        with result_cols[idx % 3]:
                            st.markdown(f"### {clip_title}")
                            st.markdown(f"⏱️ **Original:** `{format_seconds_to_time(start)}` al `{format_seconds_to_time(end)}`")
                            st.caption(FORMAT_LABELS.get(video_format, video_format))
                            st.markdown(
                                f"<div style='max-width:{player_width}px;'>",
                                unsafe_allow_html=True
                            )
                            st.video(clip_path)
                            st.markdown("</div>", unsafe_allow_html=True)

                            social_desc = clip.get("social_description", "¡Mira este clip!")
                            st.info(f"✍️ **Copy sugerido:**\n\n{social_desc}")

                            with st.expander("🎵 Mezclar Música de Fondo"):
                                sub_audio_file = st.file_uploader(
                                    "Audio (.mp3, .wav, .m4a, .aac, .ogg)",
                                    type=["mp3", "wav", "m4a", "aac", "ogg"],
                                    key=f"audio_proc_{idx}_{safe_title}"
                                )
                                sub_audio_vol = st.slider(
                                    "Volumen de la música",
                                    min_value=0.01, max_value=0.50, value=0.10, step=0.01,
                                    key=f"vol_proc_{idx}_{safe_title}"
                                )
                                if st.button("🎛️ Combinar Audio", key=f"btn_proc_{idx}_{safe_title}"):
                                    if sub_audio_file is not None:
                                        import uuid
                                        temp_sub_path = os.path.join(
                                            tempfile.gettempdir(),
                                            f"temp_sub_{uuid.uuid4().hex}_{sub_audio_file.name}"
                                        )
                                        with open(temp_sub_path, "wb") as f_sub:
                                            f_sub.write(sub_audio_file.read())
                                        
                                        with st.spinner("Mezclando audio..."):
                                            try:
                                                mix_background_music(
                                                    clip_path, temp_sub_path, sub_audio_vol, clip_path
                                                )
                                                st.success("¡Música mezclada con éxito!")
                                                st.rerun()
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
                                    mime="video/mp4"
                                )

            except Exception as e:
                st.error(f"❌ Error en el procesamiento: {e}")
                import traceback
                st.code(traceback.format_exc())
            finally:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
                if temp_uploaded_path:
                    try:
                        if os.path.exists(temp_uploaded_path):
                            os.remove(temp_uploaded_path)
                    except Exception:
                        pass
        else:
            st.warning("⚠️ Sube un video o ingresa la ruta de un archivo local válido.")

with tab_lib:
    output_dir = get_persistent_output_dir()
    st.subheader("📚 Biblioteca y Historial de Clips")
    st.markdown(f"📁 **Carpeta de guardado:** `{output_dir}`")

    # Botón para abrir la carpeta (solo funciona localmente)
    if st.button("📂 Abrir Carpeta en el Explorador"):
        try:
            os.startfile(output_dir)
        except Exception as e:
            st.error(f"No se pudo abrir la carpeta: {e}")

    st.write("---")

    history = load_history(output_dir)
    # Filtrar solo entradas que correspondan a archivos físicos reales que existan
    valid_history = []
    for item in history:
        c_path = item.get("clip_path", "")
        if c_path and os.path.exists(c_path):
            valid_history.append(item)

    if not valid_history:
        st.info("Aún no tienes clips en tu biblioteca. ¡Procesa un video para empezar!")
    else:
        # Ordenar de más reciente a más antiguo
        valid_history = list(reversed(valid_history))

        def format_seconds_to_time(seconds):
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            centis = int(round((seconds % 1) * 100))
            if centis == 100:
                secs += 1
                centis = 0
            return f"{mins:02d}:{secs:02d}.{centis:02d}"

        for idx, item in enumerate(valid_history):
            c_path = item.get("clip_path", "")
            c_name = item.get("clip_name", "")
            c_title = item.get("title", "Clip Sin Título")
            c_start = item.get("start", 0)
            c_end = item.get("end", 0)
            c_desc = item.get("social_description", "")
            c_date = item.get("created_at", "")
            c_fmt = item.get("video_format", "9:16")

            with st.container():
                col_info, col_vid = st.columns([3, 2])
                with col_info:
                    st.markdown(f"### {c_title}")
                    st.markdown(f"⏱️ **Original:** `{format_seconds_to_time(c_start)}` al `{format_seconds_to_time(c_end)}` ({c_fmt})")
                    st.caption(f"📅 Creado el: {c_date}")
                    st.info(f"✍️ **Copy sugerido:**\n\n{c_desc}")

                    with st.expander("🎵 Mezclar Música de Fondo"):
                        lib_audio_file = st.file_uploader(
                            "Audio (.mp3, .wav, .m4a, .aac, .ogg)",
                            type=["mp3", "wav", "m4a", "aac", "ogg"],
                            key=f"audio_lib_{idx}_{c_name}"
                        )
                        lib_audio_vol = st.slider(
                            "Volumen de la música",
                            min_value=0.01, max_value=0.50, value=0.10, step=0.01,
                            key=f"vol_lib_{idx}_{c_name}"
                        )
                        if st.button("🎛️ Combinar Audio", key=f"btn_lib_{idx}_{c_name}"):
                            if lib_audio_file is not None:
                                import uuid
                                temp_lib_path = os.path.join(
                                    tempfile.gettempdir(),
                                    f"temp_lib_{uuid.uuid4().hex}_{lib_audio_file.name}"
                                )
                                with open(temp_lib_path, "wb") as f_lib:
                                    f_lib.write(lib_audio_file.read())
                                
                                with st.spinner("Mezclando audio..."):
                                    try:
                                        mix_background_music(
                                            c_path, temp_lib_path, lib_audio_vol, c_path
                                        )
                                        st.success("¡Música mezclada con éxito!")
                                        st.rerun()
                                    except Exception as mix_err:
                                        st.error(f"Error mezclando: {mix_err}")
                                    finally:
                                        if os.path.exists(temp_lib_path):
                                            os.remove(temp_lib_path)
                            else:
                                st.warning("Por favor, sube un archivo de audio primero.")

                    # Botones de descarga y eliminación
                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        try:
                            with open(c_path, "rb") as f:
                                st.download_button(
                                    label="⬇️ Descargar",
                                    data=f,
                                    file_name=c_name,
                                    mime="video/mp4",
                                    key=f"dl_{idx}_{c_name}"
                                )
                        except Exception:
                            st.error("Archivo no accesible.")
                    with col_b2:
                        if st.button("🗑️ Eliminar", key=f"del_{idx}_{c_name}"):
                            # Eliminar archivo físico
                            try:
                                if os.path.exists(c_path):
                                    os.remove(c_path)
                            except Exception as e:
                                st.warning(f"No se pudo borrar el archivo físico: {e}")

                            # Eliminar del registro JSON
                            raw_history = load_history(output_dir)
                            raw_history = [x for x in raw_history if x.get("clip_path") != c_path]
                            save_history(output_dir, raw_history)
                            st.success("Clip eliminado correctamente.")
                            st.rerun()
                with col_vid:
                    VIDEO_WIDTH_MAP = {"9:16": 200, "16:9": 300, "1:1": 250}
                    player_width = VIDEO_WIDTH_MAP.get(c_fmt, 250)
                    st.markdown(f"<div style='max-width:{player_width}px;'>", unsafe_allow_html=True)
                    st.video(c_path)
                    st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("---")
