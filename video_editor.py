import os
import subprocess

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

def process_video_clip(video_path, start_time, end_time, ass_path, output_path, zoom_effect=False):
    """
    Cuts, crops to 9:16, and burns ASS subtitles onto a video clip using FFmpeg.
    """
    duration = end_time - start_time
    print(f"[*] Processing clip: {start_time}s to {end_time}s (duration: {duration:.2f}s)...")
    

    # Build filter chain:
    # 1. Crop to 9:16 aspect ratio center: crop=ih*9/16:ih
    # 2. Scale up/down to 1080x1920
    # 3. Burn subtitles
    
    filter_chain = f"crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920"
    
    # Optional dynamic zoom: subtle pulsing zoom using scale and zoompan
    # (keeps it simple and stable on modest CPUs)
    if zoom_effect:
        # A simple zoom script that cuts back and forth slightly or does a slow zoom in
        # For simplicity and speed on CPU, we can alternate scale between 100% and 110% at regular intervals
        # Let's use a subtle zoompan filter:
        # zoompan=z='min(zoom+0.0015,1.1)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'
        # But zoompan can be performance heavy, so we make it optional.
        pass
    if ass_path and os.path.exists(ass_path):
        escaped_ass_path = ass_path.replace("\\", "/").replace(":", "\\:")
        filter_chain += f",subtitles='{escaped_ass_path}'"


    ffmpeg_bin = get_ffmpeg_path()
    cmd = [
        ffmpeg_bin, "-y",
        "-ss", str(start_time),
        "-to", str(end_time),
        "-i", video_path,
        "-vf", filter_chain,
        "-c:v", "libx264",
        "-preset", "veryfast",  # Fast compression, light on CPU
        "-crf", "22",           # Decent quality
        "-c:a", "aac",
        "-b:a", "192k",
        output_path
    ]

    
    print(f"[*] Running FFmpeg command for export...")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    if result.returncode != 0:
        print("[!] FFmpeg Error:")
        print(result.stderr)
        raise RuntimeError("FFmpeg processing failed.")
        
    print(f"[+] Exported video clip to {output_path}")
    return output_path

if __name__ == "__main__":
    # Test script if called directly
    pass
