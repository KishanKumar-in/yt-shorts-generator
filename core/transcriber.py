"""Transcribe video audio locally with OpenAI Whisper (free, runs on-device)."""
import whisper

_MODEL_CACHE = {}


def get_model(size: str = "small"):
    if size not in _MODEL_CACHE:
        _MODEL_CACHE[size] = whisper.load_model(size)
    return _MODEL_CACHE[size]


def transcribe(video_path: str, model_size: str = "small") -> dict:
    """Returns whisper result dict with 'segments', each segment has 'words'
    (word-level timestamps) because word_timestamps=True.
    """
    model = get_model(model_size)
    result = model.transcribe(video_path, word_timestamps=True, verbose=False)
    return result


def flatten_words(whisper_result: dict) -> list:
    """Flatten to a single list of {word, start, end} across the whole video."""
    words = []
    for seg in whisper_result.get("segments", []):
        for w in seg.get("words", []):
            words.append({
                "word": w["word"].strip(),
                "start": w["start"],
                "end": w["end"],
            })
    return words
