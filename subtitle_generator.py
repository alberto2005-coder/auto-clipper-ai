import os

# ─────────────────────────────────────────────────────────────────────────────
# ASS color format: &HAABBGGRR  (AA=00 means fully opaque)
# ─────────────────────────────────────────────────────────────────────────────
#
# En el modelo karaoke por línea (un Dialogue por grupo de palabras):
#   PrimaryColour   → color de la palabra ACTIVA (la que se está diciendo)
#   SecondaryColour → color de las palabras EN ESPERA (aún no dichas)
#   El tag \k<cs> hace que cada palabra se ilumine en secuencia.
#
# En SUBTITLE_STYLES:
#   primary   → color del texto en reposo / no activo  (→ SecondaryColour en ASS)
#   highlight → color de la palabra activa             (→ PrimaryColour en ASS)
# ─────────────────────────────────────────────────────────────────────────────

SUBTITLE_STYLES = {
    "tiktok": {
        "label":      "🎵 TikTok (blanco + borde negro)",
        "primary":    "&H00FFFFFF",  # white  — palabras en espera
        "outline":    "&H00000000",  # black outline
        "back":       "&H00000000",
        "border_w":   6,
        "shadow_w":   0,
        "border_sty": 1,
        "highlight":  "&H0000FFFF",  # yellow — palabra activa
    },
    "neon_blanco": {
        "label":      "⚡ Neón Blanco (blanco puro + glow negro)",
        "primary":    "&H99FFFFFF",  # blanco semitransparente — en espera
        "outline":    "&H00000000",  # borde negro grueso
        "back":       "&H44000000",
        "border_w":   8,
        "shadow_w":   3,
        "border_sty": 1,
        "highlight":  "&H00FFFFFF",  # blanco puro brillante — activa
    },
    "brillo": {
        "label":      "✨ Brillo (Amarillo Neón + Borde y Sombra)",
        "primary":    "&H8800FFFF",  # amarillo semitransparente — en espera
        "outline":    "&H00000000",
        "back":       "&H0000FFFF",
        "border_w":   3,
        "shadow_w":   4,
        "border_sty": 1,
        "highlight":  "&H0000FFFF",  # amarillo puro — activa
    },
    "caja_blanca": {
        "label":      "⬜ Caja blanca + letra negra",
        "primary":    "&H88000000",  # negro semitransparente — en espera
        "outline":    "&H00FFFFFF",
        "back":       "&H00FFFFFF",  # white box
        "border_w":   0,
        "shadow_w":   0,
        "border_sty": 3,
        "highlight":  "&H000000FF",  # rojo — activa
    },
    "caja_negra": {
        "label":      "⬛ Caja negra + letra blanca",
        "primary":    "&H88FFFFFF",  # blanco semitransparente — en espera
        "outline":    "&H00000000",
        "back":       "&HAA000000",
        "border_w":   0,
        "shadow_w":   0,
        "border_sty": 3,
        "highlight":  "&H0000FFFF",  # amarillo — activa
    },
    "amarillo": {
        "label":      "💛 Amarillo + borde negro (YouTube)",
        "primary":    "&H880000FF",  # amarillo tenue — en espera  (BGR: FF FF 00)
        "outline":    "&H00000000",
        "back":       "&H00000000",
        "border_w":   3,
        "shadow_w":   4,
        "border_sty": 1,
        "highlight":  "&H0000FFFF",  # amarillo puro — activa
    },
    "neon": {
        "label":      "🟢 Neón (cian + borde negro)",
        "primary":    "&H88FFFF00",  # cian tenue — en espera  (BGR: 00 FF FF)
        "outline":    "&H00000000",
        "back":       "&H00000000",
        "border_w":   4,
        "shadow_w":   0,
        "border_sty": 1,
        "highlight":  "&H00FFFF00",  # cian puro — activa
    },
    "capcut": {
        "label":      "🎬 CapCut (letra blanca + borde y sombra)",
        "primary":    "&H99FFFFFF",  # blanco tenue — en espera
        "outline":    "&H00000000",
        "back":       "&H00000000",
        "border_w":   3,
        "shadow_w":   4,
        "border_sty": 1,
        "highlight":  "&H00FFFFFF",  # blanco puro brillante — activa
    },
}

# Fonts that are reliable on Windows systems
AVAILABLE_FONTS = [
    "Montserrat",
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
    hours        = int(seconds // 3600)
    minutes      = int((seconds % 3600) // 60)
    secs         = int(seconds % 60)
    centiseconds = int(round((seconds % 1) * 100))
    if centiseconds == 100:
        secs        += 1
        centiseconds = 0
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"


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
    Generates a stylized ASS subtitle file using a LINE-BASED karaoke model.

    One Dialogue event per group of 3-4 words (chunk).  Each event spans the
    full duration of its word group (~1-4 seconds), so the \\fad fade tag has
    enough room to work without causing flicker.  Within each event the active
    word is illuminated via ASS \\k karaoke timing tags.

    Parameters
    ----------
    subtitle_position : 'top' | 'center' | 'bottom'
    font_name         : Font family (must be installed on the system).
    font_size         : Base font size in ASS units (reference 1080x1920).
    subtitle_style    : Key in SUBTITLE_STYLES dict.
    margin_override   : If set (int), overrides the default MarginV.
    """
    print(
        f"[*] Generating ASS subtitles | pos={subtitle_position} | "
        f"font={font_name} {font_size}pt | style={subtitle_style}"
    )

    # ── Position mapping ──────────────────────────────────────────────────────
    POSITION_MAP = {
        "top":    ("8", "120"),
        "center": ("5", "0"),
        "bottom": ("2", "200"),
    }
    alignment, margin_v = POSITION_MAP.get(subtitle_position, POSITION_MAP["bottom"])
    if margin_override is not None:
        margin_v = str(int(margin_override))

    # ── Style preset ──────────────────────────────────────────────────────────
    style = SUBTITLE_STYLES.get(subtitle_style, SUBTITLE_STYLES["tiktok"])

    # ASS PrimaryColour   = base / waiting word color (PrimaryColour in ASS style definition)
    # ASS SecondaryColour = highlight / active word color (SecondaryColour in ASS style definition)
    ass_primary   = style["primary"]       # waiting word color (non-active)
    ass_secondary = style["highlight"]     # active word color (under karaoke tag)

    # ── Build word list ───────────────────────────────────────────────────────
    all_words = []
    for segment in transcription_data:
        for w in segment.get("words", []):
            w_start = w["start"]
            w_end   = w["end"]
            # Permitir palabras que comiencen dentro del rango o que tengan un solapamiento significativo
            # (esto evita que límites muy estrictos de decimales de la IA descarten palabras al inicio/fin del clip)
            if (w_start >= clip_start - 0.5 and w_start < clip_end) or (w_end > clip_start and w_end <= clip_end + 0.5):
                # Clampear tiempos relativos para que no queden fuera del rango [0, duration]
                rel_start = max(0.0, w_start - clip_start)
                rel_end   = min(clip_end - clip_start, w_end - clip_start)
                if rel_end > rel_start:
                    all_words.append({
                        "word":  w["word"].strip().upper(),
                        "start": rel_start,
                        "end":   rel_end,
                    })

    if not all_words:
        print("[!] No words found in the clip range for subtitles.")
        return False

    # ── ASS header ────────────────────────────────────────────────────────────
    # Standard ASS Karaoke uses SecondaryColour for the color of the text *before*
    # the karaoke highlight sweeps over it, and PrimaryColour for the color *after*.
    # In order to make waiting words show primary (waiting) and active show highlight,
    # we assign ass_primary (waiting) to SecondaryColour and ass_secondary (highlight) to PrimaryColour.
    ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{ass_secondary},{ass_primary},{style['outline']},{style['back']},1,0,0,0,100,100,0,0,{style['border_sty']},{style['border_w']},{style['shadow_w']},{alignment},100,100,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    # ── Build karaoke events (LINE-BASED: one event per word-group) ──────────
    #
    # Each chunk of CHUNK_SIZE words becomes a single Dialogue event.
    # Duration ≈ 1-4 seconds → \fad(250,150) works correctly with no flicker.
    # \k<cs> tags advance the karaoke highlight word by word.
    #
    CHUNK_SIZE = int(os.environ.get("SUBTITLE_CHUNK_SIZE", 3))
    FADE_IN_MS  = 250   # ms
    FADE_OUT_MS = 150   # ms

    events  = []
    n_words = len(all_words)

    chunk_idx = 0
    while chunk_idx < n_words:
        chunk     = all_words[chunk_idx: chunk_idx + CHUNK_SIZE]
        chunk_start = chunk[0]["start"]
        # Give the last chunk a minimum visible duration of 500ms
        chunk_end   = max(chunk[-1]["end"], chunk_start + 0.50)

        start_str = format_timestamp(chunk_start)
        end_str   = format_timestamp(chunk_end)

        # Build the karaoke text: {\kXX}WORD1 {\kXX}WORD2 ...
        # \k duration is in centiseconds (1 cs = 10 ms)
        text_parts = []
        for w in chunk:
            dur_cs = max(5, int(round((w["end"] - w["start"]) * 100)))
            text_parts.append(f"{{\\k{dur_cs}}}{w['word']}")

        line_text = " ".join(text_parts)

        # Apply fade only when the event is long enough (≥ fade_in + fade_out)
        min_fade_duration = (FADE_IN_MS + FADE_OUT_MS) / 1000.0
        if chunk_end - chunk_start >= min_fade_duration:
            fade_tag = f"{{\\fad({FADE_IN_MS},{FADE_OUT_MS})}}"
        else:
            fade_tag = ""

        full_text = fade_tag + line_text
        events.append(
            f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{full_text}"
        )

        chunk_idx += CHUNK_SIZE

    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        f.write("\n".join(events))

    print(f"[+] Subtitles generated: {output_ass_path} ({len(events)} line events)")
    return True


if __name__ == "__main__":
    dummy_words = [
        {"word": "hola",    "start": 0.5,  "end": 0.9},
        {"word": "amigos",  "start": 0.9,  "end": 1.4},
        {"word": "esto",    "start": 1.5,  "end": 1.8},
        {"word": "es",      "start": 1.8,  "end": 2.0},
        {"word": "una",     "start": 2.0,  "end": 2.2},
        {"word": "prueba",  "start": 2.2,  "end": 2.8},
        {"word": "del",     "start": 2.9,  "end": 3.1},
        {"word": "sistema", "start": 3.1,  "end": 3.7},
    ]
    dummy_data = [{"words": dummy_words}]
    for style_key in ["tiktok", "neon_blanco", "amarillo"]:
        out = f"test_{style_key}.ass"
        generate_ass_subtitles(dummy_data, 0.0, 4.0, out, subtitle_style=style_key)
        with open(out, encoding="utf-8") as f:
            print(f"\n=== {style_key} ===")
            print(f.read())
