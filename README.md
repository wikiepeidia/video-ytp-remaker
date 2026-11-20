# video-ytp-remaker

making another video has the same source as the 1st to see what happen

Audio mosaicing: rebuilds video 1's audio from 60 ms grains of video 2's sound,
matched on notes (chroma) and timbre, each grain sped up or slowed down (up to ±6 semitones,
chipmunk-style) to land on video 1's notes, and shows video 2's matching frames. Works on full songs.

```sh
py -3.13 -m pip install -r requirements.txt   # ffmpeg goes in ./ffmpeg/bin or on PATH
py -3.13 -B smoke.py                          # setup check, writes test files to out/
py -3.13 -B remix.py clips/song.mp4 clips/speech.mp4 out/remix.mp4
py -3.13 -B remix.py "path/to/tune.mid" clips/speech.mp4 out/remix.mp4   # MIDI as the melody
```

Knobs: `--ms 30..1000` (grain size: small = autotune mush, big = sentence mixing), `--no-autotune` (no key shifting).
Best results when video 2 is long and varied (a monologue beats 10 s of one vowel).

With a MIDI target, the remix plays voiced grains from the source video at the
written pitches and octaves. It keeps note timing, rests, and chords. MIDI drum
tracks, instrument sounds, pitch bends, and sustain pedal are skipped. Use a
MIDI with just the melody track if you want a single voice. Clear, sustained
vowels work well as the source. For a remix that follows the sound of the
original recording, use that recording as the target.
