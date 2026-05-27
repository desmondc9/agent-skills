---
name: transcribing-meeting-recordings
description: "Use when converting a meeting recording (mp4/mov/m4a/wav audio or video) into a timestamped SRT/VTT transcript, especially Chinese or multilingual audio. Triggers include 'transcribe this meeting', 'generate captions', 'convert recording to subtitles', '生成字幕', '会议转文字', 'speaker labels', 'who said what', or requests for SRT/transcript files. Supports automatic speaker identification via pyannote diarization combined with video-frame analysis of Microsoft Teams or Zoom active-speaker highlighting to map anonymized SPEAKER_XX clusters onto real participant names. Do NOT use for live/streaming transcription, lecture summarization without a transcript artifact, or text-to-speech."
---

# Transcribing Meeting Recordings (with Speaker Identification)

## Overview

End-to-end pipeline: video/audio file → cleaned SRT transcript with timestamps and **real participant names**. Uses **whisperx** (faster-whisper + alignment + pyannote diarization) for ASR + speaker clustering, plus a Microsoft Teams / Zoom **video-frame trick** to map anonymized `SPEAKER_XX` clusters onto real names.

## When to Use

- User provides a meeting recording (`.mp4` / `.mov` / `.mkv` / `.wav` / `.m4a` / `.mp3`) and wants a transcript with timestamps.
- User asks for SRT/VTT subtitles, captions, 字幕, or "transcript with speaker labels".
- Multilingual content (especially Chinese with English technical terms mixed in — whisper large-v3 handles this well with the right prompt).
- User wants to know **who said what** in a meeting, not just the words.

**Do NOT use for:**

- Live / real-time / streaming transcription — whisperx is batch-only.
- Summarization without producing a transcript artifact.
- Audio-only files where speaker identification doesn't matter — then skip diarization and the Teams-frame step.

## Quick Reference

| Stage                          | Command                                                                                  |
| ------------------------------ | ---------------------------------------------------------------------------------------- |
| 1. Extract WAV                 | `ffmpeg -i in.mp4 -vn -ac 1 -ar 16000 -c:a pcm_s16le audio.wav`                          |
| 2. Transcribe + diarize        | `whisperx audio.wav --model large-v3 --language zh --diarize …` (see Implementation)     |
| 3. Clean + map names           | `python3 scripts/make_srt.py` (reads `./audio.json` + `./speakers.md` from CWD)          |
| 4. (Optional) Identify speakers | `ffmpeg -ss <t> -i in.mp4 -frames:v 1 spk_XX.jpg` — read Teams banner → fill speakers.md |

## Prerequisites (one-time setup)

```bash
# 1. ffmpeg installed system-wide
which ffmpeg || sudo apt install ffmpeg

# 2. whisperx — REQUIRES Python 3.11
#    (Python 3.14 ships a torchaudio that removed list_audio_backends → pyannote crashes)
uv tool install whisperx --python 3.11

# 3. Accept ALL THREE pyannote gated repos on huggingface.co (just click "Agree"):
#      https://huggingface.co/pyannote/speaker-diarization-3.1
#      https://huggingface.co/pyannote/segmentation-3.0
#      https://huggingface.co/pyannote/speaker-diarization-community-1
#    Then ensure HF_TOKEN is in ~/.cache/huggingface/token:
huggingface-cli login   # only needed once
```

## Implementation

### Step 1 — Extract 16 kHz mono WAV

Whisper is trained on 16 kHz mono; matching that format avoids resampling cost.

```bash
ffmpeg -y -i meeting.mp4 -vn -ac 1 -ar 16000 -c:a pcm_s16le audio.wav
```

### Step 2 — Run whisperx (transcribe + align + diarize)

Tune for your GPU. **For 8 GB VRAM** (e.g., RTX 4060) use `--compute_type int8 --batch_size 4` — at the default `batch_size 8` `large-v3` + diarization OOMs around 70 % progress:

```bash
whisperx audio.wav \
  --model large-v3 \
  --language zh \
  --device cuda \
  --compute_type int8 \
  --batch_size 4 \
  --diarize \
  --diarize_model pyannote/speaker-diarization-3.1 \
  --min_speakers 2 --max_speakers 8 \
  --output_format srt --output_format json \
  --output_dir . \
  --condition_on_previous_text False \
  --initial_prompt "domain terminology hint, e.g. 物流系统, AB Declaration, shipment, MAWB"
```

This produces:

- `audio.json` — word-level timestamps + `speaker` field on every segment.
- `audio.srt` — basic SRT (may be missing if writing fails; we regenerate it in step 3 anyway).

> The `--initial_prompt` gives whisper context for technical/domain words it would otherwise mis-transcribe. Always pass one for technical meetings.

> If diarization fails with `403 Client Error: Forbidden`, you haven't accepted all three pyannote licenses — see Prerequisites.

### Step 3 — Clean + (optionally) map names

The bundled `scripts/make_srt.py` reads `./audio.json` from the current directory and writes `./transcript.srt`. It:

1. Splits long whisper segments at sentence-final punctuation **and** at speaker-change boundaries from pyannote.
2. Strips known Whisper YouTube-training hallucinations (`请不吝点赞订阅...`, `请勿模仿`, etc.).
3. Inserts a space between CJK and ASCII characters (`shipment加A` → `shipment 加 A`) for readability.
4. **Smooths diarization noise** — cues shorter than 2.5 s + 10 chars sandwiched between two same-speaker neighbours get snapped to the surrounding speaker.
5. **Merges consecutive same-speaker cues** that are close in time and don't cross sentence boundaries.
6. **Substitutes `SPEAKER_XX` with real names** read from a sibling `speakers.md` table (see step 4).

```bash
cd <meeting-folder-with-audio.json>
cp <skill>/templates/speakers.template.md ./speakers.md  # first time only
python3 <skill>/scripts/make_srt.py
# → wrote transcript.srt (NN cues)
# → speaker durations printed to stdout
```

### Step 4 — Speaker identification via Teams/Zoom video frames (novel technique)

> Microsoft Teams and Zoom both show the **active speaker's name** in a bottom-left banner *and* highlight their gallery tile with a coloured ring / brighter border. This makes label → name mapping a simple visual check.

For every `SPEAKER_XX` produced by step 2:

1. From the SRT, pick a timestamp **3–5 seconds into a clean monologue** (avoid speaker-change boundaries — the Teams banner has ~1-2 s lag).
2. Extract the frame:

   ```bash
   ffmpeg -ss <seconds> -i meeting.mp4 -frames:v 1 -q:v 2 spk_<label>_<mmss>.jpg
   ```

3. Open the JPG and identify which avatar is highlighted (the bottom-left name banner is the surest signal).
4. Fill in the Mapping table in `speakers.md`:

   ```markdown
   | Label      | Name        | Role  | Notes                                |
   | ---------- | ----------- | ----- | ------------------------------------ |
   | SPEAKER_03 | Junwei Nie  | Dev   | confirmed at 07:25 — JN tile lit     |
   ```

5. Re-run `python3 scripts/make_srt.py` — the SRT now carries real names.

**Critical tip — pyannote over-segmentation.** It is common for *one* physical speaker to be split across 2+ `SPEAKER_XX` clusters (different mic proximity, varying intonation between explanations vs. questions, etc.). Verify by frame-checking each label; map all of them to the same canonical name in `speakers.md` and `make_srt.py` will merge their cues automatically.

**Cross-meeting tracking.** Keep a roster at the **parent folder** of all meeting recordings (use `templates/roster.template.md`). Each new meeting's per-meeting `speakers.md` gets summarised into one row per person on the parent roster, with their alias list (including Whisper homophones — e.g., `训维` for `Junwei`).

## Common Mistakes

| Symptom                                                                       | Cause                                                       | Fix                                                                              |
| ----------------------------------------------------------------------------- | ----------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `AttributeError: module 'torchaudio' has no attribute 'list_audio_backends'`  | Python 3.14 ships an incompatible torchaudio version        | `uv tool uninstall whisperx && uv tool install whisperx --python 3.11`           |
| `GatedRepoError: 403 — Cannot access gated repo`                              | One of the 3 pyannote licenses isn't accepted               | Visit each of the 3 URLs in Prerequisites and click *Agree and access*           |
| `RuntimeError: CUDA out of memory` around 50–70 % progress                    | `large-v3` + diarization peaks > 8 GB at `batch_size 8`     | Use `--compute_type int8 --batch_size 4` (or 2 for 6 GB cards)                   |
| Transcript contains `请不吝点赞订阅转发打赏...`                                 | Whisper hallucination during silent gaps (YouTube training) | `make_srt.py` strips these; also pass `--condition_on_previous_text False`       |
| One person split across 2+ `SPEAKER_XX` labels                                 | pyannote diarization over-segmentation                      | Map all their labels to the same name in `speakers.md`; cues will merge          |
| `audio.srt` is missing but `audio.json` is present                            | Whisperx wrote JSON then failed during SRT serialization    | Run `make_srt.py` — it generates the SRT from JSON                               |
| Chinese transcription is poor or drops English technical terms                 | Default `--model small` or no language hint                 | Always `--model large-v3 --language <iso>` and pass an `--initial_prompt`        |
| `make_srt.py` reads the wrong column as Name (e.g., grabs a duration "100 s") | `speakers.md` has multiple tables that contain SPEAKER rows | The script already prefers the *first* match per label and rejects `\d+(\.\d+)?\s*s$` |
| Teams frame at speaker-change boundary shows wrong avatar                     | Banner has ~1-2 s lag after voice transition                | Sample frames mid-utterance, not at cue boundaries                               |

## Bundled Files

```
transcribing-meeting-recordings/
├── SKILL.md                         ← this file
├── scripts/
│   └── make_srt.py                  ← cleaner + name-substituter (CWD-driven)
└── templates/
    ├── speakers.template.md         ← per-meeting label→name table
    └── roster.template.md           ← cross-meeting participant roster
```

## Real-World Impact

A 34-minute Chinese requirements-walkthrough meeting (10 Teams participants) was processed end-to-end in:

- ~2 min — audio extraction + whisperx transcription + alignment + diarization on RTX 4060 8 GB (int8 / batch 4).
- ~5 min — visual identification of 4 actual speakers from 6 pyannote clusters via 10 Teams screenshots.
- Output: 202-cue SRT carrying real names (Zhujun Hu, Junwei Nie, Denny Huang, Macklin Feng).

Every failure mode in the Common Mistakes table above was actually hit and resolved during that exercise — Python 3.14 incompatibility, two rounds of HF license acceptance, OOM at default batch size, YouTube hallucination, English-word concatenation, and pyannote splitting two of the four participants into two clusters each.
