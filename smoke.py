"""Setup check: makes two fake videos, mosaics one from the other, pitch-shifts a tone.
Run: py -3.13 -B smoke.py   -> listen to out/mosaic.wav and out/octave.wav
"""
import librosa
import numpy as np
import parselmouth
import soundfile as sf

from ytp import grains, pitch
from ytp.media import FFMPEG, ROOT, extract_audio, ffmpeg

SR = 22050
OUT = ROOT / "out"
OUT.mkdir(exist_ok=True)

print("librosa", librosa.__version__, "| parselmouth", parselmouth.VERSION, "| ffmpeg", FFMPEG)

# video 1: a stepping "melody"; video 2: a chirp sweeping 100 -> 1000 Hz (our "voice")
fakes = {
    "v1.mp4": "sin(2*PI*220*pow(2,floor(t*4)/12)*t)",
    "v2.mp4": "sin(2*PI*(100*t+150*t*t))",
}
for name, expr in fakes.items():
    ffmpeg("-f", "lavfi", "-i", "testsrc=d=3:s=320x240:r=25",
           "-f", "lavfi", "-i", f"aevalsrc='{expr}':s={SR}:d=3",
           "-shortest", OUT / name)
    extract_audio(OUT / name, OUT / name.replace(".mp4", ".wav"), SR)

y1, _ = librosa.load(OUT / "v1.wav", sr=SR)
y2, _ = librosa.load(OUT / "v2.wav", sr=SR)

n = grains.grain_len(SR)
f1, f2 = grains.describe(y1, SR, n), grains.describe(y2, SR, n)
idx = grains.match(f1, f2)
sf.write(OUT / "mosaic.wav", grains.chop(y2, n)[idx].ravel(), SR)

off = np.median(np.abs(f1[:, 0] - f2[idx, 0]))
print(f"mosaic: {len(idx)} grains, median pitch miss {off:.2f} semitones")
assert off < 2, "grain matching is not following the melody"

tone = np.sin(2 * np.pi * 220 * np.arange(SR) / SR)
up = pitch.shift(tone, SR, 12)
sf.write(OUT / "octave.wav", up, SR)
hz = np.median(librosa.yin(up, fmin=65, fmax=1000, sr=SR))
print(f"PSOLA: 220 Hz +12 st -> {hz:.0f} Hz")
assert abs(hz - 440) < 15, "PSOLA shift is off"

print("all good, go giggle at out/")
