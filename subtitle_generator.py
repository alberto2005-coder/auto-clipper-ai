import os

# ─────────────────────────────────────────────────────────────────────────────
# ASS color format: &HAABBGGRR  (AA=00 means fully opaque)
# ─────────────────────────────────────────────────────────────────────────────

# Each preset is a dict with the ASS style fields that differ per style:
#   primary    → text color
#   outline    → outline/border color
#   back       → background box color
#   border_w   → outline width (0 = no outline)
#   shadow_w   → shadow depth
#   border_sty → 1=outline+shadow, 3=filled box behind text
#   highlight  → inline override color for the karaoke-highlighted word
SUBTITLE_STYLES = {
    "tiktok": {
        "label": "🎵 TikTok (blanco + borde negro)",
        "primary":    "&H00FFFFFF",  # white text
        "outline":    "&H00000000",  # black outline
        "back":       "&H00000000",  # unused (border_sty=1)
        "border_w":   6,
        "shadow_w":   0,
        "border_sty": 1,
        "highlight":  "&H00FFFF00",  # cyan highlight for active word
    },
    "brillo": {
        "label": "✨ Brillo (Amarillo Neón + Borde y Sombra)",
        "primary":    "&H0000FFFF",  # Yellow
        "outline":    "&H00000000",  # Black
        "back":       "&H0000FFFF",  # Yellow shadow/glow
        "border_w":   3,
        "shadow_w":   4,
        "border_sty": 1,
        "highlight":  "&H0000FF00",  # Bright Green highlight
    },
    "caja_blanca": {
        "label": "⬜ Caja blanca + letra negra",
        "primary":    "&H00000000",  # black text
        "outline":    "&H00FFFFFF",  # white (unused visually with box)
        "back":       "&H00FFFFFF",  # white box
        "border_w":   0,
        "shadow_w":   0,
        "border_sty": 3,             # box mode
        "highlight":  "&H000000FF",  # red highlight for active word
    },
    "caja_negra": {
        "label": "⬛ Caja negra + letra blanca",
        "primary":    "&H00FFFFFF",
        "outline":    "&H00000000",
        "back":       "&HAA000000",  # semi-transparent black box
        "border_w":   0,
        "shadow_w":   0,
        "border_sty": 3,
        "highlight":  "&H0000FFFF",  # yellow highlight
    },
    "amarillo": {
        "label": "💛 Amarillo + borde negro (YouTube)",
        "primary":    "&H0000FFFF",  # yellow (BGRformat: FF FF 00)
        "outline":    "&H00000000",
        "back":       "&H00000000",
        "border_w":   3,
        "shadow_w":   4,
        "border_sty": 1,
        "highlight":  "&H000000FF",  # red highlight
    },
    "neon": {
        "label": "🟢 Neón (cian + borde negro)",
        "primary":    "&H00FFFF00",  # cyan
        "outline":    "&H00000000",
        "back":       "&H00000000",
        "border_w":   4,
        "shadow_w":   0,
        "border_sty": 1,
        "highlight":  "&H00FFFFFF",  # white highlight
    },
    "capcut": {
        "label": "🎬 CapCut (letra blanca + borde y sombra)",
        "primary":    "&H00FFFFFF",  # white text
        "outline":    "&H00000000",  # black outline
        "back":       "&H00000000",
        "border_w":   3,
        "shadow_w":   4,             # drop shadow
        "border_sty": 1,
        "highlight":  "&H0000FFFF",  # yellow active word highlight
    },
}

# Fonts that are reliable on Windows systems
AVAILABLE_FONTS = [
    "Arial Black",
    "Impact",
    "Arial",
    "Verdana",
    "Tahoma",
    "Comic Sans MS",
    "Trebuchet MS",
    "Georgia",
]


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


def to_inline_color(ass_color):
    """Converts a standard ASS color (e.g. &H00AABBCC) to a 6-hex-digit BGR string (e.g. BBCCAA) for inline tags."""
    clean = ass_color.replace("&H", "").replace("&", "")
    return clean[-6:]


def generate_ass_subtitles(
    transcription_data,
    clip_start,
    clip_end,
    output_ass_path="subtitles.ass",
    subtitle_position="bottom",
    font_name="Arial Black",
    font_size=75,
    subtitle_style="tiktok",
    margin_override=None,
):
    """
    Generates a stylized ASS subtitle file highlighting the active word.

    Parameters
    ----------
    subtitle_position : 'top' | 'center' | 'bottom'
    font_name         : Font family (must be installed on the system).
    font_size         : Base font size in ASS units (reference 1080x1920).
    subtitle_style    : Key in SUBTITLE_STYLES dict.
    margin_override   : If set (int), overrides the default MarginV so subtitles
                        are pushed away from the title when they share the same edge.
    """
    print(
        f"[*] Generating ASS subtitles | pos={subtitle_position} | "
        f"font={font_name} {font_size}pt | style={subtitle_style}"
    )
    try:
        with open("debug_log.txt", "a", encoding="utf-8") as dbg:
            dbg.write(f"style={subtitle_style} | pos={subtitle_position} | font={font_name} | size={font_size}\n")
    except Exception:
        pass

    # ── Position mapping ─────────────────────────────────────────────────────
    # ASS Alignment numpad layout:
    #   7=top-left   8=top-center   9=top-right
    #   4=mid-left   5=mid-center   6=mid-right
    #   1=bot-left   2=bot-center   3=bot-right
    POSITION_MAP = {
        "top":    ("8", "120"),   # top-center, 120px from top
        "center": ("5", "0"),     # mid-center
        "bottom": ("2", "200"),   # bottom-center, 200px from bottom
    }
    alignment, margin_v = POSITION_MAP.get(subtitle_position, POSITION_MAP["bottom"])
    # When title and subtitle share the same edge, caller provides an override
    # so the subtitle block appears right after the title instead of overlapping.
    if margin_override is not None:
        margin_v = str(int(margin_override))


    # ── Style preset ─────────────────────────────────────────────────────────
    style = SUBTITLE_STYLES.get(subtitle_style, SUBTITLE_STYLES["tiktok"])

    # ── Build word list ───────────────────────────────────────────────────────
    all_words = []
    for segment in transcription_data:
        for w in segment.get("words", []):
            start = w["start"]
            end = w["end"]
            if start >= clip_start and end <= clip_end:
                all_words.append({
                    "word":  w["word"].strip().upper(),
                    "start": start - clip_start,
                    "end":   end - clip_start,
                })

    if not all_words:
        print("[!] No words found in the clip range for subtitles.")
        return False

    # ── ASS header ────────────────────────────────────────────────────────────
    ass_template = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{style['primary']},&H0000FFFF,{style['outline']},{style['back']},1,0,0,0,100,100,0,0,{style['border_sty']},{style['border_w']},{style['shadow_w']},{alignment},100,100,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    # ── Build karaoke events (3-word rolling window) ──────────────────────────
    events = []
    n_words = len(all_words)
    chunk_size = 3
    highlight_color = style["highlight"]
    high_rgb = to_inline_color(highlight_color)
    prim_rgb = to_inline_color(style["primary"])

    for i in range(n_words):
        current_word = all_words[i]
        start_str = format_timestamp(current_word["start"])
        end_time = max(current_word["end"], current_word["start"] + 0.05)
        end_str = format_timestamp(end_time)

        # Rolling 3-word window centred around the active word
        start_idx = max(0, i - 1)
        end_idx = min(n_words, start_idx + chunk_size)
        if end_idx - start_idx < chunk_size:
            start_idx = max(0, end_idx - chunk_size)

        chunk = all_words[start_idx:end_idx]

        formatted_words = []
        for w in chunk:
            if w == current_word:
                # Highlighted active word
                formatted_words.append(
                    f"{{\\c&H{high_rgb}&}}{w['word']}{{\\c&H{prim_rgb}&}}"
                )
            else:
                formatted_words.append(w["word"])

        line_text = " ".join(formatted_words)
        events.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{line_text}")

    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_template)
        f.write("\n".join(events))

    print(f"[+] Subtitles generated at {output_ass_path}")
    return True


if __name__ == "__main__":
    dummy_words = [
        {"word": "Hola",    "start": 0.5, "end": 1.0},
        {"word": "amigos,", "start": 1.0, "end": 1.5},
        {"word": "esto",    "start": 1.5, "end": 1.8},
        {"word": "es",      "start": 1.8, "end": 2.0},
        {"word": "una",     "start": 2.0, "end": 2.2},
        {"word": "prueba",  "start": 2.2, "end": 2.8},
    ]
    dummy_data = [{"words": dummy_words}]
    generate_ass_subtitles(dummy_data, 0.0, 3.0, subtitle_style="caja_blanca")
