import os
import sys
import argparse
import json
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from autoclipper import (
    extract_audio,
    transcribe_audio,
    analyze_audio_energy,
    select_best_moments_with_llm,
    generate_ass_subtitles,
    process_video_clip,
    is_portrait_video,
)

def main():
    parser = argparse.ArgumentParser(description="Auto-Clipper AI: Transforma videos largos a Shorts/TikToks de forma ligera.")
    parser.add_argument("video_path", help="Ruta al video original (16:9)")
    parser.add_argument("--output_dir", default="output_clips", help="Carpeta de salida para los clips")
    parser.add_argument("--model", default="small", help="Modelo de Faster-Whisper a usar (tiny, base, small, medium)")
    parser.add_argument("--lang", default="es", help="Idioma del video (por defecto: es)")
    parser.add_argument("--provider", default="ollama", choices=["ollama", "openai", "groq"], help="Proveedor de LLM para elegir mejores momentos")
    parser.add_argument("--api_url", default="http://localhost:11434/api/generate", help="URL de la API de Ollama o OpenAI")
    parser.add_argument("--api_key", default=None, help="API Key si se usa proveedor OpenAI o Groq")
    parser.add_argument("--llm_model", default="llama3.2:3b", help="Modelo de LLM a usar en Ollama, OpenAI o Groq")
    parser.add_argument("--clip_type", default="virales, entretenidos, informativos o con un gancho (hook) muy fuerte", help="Tipo de clips a buscar (ej: polémicos, educativos, etc.)")
    parser.add_argument("--camera_tracking", action="store_true", help="Habilitar el seguimiento de rostro inteligente para re-encuadre vertical")
    parser.add_argument("--fade_effect", action="store_true", help="Habilitar la animación de entrada/salida (transiciones fade) en los clips")
    parser.add_argument("--max_clips", type=int, default=10, help="Número máximo de clips a generar")
    parser.add_argument("--min_clips", type=int, default=3, help="Número mínimo de clips a generar")
    parser.add_argument("--use_gpu", action="store_true", help="Habilitar aceleración por GPU (NVIDIA CUDA) para transcripción y renderizado")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.video_path):
        print(f"[!] Error: El archivo de video {args.video_path} no existe.")
        return

                               
    provider = args.provider
    api_url = args.api_url
    api_key = args.api_key
    llm_model = args.llm_model

    if provider == "groq":
        provider = "openai"                                            
        if api_url == "http://localhost:11434/api/generate":
            api_url = "https://api.groq.com/openai/v1/chat/completions"
        if llm_model == "llama3.2:3b":
            llm_model = "llama-3.3-70b-versatile"
        if not api_key:
            api_key = os.environ.get("GROQ_API_KEY")
            if not api_key:
                print("[!] Advertencia: Se seleccionó Groq pero no se encontró la clave API en la variable de entorno GROQ_API_KEY ni en el argumento --api_key.")

        
    os.makedirs(args.output_dir, exist_ok=True)
    # Use an absolute path so temp files are always alongside this script,
    # regardless of the working directory from which main.py is called.
    base_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dir = os.path.join(base_dir, "temp_processing")
    os.makedirs(temp_dir, exist_ok=True)

    temp_audio = os.path.join(temp_dir, "extracted_audio.wav")
    
    try:
                               
        extract_audio(args.video_path, temp_audio)
        
                            
        transcription_data = transcribe_audio(temp_audio, model_size=args.model, language=args.lang, use_gpu=args.use_gpu)
        
                                            
        clips = select_best_moments_with_llm(
            transcription_data,
            provider=provider,
            api_url=api_url,
            api_key=api_key,
            model=llm_model,
            max_clips=args.max_clips,
            min_clips=args.min_clips,
            clip_type=args.clip_type
        )

        
        print(f"[*] Se identificaron {len(clips)} momentos para procesar:")
        print(json.dumps(clips, indent=2, ensure_ascii=False))

        # Pre-compute portrait detection ONCE for all clips (avoids N OpenCV file opens)
        source_portrait = is_portrait_video(args.video_path) if args.camera_tracking else False

        for idx, clip in enumerate(clips):
            start = clip["start"]
            end   = clip["end"]
            title = clip.get("hook_title", f"clip_{idx+1}").replace(" ", "_").lower()

            safe_title = "".join(c for c in title if c.isalnum() or c in ("_", "-"))
            clip_output_name = f"clip_{idx+1}_{safe_title}.mp4"
            clip_output_path = os.path.join(args.output_dir, clip_output_name)

            ass_path = None # Subtitles disabled for maximum speed
            process_video_clip(
                args.video_path, start, end, ass_path, clip_output_path,
                camera_tracking=False, # Camera tracking disabled for maximum speed
                fade_effect=args.fade_effect,
                use_gpu=args.use_gpu,
                source_is_portrait=False,
            )
            
        print(f"\n[+] Proceso completado con éxito. Clips guardados en: {args.output_dir}")
        
    finally:
                                      
        if os.path.exists(temp_dir):
            print("[*] Limpiando archivos temporales...")
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    main()
