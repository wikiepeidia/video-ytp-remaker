"""PSOLA pitch shifting through Praat (keeps duration and formants)."""
import parselmouth
from parselmouth.praat import call


def shift(y, sr, semitones):
    snd = parselmouth.Sound(y, sampling_frequency=sr)
    manip = call(snd, "To Manipulation", 0.01, 65, 1000)
    tier = call(manip, "Extract pitch tier")
    call(tier, "Multiply frequencies", snd.xmin, snd.xmax, 2 ** (semitones / 12))
    call([tier, manip], "Replace pitch tier")
    return call(manip, "Get resynthesis (overlap-add)").values[0]
