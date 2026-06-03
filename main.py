import os
import argparse
import json
import shutil
from transcriber import extract_audio, transcribe_audio
from analyzer import analyze_audio_energy, select_best_moments_with_llm
from subtitle_generator import generate_ass_subtitles
from video_editor import process_video_clip

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
    temp_dir = "temp_processing"
    os.makedirs(temp_dir, exist_ok=True)
    
    temp_audio = os.path.join(temp_dir, "extracted_audio.wav")
    
    try:
                               
        extract_audio(args.video_path, temp_audio)
        
                            
        transcription_data = transcribe_audio(temp_audio, model_size=args.model, language=args.lang)
        
                                            
        clips = select_best_moments_with_llm(
            transcription_data,
            provider=provider,
            api_url=api_url,
            api_key=api_key,
            model=llm_model,
            clip_type=args.clip_type
        )

        
        print(f"[*] Se identificaron {len(clips)} momentos para procesar:")
        print(json.dumps(clips, indent=2, ensure_ascii=False))
        
                                   
        for idx, clip in enumerate(clips):
            start = clip["start"]
            end = clip["end"]
            title = clip.get("hook_title", f"clip_{idx+1}").replace(" ", "_").lower()
            
                            
            safe_title = "".join(c for c in title if c.isalnum() or c in ("_", "-"))
            clip_output_name = f"clip_{idx+1}_{safe_title}.mp4"
            clip_output_path = os.path.join(args.output_dir, clip_output_name)
            
                                                  
            ass_path = os.path.join(temp_dir, f"subtitles_{idx+1}.ass")
            generate_ass_subtitles(transcription_data, start, end, ass_path)
            
                                            
            process_video_clip(args.video_path, start, end, ass_path, clip_output_path)
            
        print(f"\n[+] Proceso completado con éxito. Clips guardados en: {args.output_dir}")
        
    finally:
                                      
        if os.path.exists(temp_dir):
            print("[*] Limpiando archivos temporales...")
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    main()
