# Speaker Identification — <meeting-title> (<YYYY-MM-DD>)

> **How to use**
>
> 1. After running whisperx with `--diarize`, look at the `speaker` field of
>    each segment in `audio.json` and fill in the Mapping table below with
>    every `SPEAKER_XX` produced.
> 2. For each label, pick a moment when only that speaker is talking and
>    extract a video frame:
>
>    ```bash
>    ffmpeg -ss <seconds> -i meeting.mp4 -frames:v 1 -q:v 2 spk_<label>_<mmss>.jpg
>    ```
>
>    Open the JPG. The Teams / Zoom active-speaker banner (bottom-left text)
>    and the highlighted gallery tile reveal the real name.
> 3. Fill in the `Name` column with the real name. Keep `_TBD_` for unknown.
> 4. Re-run `python3 /path/to/make_srt.py` — the `transcript.srt` will use
>    real names instead of `SPEAKER_XX`.
> 5. Promote any newly identified person to the cross-meeting roster at
>    `../roster.md` (one level up from this meeting folder).

---

## Mapping (edit me)

| Label      | Name   | Role | Notes |
| ---------- | ------ | ---- | ----- |
| SPEAKER_00 | _TBD_  |      |       |
| SPEAKER_01 | _TBD_  |      |       |
| SPEAKER_02 | _TBD_  |      |       |

> `make_srt.py` only takes the **first two columns** (Label, Name). The Role
> and Notes columns are for humans. Rows where Name is `_TBD_`, blank, or a
> dash are left as the raw `SPEAKER_XX` label in the SRT.

---

## Diarization summary

> Useful for picking which label to chase first (the longest one is usually
> the presenter; very short ones are often diarization noise).

| Label      | Duration | Turns | First seen | Mapped to |
| ---------- | -------- | ----- | ---------- | --------- |
| SPEAKER_00 |          |       |            |           |
| SPEAKER_01 |          |       |            |           |

---

## Names mentioned inside the meeting (candidates)

Names spoken aloud during the recording often hint at who's who:

| Name | When spoken | By whom | Context |
| --- | --- | --- | --- |

---

## Frame evidence (optional)

For each label, record the timestamp(s) you sampled and which avatar was
highlighted. This makes it easy to revisit the decision later.

| Label      | Frame timestamp | Highlighted avatar | File |
| ---------- | --------------- | ------------------ | ---- |
| SPEAKER_00 |                 |                    |      |
