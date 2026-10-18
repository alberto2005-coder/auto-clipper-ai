import sys
import os
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from autoclipper.analyzer import select_best_moments_with_llm

# Simula requests.post: primer llamado lanza HTTPError 413, segundo retorna JSON válido
call = {"n": 0}

def fake_post(url, json=None, headers=None, timeout=None):
    call["n"] += 1
    if call["n"] == 1:
        class R1:
            def raise_for_status(self):
                raise requests.HTTPError("413 Client Error: Payload Too Large for url: test")
            def json(self):
                return {}
        return R1()
    else:
        class R2:
            def raise_for_status(self):
                return None
            def json(self):
                return {"choices": [{"message": {"content": '[{"start": 12, "end": 45, "hook_title": "Good Clip", "social_description": "desc", "explanation": "ok"}]'}}]}
        return R2()

requests.post = fake_post

# Genera transcripción larga (muchos segmentos)
transcription_data = []
for i in range(0, 200):
    transcription_data.append({"start": i*5.0, "end": i*5.0 + 4.0, "text": "palabra "*10})

clips = select_best_moments_with_llm(transcription_data, provider="openai", api_url="https://api.groq.com/openai/v1/chat/completions", api_key="FAKE", model="test")
print("Result clips:", clips)
