import json
import requests
import librosa
import numpy as np

def analyze_audio_energy(audio_path, segment_duration=1.0):
    """Analyzes the audio RMS energy to find high-intensity moments."""
    print(f"[*] Analyzing audio energy for {audio_path} using librosa...")
    try:
        y, sr = librosa.load(audio_path, sr=16000)
                              
        hop_length = int(sr * segment_duration)
        rms = librosa.feature.rms(y=y, frame_length=hop_length, hop_length=hop_length)[0]
        times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)
        return list(zip(times, rms))
    except Exception as e:
        print(f"[!] Warning: Librosa analysis failed ({e}). Proceeding without audio energy analysis.")
        return []

def select_best_moments_with_llm(transcription_data, provider="ollama", api_url="http://localhost:11434/api/generate", api_key=None, model="llama3.2:3b", max_clips=3, min_clips=1, clip_type="virales, entretenidos, informativos o con un gancho (hook) muy fuerte", bypass_chunking=False):
    """Uses Ollama or OpenAI-compatible API to identify highly engaging moments/hooks."""
    if not transcription_data:
        print("[*] No speech found in video (empty transcription). Creating a default 10-second clip.")
        return [{"start": 0.0, "end": 10.0, "hook_title": "Clip de Muestra (Sin voz)", "explanation": "Mute video fallback"}]

    # Chunking logic for long videos
    if not bypass_chunking:
        total_duration = max(seg.get("end", 0.0) for seg in transcription_data)
        CHUNK_SIZE = 900.0  # 15 minutes
        if total_duration > CHUNK_SIZE:
            print(f"[*] Video duration ({total_duration:.1f}s) is long. Splitting into {CHUNK_SIZE}s chunks...")
            num_chunks = int(np.ceil(total_duration / CHUNK_SIZE))
            all_clips = []
            
            chunk_max_clips = max(1, int(np.ceil(max_clips / num_chunks)))
            chunk_min_clips = max(1, int(np.ceil(min_clips / num_chunks)))
            
            for i in range(num_chunks):
                chunk_start = i * CHUNK_SIZE
                chunk_end = (i + 1) * CHUNK_SIZE
                
                chunk_transcription = []
                for seg in transcription_data:
                    seg_start = seg.get("start", 0.0)
                    seg_end = seg.get("end", seg_start)
                    if seg_start < chunk_end and seg_end >= chunk_start:
                        chunk_transcription.append(seg)
                
                if not chunk_transcription:
                    continue
                    
                if i > 0:
                    import time
                    print("[*] Waiting 3 seconds before next chunk to avoid API rate limits...")
                    time.sleep(3.0)

                print(f"[*] Analyzing chunk {i+1}/{num_chunks} ({chunk_start:.1f}s - {chunk_end:.1f}s)...")
                chunk_clips = select_best_moments_with_llm(
                    chunk_transcription,
                    provider=provider,
                    api_url=api_url,
                    api_key=api_key,
                    model=model,
                    max_clips=chunk_max_clips,
                    min_clips=chunk_min_clips,
                    clip_type=clip_type,
                    bypass_chunking=True
                )
                
                filtered_chunk_clips = [c for c in chunk_clips if not ("Clip de Muestra" in c.get("hook_title", "") or c.get("explanation") == "Fallback")]
                if filtered_chunk_clips:
                    all_clips.extend(filtered_chunk_clips)
                else:
                    all_clips.extend(chunk_clips)
            
            # Discard fallback/default clips if we found at least one real clip in any chunk
            real_clips = [c for c in all_clips if not ("Clip de Muestra" in c.get("hook_title", "") or c.get("explanation") == "Fallback")]
            if real_clips:
                all_clips = real_clips

            all_clips = sorted(all_clips, key=lambda x: x.get("start", 0.0))
            if len(all_clips) > max_clips:
                all_clips = all_clips[:max_clips]
            return all_clips
        
    print(f"[*] Analyzing transcription for key moments using LLM ({provider} - {model})...")

    
                                                                 
    # Agrupar segmentos consecutivos para ahorrar tokens de marcas de tiempo
    compressed_transcript = []
    current_start = None
    current_end = None
    current_texts = []
    TARGET_DURATION = 15.0  # Segundos aproximados por bloque

    for seg in transcription_data:
        start = seg.get("start", 0.0)
        end = seg.get("end", start)
        text = seg.get("text", "").strip()
        if not text:
            continue
        if current_start is None:
            current_start = start
            current_end = end
            current_texts.append(text)
        elif start - current_start < TARGET_DURATION:
            current_end = end
            current_texts.append(text)
        else:
            compressed_transcript.append(f"[{current_start:.1f}s-{current_end:.1f}s]: {' '.join(current_texts)}")
            current_start = start
            current_end = end
            current_texts = [text]
    if current_start is not None:
        compressed_transcript.append(f"[{current_start:.1f}s-{current_end:.1f}s]: {' '.join(current_texts)}")

    context_text = "\n".join(compressed_transcript)
    print(f"[*] Compressed transcript sent to LLM (first 500 chars):\n{context_text[:500]}...")
    
    prompt = f"""

Eres un editor de video experto en YouTube Shorts, TikTok y Reels. Tu objetivo es encontrar momentos que sean del tipo: {clip_type} en este video largo.

Analiza la siguiente transcripción con marcas de tiempo y selecciona la mayor cantidad posible de segmentos idóneos (idealmente hasta {max_clips} si el video es lo suficientemente largo e interesante) para convertirlos en videos cortos. Si el video es largo (por ejemplo, de 1 hora), es sumamente importante que busques y devuelvas entre 10 y 20 clips (o el máximo de {max_clips} especificado) para no dejar pasar ningún momento de valor.

REGLAS OBLIGATORIAS DE DURACIÓN (MUY IMPORTANTE):
- La duración de cada clip DEBE ser de al menos 15 segundos y máximo 60 segundos (la diferencia "end" menos "start" tiene que ser como mínimo de 15.0 segundos).
- Está ESTRICTAMENTE PROHIBIDO seleccionar fragmentos de menos de 15 segundos. No devuelvas clips de 5 u 8 segundos.


IMPORTANTE PARA LOS TÍTULOS Y DESCRIPCIONES:
- Los títulos deben sonar 100% naturales, como escritos por un creador de contenido humano experto.
- EVITA palabras clichés de IA como: "revolucionario", "el secreto de", "increíble", "descubre cómo", "impactante", etc.
- Usa intriga, preguntas directas o afirmaciones contundentes. Ejemplo malo de IA: "El Secreto Para Ser Millonario". Ejemplo bueno humano: "Por esto no eres millonario a los 20".
- Proporciona también una breve descripción para redes sociales que actúe como copy de enganche.

EVALUACIÓN DE VIRALIDAD (ESTILO OPUS CLIP):
- Para cada clip, evalúa su potencial de viralidad y asígnale un "virality_score" (entero del 0 al 100).
- Proporciona una explicación concisa llamada "virality_explanation" detallando por qué tiene esa puntuación (ej: "Hook muy fuerte en los primeros 3 segundos, mantiene el ritmo dinámico y trata un tema controversial de interés general").

Transcripción:
{context_text}

Responde ÚNICAMENTE con un JSON válido de la siguiente estructura (no agregues explicaciones fuera del JSON):
[
  {{
    "start": float,
    "end": float,
    "hook_title": "Título humano y viral",
    "social_description": "Copywriting para la descripción del video",
    "virality_score": int,
    "virality_explanation": "Explicación detallada de por qué enganchará a la audiencia",
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
        def do_request(payload_to_send):
            resp = requests.post(api_url, json=payload_to_send, headers=headers, timeout=60)
            resp.raise_for_status()
            return resp.json()

        try:
            res_json = do_request(payload)
            response_text = res_json["choices"][0]["message"]["content"]
        except Exception as e:
            # Si la carga es demasiado grande, intentar reintentar con un contexto truncado
            print(f"[!] API connection error: {e}. Attempting retry with truncated context...")
            try:
                truncated_context = context_text[:3000]
                truncated_prompt = """

Eres un editor de video experto en YouTube Shorts, TikTok y Reels. Tu objetivo es encontrar momentos que sean del tipo: {clip_type} en este video largo.

Analiza la siguiente transcripción con marcas de tiempo y selecciona la mayor cantidad posible de segmentos idóneos (idealmente hasta {max_clips} si el video es lo suficientemente largo e interesante) para convertirlos en videos cortos. Si el video es largo, es sumamente importante que busques y devuelvas entre 10 y 20 clips (o el máximo de {max_clips} especificado) para no dejar pasar ningún momento de valor.

REGLAS OBLIGATORIAS DE DURACIÓN (MUY IMPORTANTE):
- La duración de cada clip DEBE ser de al menos 15 segundos y máximo 60 segundos (la diferencia "end" menos "start" tiene que ser como mínimo de 15.0 segundos).
- Está ESTRICTAMENTE PROHIBIDO seleccionar fragmentos de menos de 15 segundos. No devuelvas clips de 5 o 10 segundos.


IMPORTANTE PARA LOS TÍTULOS Y DESCRIPCIONES:
- Los títulos deben sonar 100% naturales, como escritos por un creador de contenido humano experto.
- EVITA palabras clichés de IA como: "revolucionario", "el secreto de", "increíble", "descubre cómo", "impactante", etc.
- Usa intriga, preguntas directas o afirmaciones contundentes. Ejemplo malo de IA: "El Secreto Para Ser Millonario". Ejemplo bueno humano: "Por esto no eres millonario a los 20".
- Proporciona también una breve descripción para redes sociales que actúe como copy de enganche.

EVALUACIÓN DE VIRALIDAD (ESTILO OPUS CLIP):
- Para cada clip, evalúa su potencial de viralidad y asígnale un "virality_score" (entero del 0 al 100).
- Proporciona una explicación concisa llamada "virality_explanation" detallando por qué tiene esa puntuación (ej: "Hook muy fuerte en los primeros 3 segundos, mantiene el ritmo dinámico y trata un tema controversial de interés general").

Transcripción:
{truncated}

Responde ÚNICAMENTE con un JSON válido de la siguiente estructura (no agregues explicaciones fuera del JSON):
[
  {{
    "start": float,
    "end": float,
    "hook_title": "Título humano y viral",
    "social_description": "Copywriting para la descripción del video",
    "virality_score": int,
    "virality_explanation": "Explicación detallada de por qué enganchará a la audiencia",
    "explanation": "Por qué este momento es viral"
  }}
]
""".format(truncated=truncated_context, max_clips=max_clips, clip_type=clip_type)

                payload_trunc = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "Eres un editor de video experto que devuelve solo JSON."},
                        {"role": "user", "content": truncated_prompt}
                    ],
                    "response_format": {"type": "json_object"}
                }
                res_json = do_request(payload_trunc)
                response_text = res_json["choices"][0]["message"]["content"]
            except Exception as e2:
                print(f"[!] Retry with truncated context failed: {e2}. Falling back to default segment (first 40 seconds).")
                return [{"start": 0.0, "end": 40.0, "hook_title": "Clip de Muestra", "explanation": "Fallback"}]

    try:
                                 
        print(f"[*] Raw LLM Response:\n{response_text}")
        data = json.loads(response_text)
        
                                                             
        if isinstance(data, dict) and "clips" in data:
            data = data["clips"]
            
                                                                                                   
        if isinstance(data, dict):
            nested_clips = [v for v in data.values() if isinstance(v, dict) and any(k in v for k in ["start", "end", "start_time", "end_time", "inicio", "fin"])]
            if nested_clips:
                data = nested_clips
                
                                                                  
        if isinstance(data, dict):
            if any(k in data for k in ["start", "end", "start_time", "end_time", "inicio", "fin"]):
                data = [data]
            else:
                                                                                     
                for val in data.values():
                    if isinstance(val, list):
                        data = val
                        break

                        
        if not isinstance(data, list):
            data = [data]
            
                                  
        normalized_data = []
        for item in data:
            if not isinstance(item, dict):
                continue
            
            normalized_item = {}
            
                            
            for start_key in ["start", "start_time", "startTime", "inicio"]:
                if start_key in item:
                    try:
                        normalized_item["start"] = float(item[start_key])
                        break
                    except (ValueError, TypeError):
                        pass
            if "start" not in normalized_item:
                normalized_item["start"] = 0.0
                
                          
            for end_key in ["end", "end_time", "endTime", "fin"]:
                if end_key in item:
                    try:
                        normalized_item["end"] = float(item[end_key])
                        break
                    except (ValueError, TypeError):
                        pass
            if "end" not in normalized_item:
                normalized_item["end"] = 10.0
                
                       
            for title_key in ["hook_title", "title", "titulo", "título", "hookTitle"]:
                if title_key in item:
                    normalized_item["hook_title"] = str(item[title_key])
                    break
            if "hook_title" not in normalized_item:
                normalized_item["hook_title"] = "Clip Viral"
                
                             
            for desc_key in ["social_description", "socialDescription", "description", "descripcion", "descripción", "copy", "caption"]:
                if desc_key in item:
                    normalized_item["social_description"] = str(item[desc_key])
                    break
            if "social_description" not in normalized_item:
                normalized_item["social_description"] = item.get("explanation", "Mira este increíble momento.")

            # Virality score mapping
            for score_key in ["virality_score", "viralityScore", "score", "puntuacion"]:
                if score_key in item:
                    try:
                        normalized_item["virality_score"] = int(item[score_key])
                        break
                    except (ValueError, TypeError):
                        pass
            if "virality_score" not in normalized_item:
                normalized_item["virality_score"] = 85

            # Virality explanation mapping
            for vex_key in ["virality_explanation", "viralityExplanation", "reason"]:
                if vex_key in item:
                    normalized_item["virality_explanation"] = str(item[vex_key])
                    break
            if "virality_explanation" not in normalized_item:
                normalized_item["virality_explanation"] = item.get("explanation", "Estructura narrativa sólida y gancho inicial de impacto.")
                                             
                                                                                                 
                                                                              
            MIN_DURATION = 15.0
            clip_duration = normalized_item["end"] - normalized_item["start"]
            if clip_duration < MIN_DURATION:
                diff = MIN_DURATION - clip_duration
                                             
                new_start = max(0.0, normalized_item["start"] - (diff / 2))
                new_end = normalized_item["end"] + (diff / 2)
                normalized_item["start"] = round(new_start, 2)
                normalized_item["end"] = round(new_end, 2)
                
            normalized_data.append(normalized_item)

            
        return normalized_data

    except Exception as e:
        print(f"[!] Error parsing LLM response as JSON: {e}")
                                                                      
        try:
            start_idx = response_text.find("[")
            end_idx = response_text.rfind("]") + 1
            if start_idx != -1 and end_idx != -1:
                                                                                                   
                pass
        except:
            pass
        return [{"start": 0.0, "end": 10.0, "hook_title": "Clip de Muestra", "social_description": "Fallback", "explanation": "Failed to parse JSON response"}]


if __name__ == "__main__":
               
    dummy_transcript = [
        {"start": 0.0, "end": 5.0, "text": "Hola a todos, hoy vamos a hablar de cómo el éxito no ocurre de la noche a la mañana."},
        {"start": 5.0, "end": 15.0, "text": "Mucha gente piensa que los millonarios tuvieron suerte, pero la verdad es otra."},
        {"start": 15.0, "end": 35.0, "text": "Trabajaron 16 horas diarias durante 5 años seguidos. Eso no es suerte, es pura disciplina y constancia absoluta!"},
        {"start": 35.0, "end": 45.0, "text": "Así es como se logra el éxito real. Sígueme para más consejos motivacionales."}
    ]
    print(select_best_moments_with_llm(dummy_transcript))
