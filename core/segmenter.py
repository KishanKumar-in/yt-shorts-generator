"""Decide where to cut clips from the transcript.

Two modes:
  - "simple": evenly split the video into <=max_len chunks, snapped to
    sentence boundaries, covering the whole video in order.
  - "smart":  score sentence-grouped candidate windows by simple, local
    heuristics (no paid API needed) and keep the best non-overlapping ones.
"""
import re

SENTENCE_END = re.compile(r"[.!?]\s*$")


def _build_sentences(whisper_result: dict) -> list:
    """Group whisper segments into sentences with start/end/text/word list."""
    sentences = []
    cur_words = []
    cur_start = None

    for seg in whisper_result.get("segments", []):
        for w in seg.get("words", []):
            word_text = w["word"]
            if cur_start is None:
                cur_start = w["start"]
            cur_words.append(w)
            if SENTENCE_END.search(word_text.strip()):
                sentences.append({
                    "start": cur_start,
                    "end": w["end"],
                    "text": "".join(x["word"] for x in cur_words).strip(),
                    "words": cur_words,
                })
                cur_words = []
                cur_start = None

    if cur_words:
        sentences.append({
            "start": cur_start,
            "end": cur_words[-1]["end"],
            "text": "".join(x["word"] for x in cur_words).strip(),
            "words": cur_words,
        })
    return sentences


def suggest_clip_count(duration_sec: float) -> int:
    """~1 clip per ~65-70s of source, so a 10 min video -> ~8-9 clips."""
    return max(1, round(duration_sec / 67))


def simple_segments(whisper_result: dict, max_len: float = 58.0, target_count: int = None) -> list:
    """Walk through sentences in order, packing them into <=max_len chunks."""
    sentences = _build_sentences(whisper_result)
    if not sentences:
        return []

    clips = []
    chunk = []
    chunk_start = sentences[0]["start"]

    for sent in sentences:
        would_be_len = sent["end"] - chunk_start
        if chunk and would_be_len > max_len:
            clips.append({"start": chunk_start, "end": chunk[-1]["end"],
                          "text": " ".join(s["text"] for s in chunk)})
            chunk = []
            chunk_start = sent["start"]
        chunk.append(sent)

    if chunk:
        clips.append({"start": chunk_start, "end": chunk[-1]["end"],
                      "text": " ".join(s["text"] for s in chunk)})

    if target_count and len(clips) > target_count:
        clips = clips[:target_count]
    return clips


_ENGAGING_MARKERS = ["!", "?", "never", "always", "secret", "mistake", "best",
                      "worst", "biggest", "important", "amazing", "crazy",
                      "here's", "because", "so", "actually", "truth", "wrong",
                      "right", "you need", "you have to", "stop", "why"]


def _score_window(text: str, dur: float) -> float:
    t = text.lower()
    score = 0.0
    for m in _ENGAGING_MARKERS:
        score += t.count(m) * 1.5
    score += text.count("!") * 2 + text.count("?") * 2
    # prefer windows that use most of the available time (not tiny fragments)
    score += min(dur, 55) / 55 * 2
    # mild penalty for very short/low-content windows
    words = len(t.split())
    if words < 8:
        score -= 3
    return score


def smart_segments(whisper_result: dict, target_count: int, max_len: float = 58.0) -> list:
    """Score sliding sentence-windows and greedily keep the best non-overlapping ones."""
    sentences = _build_sentences(whisper_result)
    if not sentences:
        return []

    candidates = []
    n = len(sentences)
    for i in range(n):
        acc_text = []
        start = sentences[i]["start"]
        for j in range(i, n):
            end = sentences[j]["end"]
            dur = end - start
            if dur > max_len:
                break
            acc_text.append(sentences[j]["text"])
            text = " ".join(acc_text)
            if dur >= 15:  # ignore too-short candidate windows
                candidates.append({
                    "start": start, "end": end, "text": text,
                    "score": _score_window(text, dur),
                })

    candidates.sort(key=lambda c: c["score"], reverse=True)

    chosen = []
    for c in candidates:
        if len(chosen) >= target_count:
            break
        overlap = any(not (c["end"] <= o["start"] or c["start"] >= o["end"]) for o in chosen)
        if not overlap:
            chosen.append(c)

    chosen.sort(key=lambda c: c["start"])
    return chosen
