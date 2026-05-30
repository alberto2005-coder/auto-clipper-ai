import os

def format_timestamp(seconds):
    """Formats seconds into ASS format (H:MM:SS.cs)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centiseconds = int(round((seconds % 1) * 100))
    if centiseconds == 100:
        secs += 1
        centiseconds = 0
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"

def generate_ass_subtitles(transcription_data, clip_start, clip_end, output_ass_path="subtitles.ass"):
    """
    Generates a stylized ASS subtitle file highlighting the active word.
    Optimized for short vertical videos (9:16) with large centered text.
    """
    print(f"[*] Generating ASS subtitles for clip {clip_start}s - {clip_end}s...")
    
    # 1. Filter and normalize words in the range
    all_words = []
    for segment in transcription_data:
        for w in segment.get("words", []):
            start = w["start"]
            end = w["end"]
            # Keep words within or overlapping the clip range
            if start >= clip_start and end <= clip_end:
                all_words.append({
                    "word": w["word"].strip().upper(),
                    "start": start - clip_start,
                    "end": end - clip_start
                })
                
    if not all_words:
        print("[!] No words found in the clip range for subtitles.")
        return False

    # 2. Write the ASS headers and style definitions
    # Alignment 5 = Middle Center. MargV is vertical offset from center if needed, or 2 = Bottom center with high margin.
    # Alignment 2 is very reliable. Let's use Alignment 2 (bottom center) with MarginV=400 (which brings it up).
    ass_template = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,75,&H00FFFFFF,&H0000FFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,6,0,2,100,100,750,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events = []
    
    # 3. Create active word highlights.
    # Group words into blocks of 3 to show a clean phrase, shifting active word color.
    n_words = len(all_words)
    chunk_size = 3
    
    for i in range(n_words):
        current_word = all_words[i]
        start_str = format_timestamp(current_word["start"])
        # Avoid zero duration or overlaps
        end_time = max(current_word["end"], current_word["start"] + 0.05)
        end_str = format_timestamp(end_time)
        
        # Decide which chunk of words to display
        # We want a sliding window of 3 words centered around the active word
        start_idx = max(0, i - 1)
        end_idx = min(n_words, start_idx + chunk_size)
        # Re-adjust start if we are near the end
        if end_idx - start_idx < chunk_size:
            start_idx = max(0, end_idx - chunk_size)
            
        chunk = all_words[start_idx:end_idx]
        
        # Format text with colors
        formatted_words = []
        for w in chunk:
            if w == current_word:
                # Active word (Yellow)
                formatted_words.append(f"{{\\c&H00FFFF&}}{w['word']}{{\\c&HFFFFFF&}}")
            else:
                # Normal word (White)
                formatted_words.append(w["word"])
                
        line_text = " ".join(formatted_words)
        
        # Add to ASS events
        events.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{line_text}")
        
    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_template)
        f.write("\n".join(events))
        
    print(f"[+] Subtitles generated at {output_ass_path}")
    return True

if __name__ == "__main__":
    # Test script
    dummy_words = [
        {"word": "Hola", "start": 0.5, "end": 1.0, "probability": 0.9},
        {"word": "amigos,", "start": 1.0, "end": 1.5, "probability": 0.9},
        {"word": "esto", "start": 1.5, "end": 1.8, "probability": 0.9},
        {"word": "es", "start": 1.8, "end": 2.0, "probability": 0.9},
        {"word": "una", "start": 2.0, "end": 2.2, "probability": 0.9},
        {"word": "prueba", "start": 2.2, "end": 2.8, "probability": 0.9},
    ]
    dummy_data = [{"words": dummy_words}]
    generate_ass_subtitles(dummy_data, 0.0, 3.0)
