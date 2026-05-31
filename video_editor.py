import os
import subprocess
import sys
import imageio_ffmpeg

def get_ffmpeg_path():
    """Resolves path to FFmpeg strictly using imageio-ffmpeg."""

    # Si estamos corriendo como .exe empaquetado por PyInstaller
    if getattr(sys, 'frozen', False):
        for root, dirs, files in os.walk(sys._MEIPASS):
            for file in files:
                if file.startswith("ffmpeg") and file.endswith(".exe"):
                    return os.path.join(root, file)
                    
    return imageio_ffmpeg.get_ffmpeg_exe()

def process_video_clip(video_path, start_time, end_time, ass_path, output_path, zoom_effect=False):
    """
    Cuts, crops to 9:16, and burns ASS subtitles onto a video clip using FFmpeg.
    """
    duration = end_time - start_time
    print(f"[*] Processing clip: {start_time}s to {end_time}s (duration: {duration:.2f}s)...")
    

                         
                                                          
                                   
                       
    
    filter_chain = f"crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920"
    
                                                                        
                                                 
    if zoom_effect:
                                                                                       
                                                                                                            
                                            
                                                                                        
                                                                       
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
        "-preset", "veryfast",                                  
        "-crf", "22",                           
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
                                    
    pass
