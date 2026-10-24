"""ffmpeg helpers. Prefers the bundled ./ffmpeg/bin, falls back to PATH."""
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_LOCAL = ROOT / "ffmpeg" / "bin" / "ffmpeg.exe"
FFMPEG = str(_LOCAL) if _LOCAL.exists() else shutil.which("ffmpeg")


def ffmpeg(*args):
    if not FFMPEG:
        raise FileNotFoundError("ffmpeg not found: put it in ./ffmpeg/bin or on PATH")
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", *map(str, args)], check=True)


def extract_audio(video, wav, sr=22050):
    ffmpeg("-i", video, "-vn", "-ac", 1, "-ar", sr, wav)
