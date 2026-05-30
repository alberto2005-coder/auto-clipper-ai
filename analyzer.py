import json
import requests
import librosa
import numpy as np

def analyze_audio_energy(audio_path, segment_duration=1.0):
    """Analyzes the audio RMS energy to find high-intensity moments."""
    print(f"[*] Analyzing audio energy for {audio_path} using librosa...")
    try:
        y, sr = librosa.load(audio_path, sr=16000)
        # Calculate RMS energy
        hop_length = int(sr * segment_duration)
        rms = librosa.feature.rms(y=y, frame_length=hop_length, hop_length=hop_length)[0]
        times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)
        return list(zip(times, rms))
    except Exception as e:
        print(f"[!] Warning: Librosa analysis failed ({e}). Proceeding without audio energy analysis.")
        return []

def select_best_moments_with_llm(transcription_data, provider="ollama", api_url="http://localhost:11434/api/generate", api_key=None, model="llama3.2:3b"):
    """Uses Ollama or OpenAI-compatible API to identify highly engaging moments/hooks."""
    if not transcription_data:
        print("[*] No speech found in video (empty transcription). Creating a default 10-second clip.")
        return [{"start": 0.0, "end": 10.0, "hook_title": "Clip de Muestra (Sin voz)", "explanation": "Mute video fallback"}]
        
    print(f"[*] Analyzing transcription for key moments using LLM ({provider} - {model})...")

    
    # Simplify transcript into a readable context with timestamps
    simplified_transcript = []
    for seg in transcription_data:
        simplified_transcript.append(f"[{seg['start']:.2f}s - {seg['end']:.2f}s]: {seg['text']}")
    
    context_text = "\n".join(simplified_transcript)
    print(f"[*] Simplified transcript sent to LLM (first 500 chars):\n{context_text[:500]}...")
    
    prompt = f"""

Eres un editor de video experto en YouTube Shorts, TikTok y Reels. Tu objetivo es encontrar los momentos más virales, entretenidos, informativos o con un gancho (hook) muy fuerte en este video largo.

Analiza la siguiente transcripción con marcas de tiempo y selecciona entre 1 y 3 segmentos idóneos para convertirlos en videos cortos.

REGLAS OBLIGATORIAS DE DURACIÓN (MUY IMPORTANTE):
- La duración de cada clip DEBE ser de al menos 20 segundos y máximo 60 segundos (la diferencia "end" menos "start" tiene que ser como mínimo de 20.0 segundos).
- Está ESTRICTAMENTE PROHIBIDO seleccionar fragmentos de menos de 20 segundos. No devuelvas clips de 5, 8 o 15 segundos.


IMPORTANTE PARA LOS TÍTULOS Y DESCRIPCIONES:
- Los títulos deben sonar 100% naturales, como escritos por un creador de contenido humano experto.
- EVITA palabras clichés de IA como: "revolucionario", "el secreto de", "increíble", "descubre cómo", "impactante", etc.
- Usa intriga, preguntas directas o afirmaciones contundentes. Ejemplo malo de IA: "El Secreto Para Ser Millonario". Ejemplo bueno humano: "Por esto no eres millonario a los 20".
- Proporciona también una breve descripción para redes sociales que actúe como copy de enganche.

Transcripción:
{context_text}

Responde ÚNICAMENTE con un JSON válido de la siguiente estructura (no agregues explicaciones fuera del JSON):
[
  {{
    "start": float,
    "end": float,
    "hook_title": "Título humano y viral",
    "social_description": "Copywriting para la descripción del video",
    "explanation": "Por qué este momento es viral"
  }}
]
"""



    if provider == "ollama":
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        try:
            response = requests.post(api_url, json=payload, timeout=60)
            response.raise_for_status()
            res_json = response.json()
            response_text = res_json.get("response", "")
        except Exception as e:
            print(f"[!] Ollama connection error: {e}. Falling back to default segment (first 40 seconds).")
            return [{"start": 0.0, "end": 40.0, "hook_title": "Clip de Muestra", "explanation": "Fallback"}]
    else:
        # OpenAI or compatible API
        headers = {
            "Authorization": f"Bearer {api_key or ''}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Eres un editor de video experto que devuelve solo JSON."},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"}
        }
        try:
            response = requests.post(api_url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            res_json = response.json()
            response_text = res_json["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[!] API connection error: {e}. Falling back to default segment (first 40 seconds).")
            return [{"start": 0.0, "end": 40.0, "hook_title": "Clip de Muestra", "explanation": "Fallback"}]

    try:
        # Parse the JSON response
        print(f"[*] Raw LLM Response:\n{response_text}")
        data = json.loads(response_text)
        
        # If the LLM returned a dict containing a 'clips' key
        if isinstance(data, dict) and "clips" in data:
            data = data["clips"]
            
        # If the LLM returned a dict with nested clip dicts (e.g. {"clip1": {...}, "clip2": {...}})
        if isinstance(data, dict):
            nested_clips = [v for v in data.values() if isinstance(v, dict) and any(k in v for k in ["start", "end", "start_time", "end_time", "inicio", "fin"])]
            if nested_clips:
                data = nested_clips
                
        # If the LLM returned a single clip dict instead of a list
        if isinstance(data, dict):
            if any(k in data for k in ["start", "end", "start_time", "end_time", "inicio", "fin"]):
                data = [data]
            else:
                # If it's a dict but doesn't have start/end, look for any list inside
                for val in data.values():
                    if isinstance(val, list):
                        data = val
                        break

                        
        if not isinstance(data, list):
            data = [data]
            
        # Robust key normalization
        normalized_data = []
        for item in data:
            if not isinstance(item, dict):
                continue
            
            normalized_item = {}
            
            # Map start time
            for start_key in ["start", "start_time", "startTime", "inicio"]:
                if start_key in item:
                    try:
                        normalized_item["start"] = float(item[start_key])
                        break
                    except (ValueError, TypeError):
                        pass
            if "start" not in normalized_item:
                normalized_item["start"] = 0.0
                
            # Map end time
            for end_key in ["end", "end_time", "endTime", "fin"]:
                if end_key in item:
                    try:
                        normalized_item["end"] = float(item[end_key])
                        break
                    except (ValueError, TypeError):
                        pass
            if "end" not in normalized_item:
                normalized_item["end"] = 10.0
                
            # Map title
            for title_key in ["hook_title", "title", "titulo", "título", "hookTitle"]:
                if title_key in item:
                    normalized_item["hook_title"] = str(item[title_key])
                    break
            if "hook_title" not in normalized_item:
                normalized_item["hook_title"] = "Clip Viral"
                
            # Map description
            for desc_key in ["social_description", "socialDescription", "description", "descripcion", "descripción", "copy", "caption"]:
                if desc_key in item:
                    normalized_item["social_description"] = str(item[desc_key])
                    break
            if "social_description" not in normalized_item:
                normalized_item["social_description"] = item.get("explanation", "Mira este increíble momento.")
            # Programmatic Duration Expander:
            # If the clip selected by the LLM is shorter than 30 seconds, expand it symmetrically
            # to provide context and avoid cutting off the speaker's sentence.
            MIN_DURATION = 30.0
            clip_duration = normalized_item["end"] - normalized_item["start"]
            if clip_duration < MIN_DURATION:
                diff = MIN_DURATION - clip_duration
                # Expand backward and forward
                new_start = max(0.0, normalized_item["start"] - (diff / 2))
                new_end = normalized_item["end"] + (diff / 2)
                normalized_item["start"] = round(new_start, 2)
                normalized_item["end"] = round(new_end, 2)
                
            normalized_data.append(normalized_item)

            
        return normalized_data

    except Exception as e:
        print(f"[!] Error parsing LLM response as JSON: {e}")
        # Let's try to extract JSON array using regex or simple search
        try:
            start_idx = response_text.find("[")
            end_idx = response_text.rfind("]") + 1
            if start_idx != -1 and end_idx != -1:
                # We could attempt to parse the substring, but returning a safe fallback is cleaner
                pass
        except:
            pass
        return [{"start": 0.0, "end": 10.0, "hook_title": "Clip de Muestra", "social_description": "Fallback", "explanation": "Failed to parse JSON response"}]


if __name__ == "__main__":
    # Test stub
    dummy_transcript = [
        {"start": 0.0, "end": 5.0, "text": "Hola a todos, hoy vamos a hablar de cómo el éxito no ocurre de la noche a la mañana."},
        {"start": 5.0, "end": 15.0, "text": "Mucha gente piensa que los millonarios tuvieron suerte, pero la verdad es otra."},
        {"start": 15.0, "end": 35.0, "text": "Trabajaron 16 horas diarias durante 5 años seguidos. Eso no es suerte, es pura disciplina y constancia absoluta!"},
        {"start": 35.0, "end": 45.0, "text": "Así es como se logra el éxito real. Sígueme para más consejos motivacionales."}
    ]
    print(select_best_moments_with_llm(dummy_transcript))
