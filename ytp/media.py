"""ffmpeg helpers. Prefers the bundled ./ffmpeg/bin, falls back to PATH."""
import shutil
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
_LOCAL = ROOT / "ffmpeg" / "bin" / "ffmpeg.exe"
FFMPEG = str(_LOCAL) if _LOCAL.exists() else shutil.which("ffmpeg")


def ffmpeg(*args):
    if not FFMPEG:
        raise FileNotFoundError("ffmpeg not found: put it in ./ffmpeg/bin or on PATH")
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", *map(str, args)]
    return subprocess.run(cmd, check=True, stdout=subprocess.PIPE).stdout


def load_audio(path, sr):
    """Mono float32 samples of any audio or video file."""
    return np.frombuffer(ffmpeg("-i", path, "-vn", "-ac", 1, "-ar", sr, "-f", "f32le", "-"), np.float32)


def dump_frames(video, folder, fps):
    """Extract frames with a 720-pixel short edge, preserving orientation."""
    # shortcut: writes all source frames to temp disk; fine for clips of a few minutes
    scale = "scale=w='if(gte(iw,ih),-2,720)':h='if(gte(iw,ih),720,-2)':flags=lanczos"
    ffmpeg("-i", video, "-vf", f"fps={fps},{scale}", "-q:v", 2, Path(folder) / "%06d.jpg")
    count = len(list(Path(folder).glob("*.jpg")))
    if not count:
        raise ValueError(f"no video frames in {video}")
    return count


def cut_video(folder, count, idx, grain_s, audio, out, fps):
    """Under the new audio, show the dumped frames each chosen grain came from."""
    names = []
    for k in range(int(len(idx) * grain_s * fps)):
        t = k / fps
        i = min(int(t / grain_s), len(idx) - 1)
        frame = round((idx[i] * grain_s + t - i * grain_s) * fps)
        names.append(f"{min(frame, count - 1) + 1:06d}.jpg")
    names.append(names[-1])  # concat demuxer ignores the last entry's duration
    (Path(folder) / "frames.txt").write_text("".join(f"file '{f}'\nduration {1 / fps}\n" for f in names))
    inputs = ("-f", "concat", "-i", Path(folder) / "frames.txt", "-i", audio, "-r", fps)
    output = ("-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", out)
    for encoder, options in (("h264_nvenc", ("-preset", "p4", "-cq", 20)),
                             ("h264_qsv", ("-global_quality", 20)),
                             ("h264_amf", ("-rc", "cqp", "-qp_i", 20, "-qp_p", 20))):
        try:
            ffmpeg(*inputs, "-c:v", encoder, *options, *output)
            print(f"Encoded video with {encoder}")
            return
        except subprocess.CalledProcessError:
            continue
    ffmpeg(*inputs, "-c:v", "libx264", "-preset", "veryfast", "-crf", 20, *output)
