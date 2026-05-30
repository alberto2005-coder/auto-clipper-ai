import os
import subprocess
from faster_whisper import WhisperModel

def get_ffmpeg_path():
    """Resolves path to FFmpeg: local, imageio-ffmpeg package, or system PATH."""
    local_paths = ["ffmpeg.exe", "bin/ffmpeg.exe", "./ffmpeg", "./bin/ffmpeg"]
    for path in local_paths:
        if os.path.exists(path):
            return os.path.abspath(path)
    try:
        import imageio_ffmpeg
        path = imageio_ffmpeg.get_ffmpeg_exe()
        if path:
            return path
    except ImportError:
        pass
    return "ffmpeg"

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

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        # Check if the failure is due to the video having no audio stream
        if "does not contain any stream" in result.stderr or "Output file does not contain any stream" in result.stderr:
            print("[*] No audio stream detected in video. Generating a silent audio track...")
            import re
            duration = 10.0  # default fallback duration
            match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", result.stderr)
            if match:
                hours, minutes, seconds = match.groups()
                duration = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
            
            # Generate silent WAV of the exact duration
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



def transcribe_audio(audio_path, model_size="small", language="es"):
    """Transcribes audio using faster-whisper on CPU with int8 quantization."""
    print(f"[*] Loading whisper model '{model_size}' on CPU (int8)...")
    # compute_type="int8" is lightweight and optimized for CPU
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    
    print(f"[*] Transcribing {audio_path}...")
    segments, info = model.transcribe(
        audio_path,
        language=language,
        word_timestamps=True
    )
    
    transcription_data = []
    
    # Iterate through segments and build structure
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
        
    return transcription_data

def transcribe_audio_cloud(audio_path, api_key, provider="groq", api_url=None, language="es"):
    """Transcribes audio using Groq or OpenAI's cloud Whisper API (extremely fast, low resources)."""
    import requests
    print(f"[*] Transcribing in the cloud using {provider} API...")
    
    if provider == "openai":
        url = api_url or "https://api.openai.com/v1/audio/transcriptions"
        model = "whisper-1"
    else: # groq
        url = api_url or "https://api.groq.com/openai/v1/audio/transcriptions"
        model = "whisper-large-v3"
        
    headers = {"Authorization": f"Bearer {api_key}"}
    
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    upload_path = audio_path
    temp_mp3 = None
    
    if file_size_mb > 24:
        print(f"[*] Audio file size ({file_size_mb:.2f}MB) exceeds 24MB. Compressing to MP3...")
        temp_mp3 = "temp_compressed.mp3"
        ffmpeg_bin = get_ffmpeg_path()
        cmd = [
            ffmpeg_bin, "-y",
            "-i", audio_path,
            "-codec:a", "libmp3lame",
            "-b:a", "64k",
            temp_mp3
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        upload_path = temp_mp3
        
    try:
        with open(upload_path, "rb") as f:
            files = {"file": (os.path.basename(upload_path), f, "audio/mp3" if temp_mp3 else "audio/wav")}
            data = {
                "model": model,
                "response_format": "verbose_json",
                "language": language,
                "timestamp_granularities[]": ["word", "segment"]
            }
            response = requests.post(url, headers=headers, files=files, data=data)
            response.raise_for_status()
            res_json = response.json()
            print(f"[*] Cloud Transcription response keys: {list(res_json.keys())}")
            print(f"[*] Cloud Transcription text snippet: '{res_json.get('text', '')[:100]}...'")
            if "error" in res_json:
                print(f"[!] Cloud Transcription API error: {res_json['error']}")

            
        transcription_data = []
        all_words = res_json.get("words") or []
        
        for segment in (res_json.get("segments") or []):
            segment_start = segment["start"]
            segment_end = segment["end"]
            segment_words = []
            
            # Group top-level words into this segment by timestamp
            for w in all_words:
                if w["start"] >= segment_start and w["end"] <= segment_end + 0.1:
                    segment_words.append({
                        "word": w["word"],
                        "start": w["start"],
                        "end": w["end"],
                        "probability": w.get("probability", 1.0)
                    })
                    
            transcription_data.append({
                "start": segment_start,
                "end": segment_end,
                "text": segment["text"].strip(),
                "words": segment_words
            })
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
    
    # If it's a video, extract audio first
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
