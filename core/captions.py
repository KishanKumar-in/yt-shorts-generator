"""Generate styled .ass subtitles (word-highlight 'karaoke' captions, like
Shorts/TikTok auto-captions) and burn them into a clip with ffmpeg/libass.
"""
import subprocess

DEFAULT_STYLE = {
    "font": "Arial",
    "font_size": 20,          # in ASS "points" at PlayResY=1280 (scaled for 1080x1920 canvas)
    "base_color": "&H00FFFFFF",       # white (ASS is &HAABBGGRR)
    "highlight_color": "&H0000D7FF",  # gold/yellow highlight for the active word
    "outline_color": "&H00000000",    # black outline
    "outline_width": 3,
    "bold": True,
    "position": "bottom",     # bottom | middle | top
    "words_per_group": 3,
}


def _hex_to_ass_color(hex_color: str) -> str:
    """Convert '#RRGGBB' to ASS '&H00BBGGRR'."""
    hex_color = hex_color.lstrip("#")
    r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
    return f"&H00{b}{g}{r}".upper()


def _alignment_for_position(position: str) -> int:
    # ASS numpad alignment: 2 = bottom-center, 5 = middle-center, 8 = top-center
    return {"bottom": 2, "middle": 5, "top": 8}.get(position, 2)


def build_ass(words: list, clip_start: float, clip_end: float, style: dict,
              canvas_w: int = 1080, canvas_h: int = 1920) -> str:
    """words: list of {word, start, end} in ABSOLUTE video time, already
    filtered to fall within [clip_start, clip_end]. Returns .ass file text.
    """
    s = {**DEFAULT_STYLE, **style}
    align = _alignment_for_position(s["position"])
    margin_v = 120 if s["position"] != "middle" else 0

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {canvas_w}
PlayResY: {canvas_h}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{s['font']},{int(s['font_size'] * (canvas_h / 720))},{s['base_color']},{s['highlight_color']},{s['outline_color']},&H00000000,{-1 if s['bold'] else 0},0,0,0,100,100,0,0,1,{s['outline_width']},0,{align},60,60,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def ts(t: float) -> str:
        t = max(0.0, t)
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        sec = t % 60
        return f"{h:01d}:{m:02d}:{sec:05.2f}"

    lines = []
    groups = [words[i:i + s["words_per_group"]] for i in range(0, len(words), s["words_per_group"])]

    for grp in groups:
        if not grp:
            continue
        g_start = grp[0]["start"] - clip_start
        g_end = grp[-1]["end"] - clip_start
        if g_end <= 0:
            continue

        # \k tags need centiseconds of duration for each word (karaoke fill:
        # text renders in SecondaryColour, filling to PrimaryColour as spoken)
        karaoke_text = ""
        for w in grp:
            dur_cs = max(1, round((w["end"] - w["start"]) * 100))
            karaoke_text += f"{{\\kf{dur_cs}}}{w['word']} "

        lines.append(
            f"Dialogue: 0,{ts(g_start)},{ts(g_end)},Default,,0,0,0,,{karaoke_text.strip()}"
        )

    return header + "\n".join(lines) + "\n"


def burn_captions(input_video: str, ass_path: str, output_video: str) -> None:
    """Burn subtitles into the video using ffmpeg + libass."""
    escaped = ass_path.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    vf = f"ass=filename='{escaped}'"
    cmd = [
        "ffmpeg", "-y", "-i", input_video,
        "-vf", vf,
        "-c:v", "libx264", "-crf", "19", "-preset", "veryfast",
        "-c:a", "aac", "-b:a", "160k",
        output_video,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "ffmpeg failed while burning captions.\n"
            f"Command: {' '.join(cmd)}\n"
            f"--- ffmpeg stderr (last 3000 chars) ---\n{result.stderr[-3000:]}"
        )