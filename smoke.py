"""Setup check: makes two fake videos, mosaics one from the other, varispeed-shifts a tone, runs a full remix.
Run: py -3.13 -B smoke.py   -> check out/mosaic.wav, out/octave.wav, out/remix.mp4
"""
import librosa
import numpy as np
import soundfile as sf

from remix import SR, remix
from ytp import grains
from ytp.media import FFMPEG, ROOT, ffmpeg, load_audio

OUT = ROOT / "out"
OUT.mkdir(exist_ok=True)

print("librosa", librosa.__version__, "| ffmpeg", FFMPEG)


def notes(y):
    return librosa.hz_to_midi(librosa.yin(y, fmin=65, fmax=1000, sr=SR))


def miss(a, b):
    """Median gap between two pitch tracks in semitones, ignoring octaves (like the key shifting does)."""
    k = min(len(a), len(b))
    return np.median(np.abs((a[:k] - b[:k] + 6) % 12 - 6))


# video 1: a stepping "melody"; video 2: a chirp sweeping 100 -> 1000 Hz (our "voice")
fakes = {
    "v1.mp4": "sin(2*PI*220*pow(2,floor(t*4)/12)*t)",
    "v2.mp4": "sin(2*PI*(100*t+150*t*t))",
}
for name, expr in fakes.items():
    ffmpeg("-f", "lavfi", "-i", "testsrc=d=3:s=320x240:r=25",
           "-f", "lavfi", "-i", f"aevalsrc='{expr}':s={SR}:d=3",
           "-shortest", OUT / name)
y1, y2 = load_audio(OUT / "v1.mp4", SR), load_audio(OUT / "v2.mp4", SR)

n = grains.grain_len(SR)
idx, shifts = grains.match(grains.describe(y1, SR, n), grains.describe(y2, SR, n), range(-6, 6))
mosaic = grains.resynth(y2, idx, n, shifts)
sf.write(OUT / "mosaic.wav", mosaic, SR)
m = miss(notes(mosaic), notes(y1))
print(f"mosaic: {len(idx)} grains, pitch miss {m:.2f} semitones")
assert m < 1, "matching + key shifting is not following the melody"

tone = np.sin(2 * np.pi * 220 * np.arange(2 * SR) / SR)
k = len(tone) // n
up = grains.resynth(tone, np.arange(k), n, np.full(k, 12))
sf.write(OUT / "octave.wav", up, SR)
hz = np.median(librosa.yin(up[2 * n : -2 * n], fmin=65, fmax=1000, sr=SR))  # edges read past the tone
print(f"varispeed: 220 Hz +12 st -> {hz:.0f} Hz")
assert abs(hz - 440) < 15, "varispeed shift is off"

remix(OUT / "v1.mp4", OUT / "v2.mp4", OUT / "remix.mp4")
yr = load_audio(OUT / "remix.mp4", SR)
m = miss(notes(yr), notes(y1))
print(f"remix: {len(yr) / SR:.2f}s, pitch miss {m:.2f} semitones")
assert m < 1, "remix is not following the melody"

print("all good, go giggle at out/")
