import os
import tempfile
import streamlit as st

from core import downloader, transcriber, segmenter, clipper

st.set_page_config(page_title="YT Shorts Generator", layout="wide")
st.title("🎬 YouTube → Shorts Generator")
st.caption("100% free & local: yt-dlp + Whisper + ffmpeg. Nothing leaves your Mac.")

if "video_info" not in st.session_state:
    st.session_state.video_info = None
if "transcript" not in st.session_state:
    st.session_state.transcript = None
if "clips" not in st.session_state:
    st.session_state.clips = None

WORKDIR = os.path.join(tempfile.gettempdir(), "yt_shorts_workdir")
os.makedirs(WORKDIR, exist_ok=True)

# ---------- Step 1: URL + fetch/transcribe ----------
url = st.text_input("YouTube video URL")

col_a, col_b = st.columns(2)
with col_a:
    model_size = st.selectbox(
        "Whisper model (bigger = more accurate, slower)",
        ["tiny", "base", "small", "medium"], index=2,
    )
with col_b:
    fetch_btn = st.button("1) Download & transcribe", type="primary", disabled=not url)

if fetch_btn:
    with st.spinner("Downloading video with yt-dlp..."):
        info = downloader.download_video(url, os.path.join(WORKDIR, "source"))
        st.session_state.video_info = info
    with st.spinner(f"Transcribing with Whisper ({model_size}) — this can take a few minutes..."):
        result = transcriber.transcribe(info["path"], model_size=model_size)
        st.session_state.transcript = result
    st.success(f"Ready: '{info['title']}' ({info['duration']:.0f}s)")

info = st.session_state.video_info
transcript = st.session_state.transcript

if info and transcript:
    st.divider()
    st.subheader("2) Choose how clips are picked")

    suggested = segmenter.suggest_clip_count(info["duration"])
    mode = st.radio(
        "Clip selection mode",
        ["Smart (best/most engaging moments)", "Simple (even chunks, in order)"],
        horizontal=True,
    )
    clip_count = st.slider("Number of clips", min_value=1, max_value=max(20, suggested + 5),
                            value=suggested)
    max_len = st.slider("Max clip length (seconds)", 20, 60, 58)

    st.subheader("3) Format")
    vertical = st.checkbox("Crop to vertical 9:16 (Shorts/Reels)", value=True)

    generate_btn = st.button("4) Generate clips", type="primary")

    if generate_btn:
        smart = mode.startswith("Smart")
        with st.spinner("Selecting clip boundaries..."):
            if smart:
                segments = segmenter.smart_segments(transcript, target_count=clip_count, max_len=max_len)
            else:
                segments = segmenter.simple_segments(transcript, max_len=max_len, target_count=clip_count)

            if len(segments) < clip_count:
                segments = segmenter.fill_to_target(
                    segments, info["duration"], clip_count, max_len=max_len
                )
                if len(segments) < clip_count:
                    st.caption(
                        f"Note: only {len(segments)} clip(s) fit given the video length "
                        f"and max clip length — reduce max clip length or pick a shorter "
                        f"section to get more."
                    )

        out_dir = os.path.join(WORKDIR, "clips")
        results = []
        progress = st.progress(0.0, text="Rendering clips...")

        for i, seg in enumerate(segments):
            path = clipper.cut_and_format(
                source_video=info["path"],
                start=seg["start"],
                end=seg["end"],
                out_dir=out_dir,
                clip_name=f"clip_{i+1:02d}",
                vertical=vertical,
            )
            results.append({"path": path, "text": seg["text"], "start": seg["start"], "end": seg["end"]})
            progress.progress((i + 1) / len(segments), text=f"Rendered {i+1}/{len(segments)}")

        st.session_state.clips = results
        st.success(f"Done! Generated {len(results)} clips.")

clips = st.session_state.clips
if clips:
    st.divider()
    st.subheader("Your clips")
    for i, c in enumerate(clips):
        with st.container(border=True):
            cols = st.columns([1, 2])
            with cols[0]:
                st.video(c["path"])
            with cols[1]:
                st.markdown(f"**Clip {i+1}** &nbsp; `{c['start']:.0f}s - {c['end']:.0f}s`")
                st.caption(c["text"][:300])
                with open(c["path"], "rb") as f:
                    st.download_button("Download", f, file_name=os.path.basename(c["path"]),
                                        mime="video/mp4", key=f"dl_{i}")
