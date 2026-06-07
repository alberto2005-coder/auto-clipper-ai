import os
import subprocess
import tempfile
import uuid
from faster_whisper import WhisperModel

def get_ffmpeg_path():
    """Resolves path to FFmpeg strictly using imageio-ffmpeg."""
    import sys
    
    # Si estamos corriendo como .exe empaquetado por PyInstaller
    if getattr(sys, 'frozen', False):
        for root, dirs, files in os.walk(sys._MEIPASS):
            for file in files:
                if file.startswith("ffmpeg") and file.endswith(".exe"):
                    return os.path.join(root, file)
                    
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()

def extract_audio(video_path, audio_path="temp_audio.wav"):
    """Extracts audio from a video file using FFmpeg."""
    print(f"[*] Extracting audio from {video_path}...")
    ffmpeg_bin = get_ffmpeg_path()
    cmd = [
        ffmpeg_bin, "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        audio_path
    ]

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except FileNotFoundError as fnf:
        raise RuntimeError(f"Error de sistema: No se pudo ejecutar el binario de FFmpeg. Verifica su disponibilidad en '{ffmpeg_bin}'.") from fnf
    except Exception as e:
        raise RuntimeError(f"Error crítico al intentar extraer el audio del video con FFmpeg: {e}") from e

    if result.returncode != 0:
        if "does not contain any stream" in result.stderr or "Output file does not contain any stream" in result.stderr:
            print("[*] No audio stream detected in video. Generating a silent audio track...")
            import re
            duration = 10.0
            match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", result.stderr)
            if match:
                hours, minutes, seconds = match.groups()
                duration = int(hours) * 3600 + int(minutes) * 60 + float(seconds)

            silent_cmd = [
                ffmpeg_bin, "-y",
                "-f", "lavfi",
                "-i", "anullsrc=r=16000:cl=mono",
                "-t", str(duration),
                audio_path
            ]
            subprocess.run(silent_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        else:
            raise RuntimeError(f"FFmpeg failed to extract audio. Error:\n{result.stderr}")
    return audio_path


def compress_audio_for_transcription(source_path, target_path, bitrate="32k"):
    """Compress audio to MP3 for cloud transcription uploads."""
    ffmpeg_bin = get_ffmpeg_path()
    cmd = [
        ffmpeg_bin, "-y",
        "-i", source_path,
        "-ac", "1",
        "-ar", "16000",
        "-b:a", bitrate,
        target_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return target_path


def transcribe_audio(audio_path, model_size="small", language="es", use_gpu=False):
    """Transcribes audio using faster-whisper on CPU or GPU."""
    device = "cuda" if use_gpu else "cpu"
    compute_type = "float16" if use_gpu else "int8"
    try:
        print(f"[*] Loading whisper model '{model_size}' on {device} ({compute_type})...")
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
    except Exception as e:
        if use_gpu:
            print(f"[!] Warning: CUDA initialization failed ({e}). Falling back to CPU...")
            try:
                model = WhisperModel(model_size, device="cpu", compute_type="int8")
            except Exception as e2:
                raise RuntimeError(f"Error al inicializar el modelo Whisper '{model_size}' local en CPU: {e2}.") from e2
        else:
            raise RuntimeError(f"Error al inicializar el modelo Whisper '{model_size}' local: {e}. Revisa si tu equipo tiene suficiente memoria RAM.") from e

    print(f"[*] Transcribing {audio_path}...")
    try:
        segments, info = model.transcribe(
            audio_path,
            language=language,
            word_timestamps=True
        )
        transcription_data = []
        for segment in segments:
            segment_words = []
            if segment.words:
                for word in segment.words:
                    segment_words.append({
                        "word": word.word,
                        "start": word.start,
                        "end": word.end,
                        "probability": word.probability
                    })

            transcription_data.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
                "words": segment_words
            })
    except Exception as e:
        if device == "cuda":
            print(f"[!] Warning: Error during CUDA transcription ({e}). Falling back to CPU...")
            try:
                model = WhisperModel(model_size, device="cpu", compute_type="int8")
                segments, info = model.transcribe(
                    audio_path,
                    language=language,
                    word_timestamps=True
                )
                transcription_data = []
                for segment in segments:
                    segment_words = []
                    if segment.words:
                        for word in segment.words:
                            segment_words.append({
                                "word": word.word,
                                "start": word.start,
                                "end": word.end,
                                "probability": word.probability
                            })

                    transcription_data.append({
                        "start": segment.start,
                        "end": segment.end,
                        "text": segment.text.strip(),
                        "words": segment_words
                    })
            except Exception as e2:
                raise RuntimeError(f"Error crítico en fallback a CPU durante transcripción: {e2}") from e2
        else:
            raise RuntimeError(f"Error crítico durante el proceso de transcripción local: {e}") from e

    return transcription_data


def transcribe_audio_cloud(audio_path, api_key, provider="groq", api_url=None, language="es"):
    """Transcribes audio using Groq or OpenAI's cloud Whisper API (extremely fast, low resources)."""
    import requests
    print(f"[*] Transcribing in the cloud using {provider} API...")
    
    if provider == "openai":
        url = api_url or "https://api.openai.com/v1/audio/transcriptions"
        model = "whisper-1"
    else:       
        url = api_url or "https://api.groq.com/openai/v1/audio/transcriptions"
        model = "whisper-large-v3"
        
    headers = {"Authorization": f"Bearer {api_key}"}
    
    max_upload_mb = 24
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    upload_path = audio_path
    temp_mp3 = None

    if file_size_mb > max_upload_mb:
        print(f"[*] Audio file size ({file_size_mb:.2f} MB) exceeds {max_upload_mb} MB. Compressing to MP3...")
        temp_mp3 = os.path.join(tempfile.gettempdir(), f"temp_compressed_{uuid.uuid4().hex}.mp3")
        for bitrate in ["32k", "16k", "8k"]:
            compress_audio_for_transcription(audio_path, temp_mp3, bitrate=bitrate)
            file_size_mb = os.path.getsize(temp_mp3) / (1024 * 1024)
            print(f"[*] Compressed audio size with {bitrate}: {file_size_mb:.2f} MB")
            if file_size_mb <= max_upload_mb:
                break

        if file_size_mb > max_upload_mb:
            raise RuntimeError(
                f"El audio comprimido sigue siendo demasiado grande ({file_size_mb:.2f} MB) para el endpoint de transcripción en la nube. "
                "Usa transcripción local o reduce la duración del video."
            )

        upload_path = temp_mp3

    try:
        with open(upload_path, "rb") as f:
            files = {"file": (os.path.basename(upload_path), f, "audio/mp3" if temp_mp3 else "audio/wav")}
            data = {
                "model": model,
                "response_format": "verbose_json",
                "language": language,
            }
            # timestamp_granularities is an OpenAI-specific param;
            # Groq silently ignores or rejects it — don't send it to Groq.
            if provider == "openai":
                data["timestamp_granularities[]"] = ["word", "segment"]
            response = requests.post(url, headers=headers, files=files, data=data)
            response.raise_for_status()
            res_json = response.json()
            print(f"[*] Cloud Transcription response keys: {list(res_json.keys())}")
            print(f"[*] Cloud Transcription text snippet: '{res_json.get('text', '')[:100]}...'")
            if "error" in res_json:
                print(f"[!] Cloud Transcription API error: {res_json['error']}")

            
        transcription_data = []
        # OpenAI returns words at top-level; Groq returns them inside each segment.
        top_level_words = res_json.get("words") or []

        for segment in (res_json.get("segments") or []):
            segment_start = segment["start"]
            segment_end   = segment["end"]
            segment_words = []

            # Try segment-level words first (Groq format), fall back to top-level (OpenAI)
            raw_words = segment.get("words") or []
            if not raw_words:
                # OpenAI top-level words: filter by segment time range
                raw_words = [
                    w for w in top_level_words
                    if w["start"] >= segment_start and w["end"] <= segment_end + 0.1
                ]

            for w in raw_words:
                segment_words.append({
                    "word":        w.get("word", w.get("text", "")),
                    "start":       w["start"],
                    "end":         w["end"],
                    "probability": w.get("probability", 1.0),
                })

            transcription_data.append({
                "start": segment_start,
                "end":   segment_end,
                "text":  segment["text"].strip(),
                "words": segment_words,
            })

        if not transcription_data:
            raise RuntimeError(
                "La transcripci\u00f3n en la nube no devolvi\u00f3 segmentos con timestamps. "
                "Verifica que el audio tenga voz clara o usa transcripci\u00f3n local con Whisper."
            )
        return transcription_data

    finally:
        if temp_mp3 and os.path.exists(temp_mp3):
            os.remove(temp_mp3)



if __name__ == "__main__":
    import sys
    import json
    if len(sys.argv) < 2:
        print("Usage: python transcriber.py <video_or_audio_path>")
        sys.exit(1)
        
    path = sys.argv[1]
    temp_audio = "temp_audio.wav"
    
                                          
    if not path.endswith(".wav"):
        audio_path = extract_audio(path, temp_audio)
    else:
        audio_path = path
        
    try:
        data = transcribe_audio(audio_path)
        print(json.dumps(data, indent=2, ensure_ascii=False))
    finally:
        if os.path.exists(temp_audio) and not path.endswith(".wav"):
            os.remove(temp_audio)
