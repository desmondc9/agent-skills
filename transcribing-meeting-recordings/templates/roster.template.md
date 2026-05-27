# Meeting Roster

The master list of people who appear in meeting recordings under this folder.

**Why this file exists:** pyannote diarization labels (`SPEAKER_00`, `SPEAKER_01`, …)
are **not stable across recordings** — the same person gets a different label
in every file. This roster is what carries identity across recordings.

## How to maintain

1. After mapping a new meeting in its own `speakers.md`, copy each
   newly identified person into the table below.
2. Keep names **canonical** (write `Junwei Nie` the same way every time — the
   SRT generator does a literal text substitution).
3. Track aliases — including whisper transcription errors when a Chinese name
   was heard as a homophone (e.g., 训维 vs Junwei).

---

## Known people

| Name | Role / Team | Aliases | Meetings (label) | Notes |
| --- | --- | --- | --- | --- |

---

## Meetings index

| Date       | Meeting | Per-meeting mapping |
| ---------- | ------- | ------------------- |

---

## Background

- pyannote does *unsupervised* speaker clustering per recording. Voice
  embeddings are not persisted, so `SPEAKER_01` in one meeting is
  unrelated to `SPEAKER_01` in another.
- Within one recording, labels ARE consistent — so a single SRT cue stays
  attached to the same physical voice for the whole file.
- pyannote sometimes **over-segments** one voice into 2+ clusters (different
  mic proximity, intonation shifts between explanation vs. question).
  Map both labels to the same canonical name in the per-meeting mapping
  and `make_srt.py` will merge their cues.
