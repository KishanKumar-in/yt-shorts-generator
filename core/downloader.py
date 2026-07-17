"""Download a YouTube video with yt-dlp."""
import os
import yt_dlp


def download_video(url: str, out_dir: str) -> dict:
    """Download best mp4 video+audio. Returns dict with path, title, duration."""
    os.makedirs(out_dir, exist_ok=True)
    out_template = os.path.join(out_dir, "%(id)s.%(ext)s")

    ydl_opts = {
        "format": "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": out_template,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        # YouTube's default "web" client sometimes throws
        # "The page needs to be reloaded" due to bot-verification changes.
        # android/ios clients usually sidestep it.
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "web"],
            }
        },
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filepath = ydl.prepare_filename(info)
        # merge_output_format forces mp4, prepare_filename may report pre-merge ext
        base, _ = os.path.splitext(filepath)
        mp4path = base + ".mp4"
        if os.path.exists(mp4path):
            filepath = mp4path

    return {
        "path": filepath,
        "title": info.get("title", "video"),
        "duration": info.get("duration", 0),
        "id": info.get("id"),
    }
