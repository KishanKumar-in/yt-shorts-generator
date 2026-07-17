"""Decide where to cut clips from the transcript.

Two modes:
  - "simple": evenly split the video into <=max_len chunks, snapped to
    sentence boundaries, covering the whole video in order.
  - "smart":  score sentence-grouped candidate windows by simple, local
    heuristics (no paid API needed) and keep the best non-overlapping ones.
"""
import re

SENTENCE_END = re.compile(r"[.!?]\s*$")


def _build_sentences(whisper_result: dict, max_sentence_len: float = 45.0) -> list:
    """Group whisper segments into sentences with start/end/text/word list.

    Also force-closes a "sentence" once it exceeds max_sentence_len even
    without punctuation — natural speech (tutorials, vlogs, lectures) often
    rambles for a long time between hard stops, and an unbounded sentence
    here would become unusable as a clip candidate downstream, silently
    shrinking the number of clips that can ever be produced.
    """
    sentences = []
    cur_words = []
    cur_start = None

    for seg in whisper_result.get("segments", []):
        for w in seg.get("words", []):
            word_text = w["word"]
            if cur_start is None:
                cur_start = w["start"]
            cur_words.append(w)

            hit_punct = SENTENCE_END.search(word_text.strip())
            too_long = (w["end"] - cur_start) >= max_sentence_len
            if hit_punct or too_long:
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


def even_segments(duration_sec: float, target_count: int, max_len: float = 58.0) -> list:
    """Guaranteed fallback: splits the whole video into `target_count`
    consecutive, non-overlapping segments (each capped at max_len). Doesn't
    depend on sentence/punctuation detection at all, so it always produces
    exactly the requested count (video length permitting).
    """
    if target_count <= 0 or duration_sec <= 0:
        return []
    piece = min(max_len, duration_sec / target_count)
    segments = []
    t = 0.0
    for _ in range(target_count):
        start = t
        end = min(duration_sec, start + piece)
        if end - start < 3:  # skip degenerate slivers at the very end
            break
        segments.append({"start": start, "end": end, "text": ""})
        t = end
    return segments


def fill_to_target(segments: list, duration_sec: float, target_count: int, max_len: float = 58.0) -> list:
    """If sentence-based selection (simple or smart) came up short of the
    requested clip count, top it up with evenly-spaced segments filling the
    gaps, so the user always gets the number of clips they asked for.
    """
    if len(segments) >= target_count or duration_sec <= 0:
        return segments

    existing = sorted(segments, key=lambda s: s["start"])
    covered = [(s["start"], s["end"]) for s in existing]

    def overlaps_existing(start, end):
        return any(not (end <= a or start >= b) for a, b in covered)

    needed = target_count - len(existing)
    candidates = even_segments(duration_sec, target_count * 2, max_len)
    for c in candidates:
        if needed <= 0:
            break
        if not overlaps_existing(c["start"], c["end"]):
            existing.append(c)
            covered.append((c["start"], c["end"]))
            needed -= 1

    existing.sort(key=lambda s: s["start"])
    return existing


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
