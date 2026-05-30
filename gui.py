import os
import streamlit as st
import shutil
import json
from transcriber import extract_audio, transcribe_audio
from analyzer import select_best_moments_with_llm
from subtitle_generator import generate_ass_subtitles
from video_editor import process_video_clip

                       
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
st.markdown("<p style='text-align: center; color: #888;'>Corta, re-encuadra a 9:16 y genera subtítulos dinámicos de forma automática para TikTok y Shorts.</p>", unsafe_allow_html=True)

                        
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
                                         
        temp_uploaded_path = "temp_uploaded_video.mp4"
        with open(temp_uploaded_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        video_to_process = temp_uploaded_path
    elif local_path:
        if os.path.exists(local_path):
            video_to_process = local_path
        else:
            st.error(f"❌ La ruta local '{local_path}' no existe.")
            
    if video_to_process:
        temp_dir = "temp_gui_processing"
        output_dir = "output_clips_gui"
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
                
                           
                ass_path = os.path.join(temp_dir, f"subtitles_{idx+1}.ass")
                generate_ass_subtitles(transcription_data, start, end, ass_path)
                
                        
                status_area.write(f"🎬 Procesando video {idx+1}/{len(clips)}: '{clip.get('hook_title')}'...")
                process_video_clip(video_to_process, start, end, ass_path, clip_output_path)
                
            progress_bar.progress(100)
            status_area.success("🎉 ¡Todo listo! Clips creados correctamente.")
            
                             
            st.write("---")
            st.subheader("🎉 Clips Creados")
            
            result_cols = st.columns(len(clips) if len(clips) > 0 else 1)
            for idx, clip in enumerate(clips):
                title = clip.get("hook_title", f"Clip {idx+1}")
                safe_title = "".join(c for c in title.replace(" ", "_").lower() if c.isalnum() or c in ("_", "-"))
                clip_output_name = f"clip_{idx+1}_{safe_title}.mp4"
                clip_path = os.path.join(output_dir, clip_output_name)
                
                if os.path.exists(clip_path):
                    with result_cols[idx]:
                        st.markdown(f"### {title}")
                        st.video(clip_path)
                        
                                                                        
                        social_desc = clip.get("social_description", "¡Mira este clip!")
                        st.info(f"✍️ **Copy sugerido para TikTok/Shorts:**\n\n{social_desc}")
                        
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
