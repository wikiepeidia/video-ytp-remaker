"""Chop audio into grains, describe them, match target grains to source grains."""
import librosa
import numpy as np
from scipy.signal import get_window
from scipy.spatial import cKDTree


def grain_len(sr, ms=60):
    return int(sr * ms / 1000)


def describe(y, sr, n):
    """One row per grain of n samples: 12 chroma bins (which notes sound), then 13 MFCCs (timbre, loudness)."""
    h = min(512, n)
    # tuning=0: per-signal tuning guesses can land a bin apart and make every note match the wrong one
    chroma = librosa.feature.chroma_stft(y=y, sr=sr, n_fft=4096, hop_length=h, tuning=0.0)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=h)
    frames = np.vstack([chroma, mfcc]).T
    k = len(y) // n
    g = np.arange(len(frames)) * h // n  # grain each analysis frame falls in
    keep = g < k
    sums = np.zeros((k, frames.shape[1]))
    np.add.at(sums, g[keep], frames[keep])
    return sums / np.bincount(g[keep], minlength=k)[:, None]


def match(target, source, shifts=(0,)):
    """Closest source grain for every target grain, plus the semitone shift that makes it fit.
    Each shift rolls the source chroma, so a grain can match a note it only reaches after transposing."""
    variants = np.vstack([np.column_stack([np.roll(source[:, :12], s, axis=1), source[:, 12:]]) for s in shifts])
    mu = variants.mean(0)
    # notes weigh 3x timbre: on two real songs this lifted note fit from 0.93 to 0.96 (random grains: 0.68)
    scale = np.r_[np.full(12, 3.0), np.ones(variants.shape[1] - 12)] / (variants.std(0) + 1e-9)
    hit = cKDTree((variants - mu) * scale).query((target - mu) * scale, workers=-1)[1]
    return hit % len(source), np.asarray(shifts)[hit // len(source)]


def resynth(y, idx, n, shifts):
    """Join source grains idx with short crossfades, each varispeed-shifted by shifts semitones."""
    # short fades, not 50% overlap: a grain repeated back to back would otherwise phase-cancel into mush
    f = n // 6
    m = n + f
    win = get_window(("tukey", 2 * f / m), m, fftbins=False)
    y = np.asarray(y, dtype=float)  # np.interp would otherwise re-convert the whole song on every grain
    t = np.arange(len(y), dtype=float)
    out = np.zeros(len(idx) * n + m)
    for i, (j, s) in enumerate(zip(idx, shifts)):
        # shortcut: linear interpolation aliases a bit on big upward shifts; resample with soxr if it sounds harsh
        pos = j * n + n / 2 + (np.arange(m) - m / 2) * 2 ** (s / 12)  # read faster = higher pitch
        out[i * n : i * n + m] += np.interp(pos, t, y, left=0, right=0) * win
    return out[f // 2 : f // 2 + len(idx) * n]
