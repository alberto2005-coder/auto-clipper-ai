"""Auto-Clipper AI: Generación automatizada de clips verticales con IA."""

__version__ = "1.0.0"

from .transcriber import extract_audio, transcribe_audio, transcribe_audio_cloud
from .analyzer import select_best_moments_with_llm, analyze_audio_energy
from .subtitle_generator import generate_ass_subtitles, SUBTITLE_STYLES, AVAILABLE_FONTS
from .video_editor import (
    process_video_clip,
    compute_title_info,
    TITLE_STYLES,
    TITLE_FONTS,
    mix_background_music,
    is_portrait_video,
)

__all__ = [
    "extract_audio",
    "transcribe_audio",
    "transcribe_audio_cloud",
    "select_best_moments_with_llm",
    "analyze_audio_energy",
    "generate_ass_subtitles",
    "SUBTITLE_STYLES",
    "AVAILABLE_FONTS",
    "process_video_clip",
    "compute_title_info",
    "TITLE_STYLES",
    "TITLE_FONTS",
    "mix_background_music",
    "is_portrait_video",
]
