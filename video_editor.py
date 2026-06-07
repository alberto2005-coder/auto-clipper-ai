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


def get_video_dimensions(video_path):
    """
    Returns (width, height) of a video file using FFprobe.
    Falls back to (0, 0) if detection fails.
    """
    try:
        import cv2
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            return w, h
    except Exception:
        pass
    return 0, 0


def is_portrait_video(video_path):
    """
    Returns True if the source video is already in portrait/vertical orientation (height > width).
    Camera tracking makes no sense for portrait videos being converted to 9:16.
    """
    w, h = get_video_dimensions(video_path)
    if w > 0 and h > 0:
        is_portrait = h > w
        print(f"[*] Source video dimensions: {w}x{h} → {'portrait (tracking disabled)' if is_portrait else 'landscape'}")
        return is_portrait
    return False


def detect_face_center(video_path, start_time, end_time, sample_rate=1.0):
    """
    Samples frames from the video clip and uses OpenCV's Haar Cascade classifier
    to find the average/median face X position.
    Returns (face_x_center_ratio, width, height) where face_x_center_ratio is from 0.0 to 1.0.
    Only uses the detected position if faces are found in at least 50% of sampled frames
    (confidence threshold), otherwise falls back to center (0.5).
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        print("[!] Warning: cv2 or numpy not found. Skipping face tracking.")
        return 0.5, 0, 0

    print(f"[*] Analyzing video for face tracking: {video_path} from {start_time}s to {end_time}s...")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("[!] Warning: Could not open video file with OpenCV for face tracking.")
        return 0.5, 0, 0

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if width <= 0 or height <= 0:
        cap.release()
        return 0.5, width, height

    # Load Haar cascade
    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(cascade_path)
    if face_cascade.empty():
        print("[!] Warning: OpenCV face cascade classifier failed to load.")
        cap.release()
        return 0.5, width, height

    start_frame = int(start_time * fps)
    end_frame   = int(end_time * fps)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    start_frame = max(0, min(start_frame, total_frames - 1))
    end_frame   = max(start_frame, min(end_frame, total_frames))

    # Sample exactly 10 frames evenly spaced
    num_samples  = 10
    frame_indices = [int(x) for x in np.linspace(start_frame, end_frame - 1, num_samples)]
    face_x_positions  = []
    frames_with_faces = 0

    for frame_idx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            break

        # Downscale frame for speed (scale height to 360px)
        h, w = frame.shape[:2]
        if w > 640:
            scale    = 360.0 / h
            target_w = int(w * scale)
            small_frame = cv2.resize(frame, (target_w, 360))
            x_scale  = w / target_w
        else:
            small_frame = frame
            x_scale  = 1.0

        gray  = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5, minSize=(30, 30))

        if len(faces) > 0:
            frames_with_faces += 1
            x, y, w_face, h_face = faces[0]
            face_center_x = (x + w_face / 2) * x_scale
            face_x_positions.append(face_center_x)

    cap.release()

    detection_ratio = frames_with_faces / max(len(frame_indices), 1)
    print(f"[*] Face detection confidence: {frames_with_faces}/{len(frame_indices)} frames ({detection_ratio:.0%})")

    # Only trust the face position if detected in at least 50% of frames
    if face_x_positions and detection_ratio >= 0.50:
        median_x = float(np.median(face_x_positions))
        ratio    = median_x / width
        print(f"[+] Face tracking → X position: {median_x:.1f}px (ratio: {ratio:.2f})")
        return ratio, width, height

    print("[*] Low face detection confidence or no faces found. Using center (0.5).")
    return 0.5, width, height


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
    camera_tracking=False,
    fade_effect=False,
    use_gpu=False,
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
    camera_tracking : Centrar la cámara en el rostro detectado (si es horizontal y pasa a vertical/cuadrado).
    fade_effect     : Animación de entrada y salida (transición de desvanecimiento).
    use_gpu         : Habilitar codificación por hardware usando la GPU (NVIDIA h264_nvenc).
    """
    duration = end_time - start_time
    print(
        f"[*] Processing clip: {start_time}s → {end_time}s ({duration:.1f}s) | "
        f"format: {video_format} | title_pos: {title_position} | sub_pos: {subtitle_position} | "
        f"tracking: {camera_tracking} | fade: {fade_effect}"
    )

    # ── 1. Crop + Scale ───────────────────────────────────────────────────────
    vid_dims = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}
    vid_w, vid_h = vid_dims.get(video_format, (1080, 1920))

    crop_x_expr = "(iw-ih*9/16)/2"
    crop_1to1_x_expr = "(iw-min(iw\\,ih))/2"

    # Skip face tracking if the source video is already portrait/vertical
    # (tracking makes no sense — there is nothing to re-frame)
    _effective_tracking = camera_tracking and not is_portrait_video(video_path)

    if _effective_tracking:
        face_ratio, orig_w, orig_h = detect_face_center(video_path, start_time, end_time)
        if orig_w > 0 and orig_h > 0:
            # For 9:16: crop width is orig_h * 9 / 16
            in_crop_w = orig_h * 9 / 16
            ideal_x   = int(face_ratio * orig_w - in_crop_w / 2)
            clamped_x = max(0, min(ideal_x, int(orig_w - in_crop_w)))
            crop_x_expr = str(clamped_x)

            # For 1:1: crop width is min(orig_w, orig_h)
            in_crop_1to1_w = min(orig_w, orig_h)
            ideal_1to1_x   = int(face_ratio * orig_w - in_crop_1to1_w / 2)
            clamped_1to1_x = max(0, min(ideal_1to1_x, int(orig_w - in_crop_1to1_w)))
            crop_1to1_x_expr = str(clamped_1to1_x)

    if video_format == "9:16":
        filter_chain = f"crop=ih*9/16:ih:{crop_x_expr}:0,scale=1080:1920"
    elif video_format == "16:9":
        filter_chain = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
    elif video_format == "1:1":
        filter_chain = f"crop=min(iw\\,ih):min(iw\\,ih):{crop_1to1_x_expr}:(ih-min(iw\\,ih))/2,scale=1080:1080"
    else:
        filter_chain = f"crop=ih*9/16:ih:{crop_x_expr}:0,scale=1080:1920"

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
        # FFmpeg subtitles filter requires forward slashes and the drive-letter
        # colon escaped as \: — but ONLY the drive colon, not the path itself.
        # Wrong: replace ALL ":" → breaks Windows paths like C:\...
        # Correct: forward slashes first, then escape only the first colon (drive letter)
        ass_fwd = ass_path.replace("\\", "/")
        # Escape the drive-letter colon: "C:/..." → "C\:/..."
        if len(ass_fwd) >= 2 and ass_fwd[1] == ":":
            ass_fwd = ass_fwd[0] + "\\:" + ass_fwd[2:]
        filter_chain += f",subtitles='{ass_fwd}'"

    # ── 3.5. Fade animations ──────────────────────────────────────────────────
    audio_filters = []
    if fade_effect:
        fade_d = 0.7
        if duration > 2 * fade_d:
            filter_chain += f",fade=t=in:st=0:d={fade_d},fade=t=out:st={duration - fade_d}:d={fade_d}"
            audio_filters.append(f"afade=t=in:st=0:d={fade_d}")
            audio_filters.append(f"afade=t=out:st={duration - fade_d}:d={fade_d}")

    # ── 4. FFmpeg command ─────────────────────────────────────────────────────
    ffmpeg_bin = get_ffmpeg_path()
    cmd = [
        ffmpeg_bin, "-y",
        "-ss", str(start_time),
        "-to", str(end_time),
        "-i", video_path,
        "-vf", filter_chain,
    ]
    if audio_filters:
        cmd.extend(["-af", ",".join(audio_filters)])

    v_codec = "h264_nvenc" if use_gpu else "libx264"
    preset = "fast" if use_gpu else "veryfast"
    
    cmd.extend([
        "-c:v", v_codec,
        "-preset", preset,
    ])
    if not use_gpu:
        cmd.extend(["-crf", "22"])

    cmd.extend([
        "-c:a", "aac",
        "-b:a", "192k",
        output_path
    ])

    print("[*] Running FFmpeg command for export...")
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except FileNotFoundError as fnf:
        raise RuntimeError(f"Error de sistema: No se pudo encontrar o ejecutar el binario de FFmpeg. Verifica su disponibilidad en '{ffmpeg_bin}'.") from fnf
    except Exception as e:
        raise RuntimeError(f"Error crítico al iniciar el proceso de FFmpeg para la exportación: {e}") from e

    if result.returncode != 0:
        if use_gpu:
            print("[!] GPU acceleration failed. Re-trying video processing on CPU (libx264)...")
            cmd_cpu = []
            skip_next = False
            for idx_arg, arg in enumerate(cmd):
                if skip_next:
                    skip_next = False
                    continue
                if arg == "-c:v":
                    cmd_cpu.extend(["-c:v", "libx264"])
                    skip_next = True
                elif arg == "-preset":
                    cmd_cpu.extend(["-preset", "veryfast"])
                    skip_next = True
                else:
                    cmd_cpu.append(arg)
            # Insert -crf 22 right before the output path (last element)
            output_idx = len(cmd_cpu) - 1
            cmd_cpu.insert(output_idx, "-crf")
            cmd_cpu.insert(output_idx + 1, "22")
            
            result = subprocess.run(cmd_cpu, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                print("[!] FFmpeg CPU Fallback Error:")
                print(result.stderr)
                raise RuntimeError(f"FFmpeg falló al procesar el video en CPU. Detalles técnicos del error:\n{result.stderr}")
        else:
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
