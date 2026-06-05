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


def _deduplicate_clips(clips, min_gap=20.0):
    """
    Removes clips that overlap or start too close to each other.
    Keeps the one with the highest virality_score when two clips conflict.
    Returns clips sorted chronologically.
    """
    if not clips:
        return clips

    # Sort by virality_score descending so better clips survive dedup
    sorted_by_score = sorted(clips, key=lambda x: x.get("virality_score", 0), reverse=True)

    kept = []
    for candidate in sorted_by_score:
        c_start = candidate.get("start", 0.0)
        c_end   = candidate.get("end", 0.0)
        conflict = False
        for k in kept:
            k_start = k.get("start", 0.0)
            k_end   = k.get("end", 0.0)
            # Overlap or starts within min_gap of an already-kept clip
            if not (c_end <= k_start + min_gap or c_start >= k_end - min_gap):
                conflict = True
                break
        if not conflict:
            kept.append(candidate)

    # Reorder chronologically
    kept.sort(key=lambda x: x.get("start", 0.0))
    return kept


def select_best_moments_with_llm(
    transcription_data,
    provider="ollama",
    api_url="http://localhost:11434/api/generate",
    api_key=None,
    model="llama3.2:3b",
    max_clips=3,
    min_clips=1,
    clip_type="virales, entretenidos, informativos o con un gancho (hook) muy fuerte",
    bypass_chunking=False,
):
    """Uses Ollama or OpenAI-compatible API to identify highly engaging moments/hooks."""
    if not transcription_data:
        print("[*] No speech found in video (empty transcription). Creating a default 30-second clip.")
        return [{"start": 0.0, "end": 30.0, "hook_title": "Clip de Muestra (Sin voz)", "explanation": "Mute video fallback"}]

    # ── Chunking logic for long videos ────────────────────────────────────────
    if not bypass_chunking:
        total_duration = max(seg.get("end", 0.0) for seg in transcription_data)
        CHUNK_SIZE = 900.0  # 15 minutes per chunk

        if total_duration > CHUNK_SIZE:
            print(f"[*] Video duration ({total_duration:.1f}s) is long. Splitting into {CHUNK_SIZE}s chunks...")
            num_chunks = int(np.ceil(total_duration / CHUNK_SIZE))
            all_clips = []

            # Distribute clips more generously across chunks so none is starved
            chunk_max_clips = max(2, int(np.ceil(max_clips / num_chunks)) + 1)
            chunk_min_clips = max(1, int(np.ceil(min_clips / num_chunks)))

            for i in range(num_chunks):
                chunk_start = i * CHUNK_SIZE
                chunk_end   = (i + 1) * CHUNK_SIZE

                chunk_transcription = [
                    seg for seg in transcription_data
                    if seg.get("start", 0.0) < chunk_end and seg.get("end", seg.get("start", 0.0)) >= chunk_start
                ]

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
                    bypass_chunking=True,
                )

                real_chunk_clips = [
                    c for c in chunk_clips
                    if not ("Clip de Muestra" in c.get("hook_title", "") or c.get("explanation") == "Fallback")
                ]
                all_clips.extend(real_chunk_clips if real_chunk_clips else chunk_clips)

            # Keep only real clips if we have any
            real_clips = [
                c for c in all_clips
                if not ("Clip de Muestra" in c.get("hook_title", "") or c.get("explanation") == "Fallback")
            ]
            if real_clips:
                all_clips = real_clips

            # Deduplicate overlapping clips, then limit to max_clips
            all_clips = _deduplicate_clips(all_clips, min_gap=20.0)
            if len(all_clips) > max_clips:
                # Keep the highest-scored ones up to max_clips, then re-sort chronologically
                top_clips = sorted(all_clips, key=lambda x: x.get("virality_score", 0), reverse=True)[:max_clips]
                all_clips = sorted(top_clips, key=lambda x: x.get("start", 0.0))

            return all_clips

    print(f"[*] Analyzing transcription for key moments using LLM ({provider} - {model})...")

    # ── Compress transcript into 15-second blocks ─────────────────────────────
    compressed_transcript = []
    current_start = None
    current_end   = None
    current_texts = []
    TARGET_DURATION = 15.0

    for seg in transcription_data:
        start = seg.get("start", 0.0)
        end   = seg.get("end", start)
        text  = seg.get("text", "").strip()
        if not text:
            continue
        if current_start is None:
            current_start = start
            current_end   = end
            current_texts.append(text)
        elif start - current_start < TARGET_DURATION:
            current_end = end
            current_texts.append(text)
        else:
            compressed_transcript.append(
                f"[{current_start:.1f}s-{current_end:.1f}s]: {' '.join(current_texts)}"
            )
            current_start = start
            current_end   = end
            current_texts = [text]
    if current_start is not None:
        compressed_transcript.append(
            f"[{current_start:.1f}s-{current_end:.1f}s]: {' '.join(current_texts)}"
        )

    context_text = "\n".join(compressed_transcript)
    print(f"[*] Compressed transcript sent to LLM (first 500 chars):\n{context_text[:500]}...")

    prompt = f"""
Eres un editor de video experto en YouTube Shorts, TikTok y Reels. Tu objetivo es encontrar momentos del tipo: {clip_type}.

Analiza la transcripción con marcas de tiempo y selecciona la MAYOR CANTIDAD POSIBLE de segmentos (hasta {max_clips} clips).
- Si el video es largo (por ejemplo, 1 hora), DEBES encontrar entre {min_clips} y {max_clips} clips. No te quedes corto.
- Cada clip debe cubrir un momento COMPLETO: si alguien empieza a contar una historia, una anécdota, un argumento o una reflexión, el clip DEBE incluir el desenlace o conclusión de esa idea. No cortes en mitad de una frase o pensamiento.

REGLAS OBLIGATORIAS DE DURACIÓN:
- La duración mínima de cada clip es de 30 segundos (end - start >= 30.0). PROHIBIDO clips de menos de 30 segundos.
- La duración máxima es de 90 segundos. Si el momento lo requiere para completar la narrativa, puedes llegar a 90 segundos.
- Está ESTRICTAMENTE PROHIBIDO seleccionar fragmentos menores a 30 segundos.

REGLAS PARA EVITAR REPETICIÓN:
- Los clips NO pueden solaparse entre sí. Cada clip debe empezar al menos 10 segundos después del final del clip anterior.
- No selecciones el mismo fragmento de tiempo más de una vez aunque lo reformules de forma diferente.

TÍTULOS Y DESCRIPCIONES:
- Los títulos deben sonar 100% naturales, escritos por un creador de contenido humano.
- EVITA clichés de IA: "revolucionario", "el secreto de", "increíble", "descubre cómo", "impactante".
- Usa intriga, preguntas directas o afirmaciones contundentes.
  ❌ Malo: "El Secreto Para Ser Millonario"
  ✅ Bueno: "Por esto no eres millonario a los 20"

EVALUACIÓN DE VIRALIDAD:
- Asigna un "virality_score" entero del 0 al 100 a cada clip.
- Proporciona "virality_explanation": por qué enganchará a la audiencia (hook, ritmo, tema, etc.).

Transcripción:
{context_text}

Responde ÚNICAMENTE con un JSON array válido (sin texto fuera del JSON):
[
  {{
    "start": float,
    "end": float,
    "hook_title": "Título humano y viral",
    "social_description": "Copywriting para la descripción del video",
    "virality_score": int,
    "virality_explanation": "Por qué enganchará a la audiencia",
    "explanation": "Por qué este momento es viral"
  }}
]
"""

    # ── Call LLM ──────────────────────────────────────────────────────────────
    if provider == "ollama":
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }
        try:
            response = requests.post(api_url, json=payload, timeout=120)
            response.raise_for_status()
            res_json = response.json()
            response_text = res_json.get("response", "")
        except Exception as e:
            print(f"[!] Ollama connection error: {e}. Falling back to default segment (first 40 seconds).")
            return [{"start": 0.0, "end": 40.0, "hook_title": "Clip de Muestra", "explanation": "Fallback"}]
    else:
        headers = {
            "Authorization": f"Bearer {api_key or ''}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Eres un editor de video experto que devuelve solo JSON array."},
                {"role": "user",   "content": prompt},
            ],
            "response_format": {"type": "json_object"},
        }

        def do_request(payload_to_send):
            resp = requests.post(api_url, json=payload_to_send, headers=headers, timeout=120)
            resp.raise_for_status()
            return resp.json()

        try:
            res_json = do_request(payload)
            response_text = res_json["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[!] API connection error: {e}. Attempting retry with truncated context...")
            try:
                truncated_context = context_text[:3000]
                truncated_prompt = prompt.replace(context_text, truncated_context)
                payload_trunc = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "Eres un editor de video experto que devuelve solo JSON array."},
                        {"role": "user",   "content": truncated_prompt},
                    ],
                    "response_format": {"type": "json_object"},
                }
                res_json = do_request(payload_trunc)
                response_text = res_json["choices"][0]["message"]["content"]
            except Exception as e2:
                print(f"[!] Retry failed: {e2}. Falling back to default segment.")
                return [{"start": 0.0, "end": 40.0, "hook_title": "Clip de Muestra", "explanation": "Fallback"}]

    # ── Parse LLM response ────────────────────────────────────────────────────
    try:
        print(f"[*] Raw LLM Response:\n{response_text}")
        data = json.loads(response_text)

        # Unwrap common wrapper patterns
        if isinstance(data, dict) and "clips" in data:
            data = data["clips"]
        if isinstance(data, dict):
            nested = [v for v in data.values() if isinstance(v, dict) and any(k in v for k in ["start", "end", "start_time", "end_time", "inicio", "fin"])]
            if nested:
                data = nested
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

        # ── Normalize each clip ───────────────────────────────────────────────
        MIN_DURATION = 30.0
        MAX_DURATION = 90.0
        normalized_data = []

        for item in data:
            if not isinstance(item, dict):
                continue

            n = {}

            # Start time
            for k in ["start", "start_time", "startTime", "inicio"]:
                if k in item:
                    try:
                        n["start"] = float(item[k]); break
                    except (ValueError, TypeError):
                        pass
            if "start" not in n:
                n["start"] = 0.0

            # End time
            for k in ["end", "end_time", "endTime", "fin"]:
                if k in item:
                    try:
                        n["end"] = float(item[k]); break
                    except (ValueError, TypeError):
                        pass
            if "end" not in n:
                n["end"] = n["start"] + MIN_DURATION

            # Enforce minimum duration (30s)
            clip_dur = n["end"] - n["start"]
            if clip_dur < MIN_DURATION:
                extra = MIN_DURATION - clip_dur
                n["start"] = max(0.0, n["start"] - extra / 2)
                n["end"]   = n["end"] + extra / 2
            # Enforce maximum duration (90s)
            if n["end"] - n["start"] > MAX_DURATION:
                n["end"] = n["start"] + MAX_DURATION

            n["start"] = round(n["start"], 2)
            n["end"]   = round(n["end"],   2)

            # Title
            for k in ["hook_title", "title", "titulo", "título", "hookTitle"]:
                if k in item:
                    n["hook_title"] = str(item[k]); break
            if "hook_title" not in n:
                n["hook_title"] = "Clip Viral"

            # Description
            for k in ["social_description", "socialDescription", "description", "descripcion", "descripción", "copy", "caption"]:
                if k in item:
                    n["social_description"] = str(item[k]); break
            if "social_description" not in n:
                n["social_description"] = item.get("explanation", "Mira este increíble momento.")

            # Virality score
            for k in ["virality_score", "viralityScore", "score", "puntuacion"]:
                if k in item:
                    try:
                        n["virality_score"] = int(item[k]); break
                    except (ValueError, TypeError):
                        pass
            if "virality_score" not in n:
                n["virality_score"] = 85

            # Virality explanation
            for k in ["virality_explanation", "viralityExplanation", "reason"]:
                if k in item:
                    n["virality_explanation"] = str(item[k]); break
            if "virality_explanation" not in n:
                n["virality_explanation"] = item.get("explanation", "Estructura narrativa sólida y gancho inicial de impacto.")

            n["explanation"] = item.get("explanation", "")
            normalized_data.append(n)

        # Final deduplication pass within a single chunk result
        normalized_data = _deduplicate_clips(normalized_data, min_gap=10.0)
        return normalized_data

    except Exception as e:
        print(f"[!] Error parsing LLM response as JSON: {e}")
        # Try extracting a JSON array from raw text
        try:
            start_idx = response_text.find("[")
            end_idx   = response_text.rfind("]") + 1
            if start_idx != -1 and end_idx > start_idx:
                partial = json.loads(response_text[start_idx:end_idx])
                if isinstance(partial, list) and partial:
                    return partial
        except Exception:
            pass
        return [{"start": 0.0, "end": 40.0, "hook_title": "Clip de Muestra", "social_description": "Fallback", "explanation": "Failed to parse JSON response"}]


if __name__ == "__main__":
    dummy_transcript = [
        {"start": 0.0,  "end": 5.0,  "text": "Hola a todos, hoy vamos a hablar de cómo el éxito no ocurre de la noche a la mañana."},
        {"start": 5.0,  "end": 15.0, "text": "Mucha gente piensa que los millonarios tuvieron suerte, pero la verdad es otra."},
        {"start": 15.0, "end": 35.0, "text": "Trabajaron 16 horas diarias durante 5 años seguidos. Eso no es suerte, es pura disciplina y constancia absoluta!"},
        {"start": 35.0, "end": 55.0, "text": "Y es que la disciplina sin consistencia no funciona. Tienes que hacerlo todos los días sin excepción."},
        {"start": 55.0, "end": 75.0, "text": "Así es como se logra el éxito real. Sígueme para más consejos motivacionales."},
    ]
    print(select_best_moments_with_llm(dummy_transcript))
