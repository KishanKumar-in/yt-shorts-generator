"""Cut a segment from the source video and optionally crop to vertical 9:16."""
import os
import subprocess


def cut_and_format(
    source_video: str,
    start: float,
    end: float,
    out_dir: str,
    clip_name: str,
    vertical: bool = True,
) -> str:
    """Returns path to the final rendered clip."""
    os.makedirs(out_dir, exist_ok=True)
    raw_path = os.path.join(out_dir, f"{clip_name}_raw.mp4")
    final_path = os.path.join(out_dir, f"{clip_name}.mp4")

    duration = max(0.1, end - start)

    # 1) Cut the segment (re-encode for frame-accurate cuts)
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(start), "-i", source_video, "-t", str(duration),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
        "-c:a", "aac", "-b:a", "160k", raw_path,
    ], check=True, capture_output=True)

    # 2) Optionally crop/pad to vertical 9:16 (1080x1920), blurred-background style
    if vertical:
        canvas_w, canvas_h = 1080, 1920
        vf = (
            f"split=2[bg][fg];"
            f"[bg]scale={canvas_w}:{canvas_h}:force_original_aspect_ratio=increase,"
            f"crop={canvas_w}:{canvas_h},gblur=sigma=20[bg2];"
            f"[fg]scale={canvas_w}:-2:force_original_aspect_ratio=decrease[fg2];"
            f"[bg2][fg2]overlay=(W-w)/2:(H-h)/2,format=yuv420p"
        )
        subprocess.run([
            "ffmpeg", "-y", "-i", raw_path, "-vf", vf,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
            "-c:a", "aac", "-b:a", "160k", final_path,
        ], check=True, capture_output=True)
        os.remove(raw_path)
    else:
        os.replace(raw_path, final_path)

    return final_path
