# YouTube → Shorts Generator

Turn any YouTube video into multiple vertical, <60-second short clips —
automatically. 100% free and runs entirely on your own machine: no paid
APIs, no cloud, no sign-ups, nothing ever uploaded anywhere.

**Pipeline:** [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) (download) →
[`Whisper`](https://github.com/openai/whisper) (local transcription) →
built-in clip selection (smart or even-split) →
[`ffmpeg`](https://ffmpeg.org) (cut + crop to vertical 9:16).

A 10-minute video produces roughly 8-9 clips by default (tunable).

## Features

- Paste a YouTube URL, get downloadable vertical shorts back
- Two clip-selection modes:
  - **Smart** — scores sentence windows using local heuristics (questions,
    punchy phrasing, exclamations) to find the most engaging moments
  - **Simple** — evenly splits the whole video in order, snapped to
    sentence boundaries
- Auto-suggests how many clips to make based on video length
- Vertical 9:16 crop with a blurred-background fill (like Shorts/Reels)
- Runs as a local web app (Streamlit) in your browser
- Nothing leaves your machine — video, transcript, and clips all stay local

## Requirements

- Python 3.10+ (3.11 recommended)
- [ffmpeg](https://ffmpeg.org) on your PATH
- ~1-2 GB free disk space for the Whisper model + working files

---

## Installation

### macOS

```bash
# Homebrew (skip if already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

brew install ffmpeg python@3.11

git clone https://github.com/<KishanKumar-in>/yt-shorts-generator.git
cd yt-shorts-generator
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Windows

1. Install [Python 3.11](https://www.python.org/downloads/) — during setup,
   check **"Add python.exe to PATH"**.
2. Install ffmpeg:
   - Easiest: open PowerShell and run `winget install ffmpeg`
   - Or via [Chocolatey](https://chocolatey.org/): `choco install ffmpeg`
   - Or download a build from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)
     and add its `bin` folder to your PATH manually.
3. Install [Git for Windows](https://git-scm.com/download/win) if you don't
   have it.

Then in PowerShell (or Git Bash):

```powershell
git clone https://github.com/<KishanKumar-in>/yt-shorts-generator.git
cd yt-shorts-generator
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Linux (Debian/Ubuntu-based)

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg git

git clone https://github.com/<KishanKumar-in>/yt-shorts-generator.git
cd yt-shorts-generator
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

For Fedora/Arch, swap the package manager (`dnf install ffmpeg python3 git`
or `pacman -S ffmpeg python git`) — the rest is identical.

---

## Running the app

From the project folder, with the virtual environment active:

```bash
# macOS/Linux
source venv/bin/activate
streamlit run app.py

# Windows
venv\Scripts\activate
streamlit run app.py
```

This opens `http://localhost:8501` in your browser. If it doesn't open
automatically, visit that URL yourself.

The first time you transcribe a video, Whisper downloads its model
(a few hundred MB) — one-time, then cached locally in `~/.cache/whisper`
(macOS/Linux) or `%USERPROFILE%\.cache\whisper` (Windows).

## Using it

1. Paste a YouTube URL, pick a Whisper model size (`small` is a good
   accuracy/speed balance on CPU), click **Download & transcribe**.
2. Choose **Smart** or **Simple** clip selection, adjust the clip count and
   max clip length if you want.
3. Choose whether to crop to vertical 9:16.
4. Click **Generate clips**. Each renders as an mp4, previewable and
   downloadable individually.

Generated files live in a temp working directory
(`<system temp>/yt_shorts_workdir`) and are cleared periodically by the OS —
use the **Download** button in the app to save clips permanently.

## Known limitations

- **No burned-in captions currently.** An earlier version supported
  word-highlighted karaoke-style captions via ffmpeg's `ass`/`subtitles`
  filter (which needs `libass`), but many prebuilt ffmpeg binaries
  (notably some Homebrew bottles) don't include `libass`, making that
  feature unreliable out of the box. It was removed for reliability. If you
  want it back and have an ffmpeg build with `libass` support
  (`ffmpeg -version` should show `--enable-libass`), see
  [Roadmap](#roadmap-ideas-for-contributors) below.
- "Smart" mode selection is heuristic-based (keyword/punctuation scoring),
  not an LLM — good enough to surface decent moments for free, but not as
  sharp as a paid AI clipping tool.
- Whisper transcription runs on CPU by default and can take a few minutes
  per video, longer for bigger models.

## Roadmap / ideas for contributors

- Re-add burned-in captions with a `libass` availability check and a
  graceful fallback (e.g. ffmpeg's built-in `drawtext` filter, which
  doesn't need `libass` but does need `freetype`)
- Optional LLM-based clip scoring (swap into `core/segmenter.py`)
- Batch mode for multiple URLs
- Auto-generated titles/hashtags per clip
- GPU acceleration for Whisper (`device="cuda"` on Linux/Windows with an
  NVIDIA GPU, or Apple Silicon via `mlx-whisper`)

Contributions welcome — open an issue or PR.

## Project structure

```
yt-shorts-generator/
├── app.py                 # Streamlit UI
├── core/
│   ├── downloader.py       # yt-dlp wrapper
│   ├── transcriber.py      # Whisper wrapper
│   ├── segmenter.py        # clip boundary selection (smart/simple)
│   └── clipper.py          # ffmpeg cut + vertical crop
├── requirements.txt
├── LICENSE
└── README.md
```

## License

MIT — see [LICENSE](LICENSE). Do whatever you like with it, no warranty.

## Disclaimer

This tool downloads video from YouTube for local processing. Make sure your
use complies with YouTube's Terms of Service and applicable copyright law in
your jurisdiction — this project is provided for personal/fair-use
purposes (e.g. repurposing your own content, or clips you have rights to).
