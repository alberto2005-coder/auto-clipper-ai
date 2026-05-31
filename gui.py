import os
import streamlit as st
import shutil
import json
import tempfile
from transcriber import extract_audio, transcribe_audio
from analyzer import select_best_moments_with_llm
from subtitle_generator import generate_ass_subtitles, SUBTITLE_STYLES, AVAILABLE_FONTS
from video_editor import process_video_clip, compute_title_info

                       
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
st.markdown("<p style='text-align: center; color: #888;'>Corta, re-encuadra y genera subtítulos dinámicos de forma automática para TikTok, Shorts, YouTube y más.</p>", unsafe_allow_html=True)

                        
st.sidebar.header("⚙️ Configuración del Sistema")

whisper_model = st.sidebar.selectbox(
    "Modelo Whisper (Transcripción)",
    ["tiny", "base", "small", "medium"],
    index=2,
    help="El modelo 'small' ofrece el mejor equilibrio entre precisión y velocidad en tu CPU."
)

lang = st.sidebar.text_input("Idioma del video", "es")

use_cloud_transcription = st.sidebar.checkbox(
    "☁️ Transcripción en la Nube (Groq/OpenAI)",
    value=False,
    help="Usa la API de Groq o OpenAI para transcribir el audio en segundos en la nube. ¡Ideal para videos largos de más de 5 minutos!"
)


st.sidebar.markdown("---")

st.sidebar.header("🎞️ Formato de Video")

video_format = st.sidebar.radio(
    "Tipo de video de salida",
    options=["9:16", "16:9", "1:1"],
    index=0,
    help="**9:16** → TikTok / YouTube Shorts / Instagram Reels\n\n**16:9** → YouTube horizontal / presentaciones\n\n**1:1** → Instagram Feed / Twitter"
)

FORMAT_LABELS = {
    "9:16": "📱 Vertical (9:16)",
    "16:9": "🖥️ Horizontal (16:9)",
    "1:1":  "⬛ Cuadrado (1:1)",
}

st.sidebar.markdown("---")

st.sidebar.header("🎨 Estilo de Subtítulos")

enable_subtitles = st.sidebar.checkbox(
    "✏️ Añadir subtítulos dinámicos",
    value=True,
    help="Desactiva esto si el video ya tiene subtítulos propios o no quieres añadirlos."
)

if enable_subtitles:
    subtitle_style_key = st.sidebar.selectbox(
        "Estilo de color",
        options=list(SUBTITLE_STYLES.keys()),
        format_func=lambda k: SUBTITLE_STYLES[k]["label"],
        index=0,
    )
    font_name = st.sidebar.selectbox(
        "Tipo de letra",
        options=AVAILABLE_FONTS,
        index=0,
    )
    font_size = st.sidebar.slider(
        "Tamaño de letra",
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
    font_name = "Arial Black"
    font_size = 75
    subtitle_position = "bottom"

st.sidebar.markdown("---")

st.sidebar.header("🏷️ Título en el Video")

show_title = st.sidebar.checkbox(
    "📌 Quemar título en el video",
    value=True,
    help="Muestra el título recomendado por la IA como texto dentro del clip."
)

if show_title:
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
    title_position = "top"

st.sidebar.markdown("---")

st.sidebar.header("🤖 Inferencia AI (Selección de Momentos)")

provider = st.sidebar.selectbox(
    "Proveedor de IA",
    ["ollama", "openai", "groq"],
    index=0
)

api_key = ""
if provider in ["openai", "groq"]:
    api_key = st.sidebar.text_input("Clave API (API Key)", type="password")

default_model = "llama3.2:3b" if provider == "ollama" else ("gpt-4o-mini" if provider == "openai" else "llama-3.3-70b-versatile")
llm_model = st.sidebar.text_input("Modelo de IA", default_model)

              
api_url = "http://localhost:11434/api/generate"
if provider == "groq":
    api_url = "https://api.groq.com/openai/v1/chat/completions"
    resolved_provider = "openai"
elif provider == "openai":
    api_url = "https://api.openai.com/v1/chat/completions"
    resolved_provider = "openai"
else:
    resolved_provider = "ollama"

           
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📹 Cargar Video")
    uploaded_file = st.file_uploader("Selecciona un video (MP4/MKV/MOV)", type=["mp4", "mkv", "mov"])
    
    st.info("💡 Consejo: Una vez subido el video, haz clic en 'Comenzar Pipeline' para procesar.")
    
                                                      
    local_path = st.text_input("O introduce la ruta de un archivo local (más rápido):")

with col2:
    st.subheader("📋 Consola de Procesamiento")
    process_btn = st.button("🚀 Comenzar Pipeline")
    
    status_area = st.empty()
    progress_bar = st.progress(0)

                
if process_btn:
    video_to_process = ""
    
    if uploaded_file is not None:
                                         
        temp_uploaded_path = os.path.join(tempfile.gettempdir(), "temp_uploaded_video.mp4")
        with open(temp_uploaded_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        video_to_process = temp_uploaded_path
    elif local_path:
        if os.path.exists(local_path):
            video_to_process = local_path
        else:
            st.error(f"❌ La ruta local '{local_path}' no existe.")
            
    if video_to_process:
        temp_dir = os.path.join(tempfile.gettempdir(), "temp_gui_processing")
        output_dir = os.path.join(tempfile.gettempdir(), "output_clips_gui")
        os.makedirs(temp_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        
        temp_audio = os.path.join(temp_dir, "extracted_audio.wav")
        
        try:
                                   
            status_area.write("⏳ Paso 1: Extrayendo audio del video...")
            progress_bar.progress(10)
            extract_audio(video_to_process, temp_audio)
            
                                
            if use_cloud_transcription and provider in ["groq", "openai"] and api_key:
                status_area.write(f"⏳ Paso 2: Transcribiendo el audio en la nube con {provider} (ultra rápido)...")
                progress_bar.progress(30)
                from transcriber import transcribe_audio_cloud
                                                                                                                         
                trans_api_url = None
                if provider == "openai" and api_url and "completions" not in api_url:
                    trans_api_url = api_url
                transcription_data = transcribe_audio_cloud(temp_audio, api_key=api_key, provider=provider, api_url=trans_api_url, language=lang)
            else:
                status_area.write("⏳ Paso 2: Transcribiendo el audio localmente con Whisper...")
                progress_bar.progress(30)
                transcription_data = transcribe_audio(temp_audio, model_size=whisper_model, language=lang)

            
                                     
            status_area.write("⏳ Paso 3: Identificando los mejores momentos con IA...")
            progress_bar.progress(60)
            
            clips = select_best_moments_with_llm(
                transcription_data,
                provider=resolved_provider,
                api_url=api_url,
                api_key=api_key if api_key else None,
                model=llm_model
            )
            
            status_area.write(f"✅ Se encontraron {len(clips)} momentos virales. Creando los videos...")
            progress_bar.progress(75)
            
                                   
            for idx, clip in enumerate(clips):
                start = clip["start"]
                end = clip["end"]
                title = clip.get("hook_title", f"clip_{idx+1}").replace(" ", "_").lower()
                safe_title = "".join(c for c in title if c.isalnum() or c in ("_", "-"))
                
                clip_output_name = f"clip_{idx+1}_{safe_title}.mp4"
                clip_output_path = os.path.join(output_dir, clip_output_name)
                
                           
                # ── Calcular offset de subtítulos si colisionan con el título ───────────
                # Si título y subtítulos están en el mismo borde, el subtitulo
                # arranca justo donde termina el bloque del título (+ 20px gap).
                subtitle_margin_override = None
                clip_title = clip.get("hook_title", "")
                if show_title and clip_title and enable_subtitles and title_position == subtitle_position:
                    anchor_px, title_h = compute_title_info(clip_title, video_format, title_position)
                    subtitle_margin_override = anchor_px + title_h + 20

                # ── Generar subtítulos ASS solo si el usuario los activó ────────────
                ass_path = None
                if enable_subtitles:
                    ass_path = os.path.join(temp_dir, f"subtitles_{idx+1}.ass")
                    generate_ass_subtitles(
                        transcription_data, start, end, ass_path,
                        subtitle_position=subtitle_position,
                        font_name=font_name,
                        font_size=font_size,
                        subtitle_style=subtitle_style_key,
                        margin_override=subtitle_margin_override,
                    )
                
                        
                status_area.write(f"🎬 Procesando video {idx+1}/{len(clips)}: '{clip.get('hook_title')}'...")
                process_video_clip(
                    video_to_process, start, end, ass_path, clip_output_path,
                    video_format=video_format,
                    hook_title=clip.get("hook_title", "") if show_title else "",
                    title_position=title_position,
                    subtitle_position=subtitle_position,
                )
                
            progress_bar.progress(100)
            status_area.success("🎉 ¡Todo listo! Clips creados correctamente.")
            
                             
            st.write("---")
            st.subheader("🎉 Clips Creados")

            # Determine a sensible column layout (max 3 per row)
            n_clips = len(clips) if len(clips) > 0 else 1
            result_cols = st.columns(min(n_clips, 3))

            # Video player width: vertical needs less horizontal space than horizontal formats
            VIDEO_WIDTH_MAP = {"9:16": 320, "16:9": 560, "1:1": 420}
            player_width = VIDEO_WIDTH_MAP.get(video_format, 400)

            for idx, clip in enumerate(clips):
                title = clip.get("hook_title", f"Clip {idx+1}")
                safe_title = "".join(c for c in title.replace(" ", "_").lower() if c.isalnum() or c in ("_", "-"))
                clip_output_name = f"clip_{idx+1}_{safe_title}.mp4"
                clip_path = os.path.join(output_dir, clip_output_name)

                if os.path.exists(clip_path):
                    col = result_cols[idx % 3]
                    with col:
                        st.markdown(f"### {title}")
                        st.caption(FORMAT_LABELS.get(video_format, video_format))

                        # Wrap the video player in a fixed-width div so it doesn't stretch
                        st.markdown(
                            f"<div style='max-width:{player_width}px;'>",
                            unsafe_allow_html=True
                        )
                        st.video(clip_path)
                        st.markdown("</div>", unsafe_allow_html=True)

                        social_desc = clip.get("social_description", "¡Mira este clip!")
                        st.info(f"✍️ **Copy sugerido:**\n\n{social_desc}")

                        with open(clip_path, "rb") as file:
                            st.download_button(
                                label=f"⬇️ Descargar Clip",
                                data=file,
                                file_name=clip_output_name,
                                mime="video/mp4"
                            )

                            
        except Exception as e:
            st.error(f"❌ Error en el procesamiento: {e}")
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            if uploaded_file is not None and os.path.exists(temp_uploaded_path):
                os.remove(temp_uploaded_path)
    else:
        st.warning("⚠️ Sube un video o ingresa la ruta de un archivo local válido.")
