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


def midi_remix(path, y, sr, n, autotune=True):
    """Play pitched source grains at the MIDI note pitches and timings."""
    import pretty_midi

    pm = pretty_midi.PrettyMIDI(str(path))
    notes = [note for track in pm.instruments if not track.is_drum for note in track.notes]
    if not notes:
        raise ValueError(f"{path} has no pitched notes")

    # YIN always returns a pitch, including for silence and consonants. Rank
    # grains by how well their waveform actually repeats at the estimated pitch.
    samples = y[:len(y) // n * n].reshape(-1, n)
    hz = librosa.yin(y[n // 2:], fmin=65, fmax=1200, sr=sr, frame_length=2048, hop_length=n)
    periods = sr / hz[:len(samples)]
    quality = np.zeros(len(samples))
    for i, (sample, period) in enumerate(zip(samples, periods)):
        lag = round(period)
        if 2 * period > n - 1:
            continue
        a, b = sample[:-lag], sample[lag:]
        energy = np.dot(a, a) + np.dot(b, b)
        if energy > 0:
            quality[i] = max(0, 2 * np.dot(a, b) / energy) * min(1, np.sqrt(energy / (2 * len(a))) / 0.03)
    voiced = np.flatnonzero(quality >= 0.35)
    if not len(voiced):
        raise ValueError("Source audio has no clearly voiced grains for MIDI")

    pitches = librosa.hz_to_midi(hz[voiced])
    selected = {}
    for pitch in {note.pitch for note in notes}:
        distance = np.abs(pitches - pitch)
        cost = distance * (0.04 if autotune else 1.0) + (1 - quality[voiced])
        best = np.argmin(cost)
        selected[pitch] = voiced[best], 2 ** ((pitch - pitches[best]) / 12) if autotune else 1.0

    duration = max(1, round(pm.get_end_time() * sr))
    mix = np.zeros(duration)
    idx = np.full((duration + n - 1) // n, -1, dtype=int)
    prominence = np.zeros(len(idx))
    for note in notes:
        start, end = round(note.start * sr), round(note.end * sr)
        if end <= start:
            continue
        j, speed = selected[note.pitch]
        sample, period = samples[j], periods[j]
        # Loop at a whole number of periods. Blend one period across the seam
        # to keep waveform changes in the original speech from creating clicks.
        loop = (int((n - 1) / period) - 1) * period
        pos = (np.arange(end - start) * speed) % loop
        grid = np.arange(n)
        signal = np.interp(pos, grid, sample)
        blend = pos < period
        weight = pos[blend] / period
        signal[blend] = weight * signal[blend] + (1 - weight) * np.interp(pos[blend] + loop, grid, sample)
        # Different vowels can have very different levels. Give MIDI velocity
        # a consistent starting level while limiting gain on quiet samples.
        rms = np.sqrt(np.mean(signal ** 2))
        signal *= min(3.0, 0.12 / max(rms, 1e-6))
        fade = min(round(sr * 0.005), len(signal) // 2)
        if fade:
            ramp = np.linspace(0, 1, fade, endpoint=False)
            signal[:fade] *= ramp
            signal[-fade:] *= ramp[::-1]
        mix[start:end] += signal * (note.velocity / 127)

        cells = np.arange(start // n, (end - 1) // n + 1)
        weight = note.velocity * (np.minimum(end, (cells + 1) * n) - np.maximum(start, cells * n))
        update = weight > prominence[cells]
        idx[cells[update]] = j
        prominence[cells[update]] = weight[update]

    # During rests, keep showing the most recent source grain.
    active = np.where(idx >= 0, np.arange(len(idx)), 0)
    idx[0] = max(0, idx[0])
    return mix, idx[np.maximum.accumulate(active)]


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


def follow_dynamics(mix, target, sr):
    """Follow the target's short-time loudness with smoothly changing gain."""
    hop = max(1, round(sr * 0.01))
    starts = np.arange(0, len(mix), hop)
    lengths = np.minimum(hop, len(mix) - starts)
    def rms(signal):
        power = np.add.reduceat(np.square(signal[:len(mix)], dtype=float), starts)
        return np.sqrt(power / lengths)

    gain = np.minimum(3.0, rms(target) / np.maximum(rms(mix), 1e-6))
    centers = starts + (lengths - 1) / 2
    return mix * np.interp(np.arange(len(mix)), centers, gain)
