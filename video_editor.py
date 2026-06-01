import os
import subprocess
import sys

# ─────────────────────────────────────────────────────────────────────────────
# Title style presets — typical for TikTok / YouTube Shorts
# ─────────────────────────────────────────────────────────────────────────────
TITLE_STYLES = {
    "clasico": {
        "label": "⬜ Clásico (blanco + borde negro)",
        "fontcolor":   "white",
        "use_box":     False,
        "boxcolor":    None,
        "border_ratio": 0.12,   # borderw = fontsize * ratio
    },
    "amarillo": {
        "label": "💛 Amarillo + borde negro",
        "fontcolor":   "yellow",
        "use_box":     False,
        "boxcolor":    None,
        "border_ratio": 0.10,
    },
    "caja_negra": {
        "label": "⬛ Caja negra semitransparente",
        "fontcolor":   "white",
        "use_box":     True,
        "boxcolor":    "black@0.65",
        "border_ratio": 0.0,
    },
    "caja_blanca": {
        "label": "⬜ Caja blanca + letra negra",
        "fontcolor":   "black",
        "use_box":     True,
        "boxcolor":    "white@0.90",
        "border_ratio": 0.0,
    },
    "neon": {
        "label": "🟢 Neón cian",
        "fontcolor":   "cyan",
        "use_box":     False,
        "boxcolor":    None,
        "border_ratio": 0.10,
    },
    "rojo": {
        "label": "🔴 Rojo viral",
        "fontcolor":   "red",
        "use_box":     False,
        "boxcolor":    None,
        "border_ratio": 0.10,
    },
    "naranja": {
        "label": "🟠 Naranja energético",
        "fontcolor":   "orange",
        "use_box":     False,
        "boxcolor":    None,
        "border_ratio": 0.10,
    },
}

# Fonts reliable on Windows
TITLE_FONTS = [
    "Arial Bold",
    "Impact",
    "Arial Black",
    "Arial",
    "Verdana",
    "Tahoma",
    "Trebuchet MS",
    "Georgia",
]


def get_ffmpeg_path():
    """Resolves path to FFmpeg strictly using imageio-ffmpeg."""
    if getattr(sys, 'frozen', False):
        for root, dirs, files in os.walk(sys._MEIPASS):
            for file in files:
                if file.startswith("ffmpeg") and file.endswith(".exe"):
                    return os.path.join(root, file)
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def _escape_drawtext(text):
    """Escapes special characters for a single-line FFmpeg drawtext text value."""
    text = text.replace("%",  "%%")
    text = text.replace("'",  "\\'")
    text = text.replace(":",  "\\:")
    text = text.replace(",",  "\\,")
    return text


def _wrap_title_lines(hook_title, vid_w, title_fontsize):
    """
    Wraps a title into lines that fit within vid_w pixels.
    max_chars is estimated from font metrics (bold ~60% of fontsize per char).
    Returns a list of escaped strings, one per line.
    """
    # ~60% of fontsize = average char width for bold fonts; 0.90 = usable width margin
    max_chars = max(8, int(vid_w * 0.90 / (title_fontsize * 0.60)))

    words = hook_title.split()
    lines = []
    current = ""
    for word in words:
        if len(current) + len(word) + (1 if current else 0) <= max_chars:
            current = (current + " " + word).strip()
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return [_escape_drawtext(line) for line in lines]


def compute_title_info(
    hook_title,
    video_format="9:16",
    title_position="top",
    title_font_size=90,
):
    """
    Returns (anchor_px, total_height_px) for the title block.

    anchor_px       : distance from the reference edge (top/bottom) in pixels.
    total_height_px : total pixel height of all title lines (line_h × n_lines).

    Used by gui.py to offset subtitles when they share the same edge as the title.
    """
    vid_dims = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}
    vid_w, vid_h = vid_dims.get(video_format, (1080, 1920))

    # Scale from 1920h reference
    actual_fontsize = max(12, int(title_font_size * vid_h / 1920))
    line_h = int(actual_fontsize * 1.30)

    lines = _wrap_title_lines(hook_title, vid_w, actual_fontsize)
    n_lines = max(len(lines), 1)
    total_h = n_lines * line_h

    if title_position == "top":
        anchor_px = int(vid_h * 0.04)
    elif title_position == "bottom":
        anchor_px = int(vid_h * 0.08)
    else:  # center
        anchor_px = (vid_h - total_h) // 2

    return anchor_px, total_h


def process_video_clip(
    video_path,
    start_time,
    end_time,
    ass_path,
    output_path,
    zoom_effect=False,
    video_format="9:16",
    hook_title="",
    title_position="top",
    title_font_size=90,
    title_style="clasico",
    title_font="Arial Bold",
    subtitle_position="bottom",
):
    """
    Cuts, re-frames, burns the hook title and ASS subtitles onto a video clip.

    video_format    : "9:16" | "16:9" | "1:1"
    hook_title      : Text to burn in (empty string = disabled).
    title_position  : "top" | "center" | "bottom"
    title_font_size : Font size in px at 1920h reference (scaled for other heights).
    title_style     : Key in TITLE_STYLES.
    title_font      : Font family name (must be installed on the system).
    subtitle_position: "top" | "center" | "bottom"
    """
    duration = end_time - start_time
    print(
        f"[*] Processing clip: {start_time}s → {end_time}s ({duration:.1f}s) | "
        f"format: {video_format} | title_pos: {title_position} | sub_pos: {subtitle_position}"
    )

    # ── 1. Crop + Scale ───────────────────────────────────────────────────────
    vid_dims = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}
    vid_w, vid_h = vid_dims.get(video_format, (1080, 1920))

    if video_format == "9:16":
        filter_chain = "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920"
    elif video_format == "16:9":
        filter_chain = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
    elif video_format == "1:1":
        filter_chain = "crop=min(iw\\,ih):min(iw\\,ih):(iw-min(iw\\,ih))/2:(ih-min(iw\\,ih))/2,scale=1080:1080"
    else:
        filter_chain = "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920"

    if zoom_effect:
        pass

    # ── 2. Hook title — one drawtext filter per line ──────────────────────────
    if hook_title:
        actual_fontsize = max(12, int(title_font_size * vid_h / 1920))
        line_h          = int(actual_fontsize * 1.30)
        border_w        = max(2, int(actual_fontsize * TITLE_STYLES.get(title_style, TITLE_STYLES["clasico"])["border_ratio"]))
        style           = TITLE_STYLES.get(title_style, TITLE_STYLES["clasico"])
        box_w           = int(actual_fontsize * 0.25)   # box padding

        lines = _wrap_title_lines(hook_title, vid_w, actual_fontsize)
        total_title_h = len(lines) * line_h

        # Starting Y of the whole title block
        if title_position == "top":
            start_y = int(vid_h * 0.04)
        elif title_position == "center":
            start_y = (vid_h - total_title_h) // 2
        else:  # bottom
            start_y = vid_h - total_title_h - int(vid_h * 0.08)

        for i, escaped_line in enumerate(lines):
            line_y = start_y + i * line_h
            if style["use_box"]:
                dt = (
                    f"drawtext=text='{escaped_line}'"
                    f":fontsize={actual_fontsize}"
                    f":fontcolor={style['fontcolor']}"
                    f":box=1:boxcolor={style['boxcolor']}:boxborderw={box_w}"
                    f":x=(w-text_w)/2"
                    f":y={line_y}"
                    f":font={title_font}"
                )
            else:
                dt = (
                    f"drawtext=text='{escaped_line}'"
                    f":fontsize={actual_fontsize}"
                    f":fontcolor={style['fontcolor']}"
                    f":bordercolor=black@0.9:borderw={border_w}"
                    f":x=(w-text_w)/2"
                    f":y={line_y}"
                    f":font={title_font}"
                )
            filter_chain += f",{dt}"

    # ── 3. ASS subtitles ──────────────────────────────────────────────────────
    if ass_path and os.path.exists(ass_path):
        escaped_ass_path = ass_path.replace("\\", "/").replace(":", "\\:")
        filter_chain += f",subtitles='{escaped_ass_path}'"

    # ── 4. FFmpeg command ─────────────────────────────────────────────────────
    ffmpeg_bin = get_ffmpeg_path()
    cmd = [
        ffmpeg_bin, "-y",
        "-ss", str(start_time),
        "-to", str(end_time),
        "-i", video_path,
        "-vf", filter_chain,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",
        "-c:a", "aac",
        "-b:a", "192k",
        output_path
    ]

    print("[*] Running FFmpeg command for export...")
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except FileNotFoundError as fnf:
        raise RuntimeError(f"Error de sistema: No se pudo encontrar o ejecutar el binario de FFmpeg. Verifica su disponibilidad en '{ffmpeg_bin}'.") from fnf
    except Exception as e:
        raise RuntimeError(f"Error crítico al iniciar el proceso de FFmpeg para la exportación: {e}") from e

    if result.returncode != 0:
        print("[!] FFmpeg Error:")
        print(result.stderr)
        raise RuntimeError(f"FFmpeg falló al procesar el video. Detalles técnicos del error:\n{result.stderr}")

    print(f"[+] Exported clip → {output_path}")
    return output_path


def mix_background_music(video_path, audio_path, volume, output_path):
    """
    Mixes background audio with an existing video's audio track.
    Copies the video stream (-c:v copy) to complete the process instantly.
    """
    import os
    import subprocess
    print(f"[*] Mixing background music: {audio_path} (vol={volume}) onto {video_path}")
    ffmpeg_bin = get_ffmpeg_path()
    
    # We write to a temporary file first, then replace output_path to avoid in-place edit issues.
    temp_output = output_path + ".mixing.mp4"
    
    cmd = [
        ffmpeg_bin, "-y",
        "-i", video_path,
        "-stream_loop", "-1", "-ss", "0", "-i", audio_path,
        "-filter_complex", f"[0:a]volume=1.0[a0];[1:a]volume={volume:.2f}[a1];[a0][a1]amix=inputs=2:duration=first:dropout_transition=0[a]",
        "-map", "0:v",
        "-map", "[a]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        temp_output
    ]
    
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except FileNotFoundError as fnf:
        if os.path.exists(temp_output):
            os.remove(temp_output)
        raise RuntimeError(f"Error de sistema: No se pudo encontrar o ejecutar el binario de FFmpeg. Verifica su disponibilidad en '{ffmpeg_bin}'.") from fnf
    except Exception as e:
        if os.path.exists(temp_output):
            os.remove(temp_output)
        raise RuntimeError(f"Error crítico al iniciar la mezcla de audio con FFmpeg: {e}") from e

    if result.returncode != 0:
        print("[!] FFmpeg mixing error:")
        print(result.stderr)
        if os.path.exists(temp_output):
            os.remove(temp_output)
        raise RuntimeError(f"FFmpeg falló al realizar la mezcla del audio de fondo. Detalles técnicos:\n{result.stderr}")
        
    # Replace the original file safely
    if os.path.exists(output_path):
        try:
            os.remove(output_path)
        except Exception as e:
            print(f"[!] Warning: could not remove original path during mix: {e}")
    try:
        os.rename(temp_output, output_path)
    except Exception as e:
        # If replace fails due to locks, try copying it instead
        import shutil
        shutil.copy2(temp_output, output_path)
        os.remove(temp_output)
        
    print(f"[+] Mixing completed → {output_path}")
    return output_path


if __name__ == "__main__":
    pass
