"""Chop audio into grains, describe them, match target grains to source grains."""
import librosa
import numpy as np
from scipy.spatial import cKDTree


def grain_len(sr, ms=60):
    return int(sr * ms / 1000)


def chop(y, n):
    return y[: len(y) // n * n].reshape(-1, n)


def describe(y, sr, n):
    """One row per grain of n samples: [midi pitch, loudness dB, 13 MFCCs]."""
    k = len(y) // n
    y = y[n // 2 :]  # shift so each centered analysis frame sits on a grain's middle
    f0 = librosa.yin(y, fmin=65, fmax=1000, sr=sr, frame_length=2048, hop_length=n)[:k]
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=n)[0, :k]
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=n)[:, :k]
    return np.column_stack([librosa.hz_to_midi(f0), librosa.amplitude_to_db(rms), mfcc.T])


def match(target, source):
    """Index of the closest-sounding source grain for every target grain."""
    mu, sd = source.mean(0), source.std(0) + 1e-9
    return cKDTree((source - mu) / sd).query((target - mu) / sd)[1]
