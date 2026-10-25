"""Rebuild video 1's audio out of video 2's grains (key-shifted to fit), over video 2's matching frames.
Usage: py -3.13 -B remix.py target.mp4 source.mp4 [out.mp4] [--ms 60] [--no-autotune]
"""
import argparse
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import soundfile as sf

from ytp import grains
from ytp.media import ROOT, cut_video, dump_frames, load_audio

SR = 44100
FPS = 25


def remix(target, source, out, ms=60, autotune=True):
    n = grains.grain_len(SR, ms)
    with tempfile.TemporaryDirectory() as tmp, ThreadPoolExecutor() as pool:
        frames = pool.submit(dump_frames, source, tmp, FPS)  # decode video 2 while the audio work runs
        y1, y2 = pool.map(load_audio, (target, source), (SR, SR))
        for y, video in ((y1, target), (y2, source)):
            if len(y) < 4 * n:
                raise ValueError(f"{video} has too little audio")

        f1, f2 = pool.map(grains.describe, (y1, y2), (SR, SR), (n, n))
        idx, shifts = grains.match(f1, f2, range(-6, 6) if autotune else (0,))
        mix = grains.resynth(y2, idx, n, shifts)
        sf.write(Path(tmp) / "mix.wav", mix / max(1, np.abs(mix).max()), SR)
        cut_video(tmp, frames.result(), idx, n / SR, Path(tmp) / "mix.wav", out, FPS)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("target", help="audio or video whose rhythm and melody you keep")
    p.add_argument("source", help="video whose sound and frames get chopped up")
    p.add_argument("out", nargs="?", default=ROOT / "out" / "remix.mp4")
    p.add_argument("--ms", type=int, default=60, help="grain length in ms (try 30-1000)")
    p.add_argument("--no-autotune", dest="autotune", action="store_false", help="no key shifting")
    a = p.parse_args()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    remix(a.target, a.source, a.out, a.ms, a.autotune)
    print("wrote", a.out)
