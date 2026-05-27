"""
Build transcript.srt from whisperx audio.json.

- Splits long segments at sentence-final punctuation (。！？!?)
- Uses pyannote speaker labels from audio.json when present (real diarization).
- Falls back to a pause/backchannel heuristic if `speaker` is absent.
- Substitutes SPEAKER_XX with real names from a sibling speakers.md
  (a markdown table whose first two columns are Label + Name).

Usage:
  cd <meeting-folder-with-audio.json>
  python3 /path/to/make_srt.py
  python3 /path/to/make_srt.py --json a.json --speakers s.md --out t.srt
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CWD = Path.cwd()
JSON_PATH = CWD / "audio.json"
SRT_PATH = CWD / "transcript.srt"
SPEAKERS_MD = CWD / "speakers.md"
SPEAKER_LABEL_RE = re.compile(r"^SPEAKER_\d+$")
TBD_VALUES = {"", "_tbd_", "tbd", "n/a", "na", "-", "?", "_?_"}


def load_speaker_map(path: Path = SPEAKERS_MD) -> dict[str, str]:
    """Parse the Mapping table in speakers.md and return {SPEAKER_XX: name}.

    Rules:
      * The file may contain multiple tables that mention SPEAKER labels —
        only the first one assigning a real name to a label wins (later
        tables, e.g. a diarization-summary table whose 2nd column is a
        duration like "1450.7 s", are ignored).
      * A cell that looks like a duration ("123 s", "12.3s") is treated as
        TBD and skipped.
    """
    if not path.exists():
        return {}
    duration_like = re.compile(r"^\d+(?:\.\d+)?\s*s$", re.IGNORECASE)
    mapping: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 2:
            continue
        label, name = cells[0], cells[1]
        if not SPEAKER_LABEL_RE.match(label):
            continue
        # Strip emphasis markup from the name cell.
        name_clean = re.sub(r"[*_`]", "", name).strip()
        if name_clean.lower() in TBD_VALUES or duration_like.match(name_clean):
            continue
        mapping.setdefault(label, name_clean)
    return mapping

PAUSE_TURN_GAP = 1.2  # seconds — pause longer than this hints turn change
BACKCHANNELS = {
    "对", "对对", "对的", "嗯", "嗯嗯", "OK", "ok", "好", "好的",
    "是", "是的", "可以", "懂了", "明白", "哦",
}
SENT_END = re.compile(r"([。！？!?])")

# Whisper-known hallucination patterns during silence (YouTube training data).
HALLUCINATION_PATTERNS = [
    r"请不吝点赞.*?支持明镜与点点栏目?",
    r"请勿模仿。?$",
    r"^HMS物流系统、AB Declaration申报.*UPS等业务术语。?$",
    r"^需求会议：HMS物流系统.*Category A B C。?$",
]
HALLUCINATION_RE = re.compile("|".join(HALLUCINATION_PATTERNS))

# Add a space between a CJK character and an ASCII letter/digit to improve
# readability ("用户story" -> "用户 story", "shipment加A" -> "shipment 加 A").
ASCII_AROUND_CJK = re.compile(
    r"(?<=[一-鿿])(?=[A-Za-z0-9])|(?<=[A-Za-z0-9])(?=[一-鿿])"
)


def fmt_time(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int((t - int(t)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _words_to_sub(words: list[dict], parent: dict) -> dict | None:
    """Build a sub-segment from a list of words, inheriting parent's speaker."""
    if not words:
        return None
    text_part = "".join(w.get("word", "") for w in words).strip()
    if not text_part:
        return None
    # Pick the most common speaker among the words (or fall back to parent).
    word_speakers = [w.get("speaker") for w in words if w.get("speaker")]
    speaker = parent.get("speaker")
    if word_speakers:
        from collections import Counter
        speaker = Counter(word_speakers).most_common(1)[0][0]
    return {
        "start": words[0].get("start", parent["start"]),
        "end": words[-1].get("end", parent["end"]),
        "text": text_part,
        "speaker": speaker,
    }


def split_sentences(seg: dict) -> list[dict]:
    """Split one whisper segment into sentence-level mini-segments, also
    breaking on speaker change inside word-level timestamps."""
    text = seg["text"].strip()
    words = seg.get("words", [])
    if not words:
        return [{
            "start": seg["start"],
            "end": seg["end"],
            "text": text,
            "speaker": seg.get("speaker"),
        }]
    out: list[dict] = []
    cur_words: list[dict] = []
    last_speaker = None
    for w in words:
        w_speaker = w.get("speaker")
        # Flush on speaker change
        if w_speaker and last_speaker and w_speaker != last_speaker:
            sub = _words_to_sub(cur_words, seg)
            if sub:
                out.append(sub)
            cur_words = []
        cur_words.append(w)
        if w_speaker:
            last_speaker = w_speaker
        # Flush on sentence end punctuation
        if SENT_END.search(w.get("word", "")):
            sub = _words_to_sub(cur_words, seg)
            if sub:
                out.append(sub)
            cur_words = []
    sub = _words_to_sub(cur_words, seg)
    if sub:
        out.append(sub)
    if not out:
        return [{
            "start": seg["start"],
            "end": seg["end"],
            "text": text,
            "speaker": seg.get("speaker"),
        }]
    return out


def is_backchannel(text: str) -> bool:
    t = re.sub(r"[，。、,.!?\s]", "", text)
    return t in BACKCHANNELS or (len(t) <= 3 and any(t.startswith(b) for b in BACKCHANNELS))


def label_speakers(segments: list[dict]) -> list[dict]:
    """Heuristic two-speaker labeling.

    Strategy:
      * Default speaker = SPEAKER_00 (the presenter).
      * After a pause >= PAUSE_TURN_GAP or after a question, the next segment
        flips to the other speaker until a clear monologue resumes.
      * Short backchannels (<=3 chars affirmatives) are tagged as the *other*
        speaker (the listener) but do not change the long-running default.
      * Reset to SPEAKER_00 when a long segment (>=15 chars, no question)
        appears — assumed to be the presenter continuing.
    """
    current_main = "SPEAKER_00"
    other = "SPEAKER_01"
    in_qa = False
    last_end = 0.0
    for seg in segments:
        text = seg["text"].strip()
        gap = seg["start"] - last_end
        ends_with_question = bool(re.search(r"[?？]$", text))

        if is_backchannel(text):
            seg["speaker"] = other
        else:
            if (gap >= PAUSE_TURN_GAP and len(text) < 25) or in_qa:
                # Short interjection or follow-up by listener
                seg["speaker"] = other if in_qa else (
                    other if len(text) < 30 else current_main
                )
                # Long sentence after pause = presenter continuing
                if len(text) >= 30 and not ends_with_question:
                    seg["speaker"] = current_main
                    in_qa = False
            else:
                seg["speaker"] = current_main

        # Question mark from main flips into Q&A mode
        if ends_with_question and seg["speaker"] == current_main:
            in_qa = True
        # Long monologue from main exits Q&A
        if not ends_with_question and len(text) >= 40 and seg["speaker"] == current_main:
            in_qa = False
        last_end = seg["end"]
    return segments


def smooth_speakers(
    segs: list[dict],
    *,
    flake_max_dur: float = 2.5,
    flake_max_chars: int = 10,
) -> list[dict]:
    """Reassign isolated short fragments to the surrounding speaker.

    A cue is treated as diarization noise when it is short (<= flake_max_dur s
    and <= flake_max_chars chars) AND the previous and next cues share a
    different speaker. The cue is then snapped to that surrounding speaker.
    """
    if len(segs) < 3:
        return segs
    for i in range(1, len(segs) - 1):
        cur, prev, nxt = segs[i], segs[i - 1], segs[i + 1]
        if prev["speaker"] == nxt["speaker"] != cur["speaker"]:
            dur = cur["end"] - cur["start"]
            if dur <= flake_max_dur and len(cur["text"]) <= flake_max_chars:
                cur["speaker"] = prev["speaker"]
    return segs


def merge_consecutive_same_speaker(
    segs: list[dict],
    *,
    max_gap: float = 1.2,
    max_merged_chars: int = 220,
) -> list[dict]:
    """Merge adjacent cues that share a speaker (and are temporally close)."""
    if not segs:
        return segs
    merged: list[dict] = [segs[0]]
    for s in segs[1:]:
        last = merged[-1]
        same_speaker = s["speaker"] == last["speaker"]
        close = (s["start"] - last["end"]) <= max_gap
        # Don't merge across sentence boundaries when the previous text already
        # ends with a full stop — keeps cues readable as captions.
        prev_ends_sentence = bool(SENT_END.search(last["text"][-1:]))
        room = (len(last["text"]) + len(s["text"])) <= max_merged_chars
        if same_speaker and close and room and not prev_ends_sentence:
            last["end"] = s["end"]
            last["text"] = (last["text"] + s["text"]).strip()
        else:
            merged.append(s)
    return merged


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", type=Path, default=JSON_PATH, help="whisperx JSON output (default: ./audio.json)")
    parser.add_argument("--out", type=Path, default=SRT_PATH, help="SRT output path (default: ./transcript.srt)")
    parser.add_argument("--speakers", type=Path, default=SPEAKERS_MD, help="speakers.md mapping file (default: ./speakers.md)")
    args = parser.parse_args()

    if not args.json.exists():
        parser.error(f"input JSON not found: {args.json}")

    data = json.loads(args.json.read_text())
    raw_segments = data.get("segments", [])

    # Split long segments at sentence + speaker boundaries
    fine: list[dict] = []
    for seg in raw_segments:
        for s in split_sentences(seg):
            text = s["text"].strip()
            if not text:
                continue
            if HALLUCINATION_RE.search(text):
                continue
            s["text"] = ASCII_AROUND_CJK.sub(" ", text)
            fine.append(s)

    # If diarization did not run, fall back to heuristic labeling
    if not any(s.get("speaker") for s in fine):
        fine = label_speakers(fine)
    else:
        # Fill any holes (segments without a speaker) by carrying forward
        last = None
        for s in fine:
            if s.get("speaker"):
                last = s["speaker"]
            elif last:
                s["speaker"] = last
            else:
                s["speaker"] = "SPEAKER_??"
        fine = smooth_speakers(fine)
        fine = merge_consecutive_same_speaker(fine)

    speaker_map = load_speaker_map(args.speakers)
    if speaker_map:
        # After applying real names, two pyannote clusters may collapse onto
        # one person (a known diarization artifact) — re-run the merge so the
        # SRT shows a clean monologue instead of fragmenting on the now-equal
        # speaker boundary.
        for s in fine:
            s["speaker"] = speaker_map.get(s["speaker"], s["speaker"])
        fine = merge_consecutive_same_speaker(fine)

    lines: list[str] = []
    for i, s in enumerate(fine, 1):
        lines.append(str(i))
        lines.append(f"{fmt_time(s['start'])} --> {fmt_time(s['end'])}")
        lines.append(f"[{s['speaker']}] {s['text'].strip()}")
        lines.append("")

    args.out.write_text("\n".join(lines), encoding="utf-8")

    # Print speaker breakdown
    from collections import defaultdict
    dur = defaultdict(float)
    for s in fine:
        dur[s["speaker"]] += s["end"] - s["start"]
    print(f"Wrote {args.out} ({len(fine)} cues)")
    if speaker_map:
        print(f"Applied speaker map: {speaker_map}")
    print("Speaker duration (s):")
    for sp, d in sorted(dur.items(), key=lambda kv: -kv[1]):
        print(f"  {sp}: {d:6.1f}")


if __name__ == "__main__":
    main()
