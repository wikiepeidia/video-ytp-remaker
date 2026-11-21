# Video YTP Remaker

Play a song using sounds from a video. Give the remixer a MIDI file and a clip of someone talking, and it turns pieces of their voice into the notes of the song. Each cut shows the moment in the source video where that sound came from.

## Demo

[![Watch the Soviet Anthem remix demo on YouTube](https://i.ytimg.com/vi/cyq4xl-GyiE/hqdefault.jpg)](https://youtu.be/cyq4xl-GyiE)

[Watch the demo on YouTube ↗](https://youtu.be/cyq4xl-GyiE)

## Make a remix

**Use MIDI as the target for the clearest melody.** The file gives the remixer the exact pitches, octaves, timing, rests, and chords. A single melody track makes one voice sing the tune. A score with several pitched parts layers those voices together.

Looking for a tune? Browse [scores on MuseScore](https://musescore.com/sheetmusic) or try [my MuseScore collection](https://musescore.com/affsuzukicup_com). Save a MIDI version of the score you want to remix.

Install Python 3.13 and put FFmpeg in `ffmpeg/bin` or on your `PATH`. From the project folder, run:

```sh
py -3.13 -m pip install -r requirements.txt
py -3.13 -B remix.py "path/to/tune.mid" clips/speech.mp4 out/remix.mp4
```

The first input supplies the **song**. The second supplies the **sound and footage**. For speech, try a varied monologue with clear vowels. The result is an MP4 with a 720-pixel short edge.

## Remix a recording

You can also use an audio or video recording as the target. The remixer matches short slices by pitch class and tone color, then shifts and joins pieces of the source clip. This mode follows the recording’s loudness, but a dense mix can make the melody harder to pick out.

```sh
py -3.13 -B remix.py clips/song.mp4 clips/speech.mp4 out/remix.mp4
```

| Option | What it changes |
| --- | --- |
| `--ms 60` | Sets the source grain length in milliseconds. Try 30–1000. Longer grains keep more of the original syllable. |
| `--no-autotune` | Keeps source grains at their recorded pitch. |

MIDI playback skips drums, instrument sounds, pitch bends, and sustain pedal. To check your setup, run `py -3.13 -B smoke.py` and look in `out/` for the test renders.
