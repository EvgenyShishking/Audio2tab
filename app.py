import streamlit as st
import os
import sys
import tempfile
from io import StringIO
import contextlib
import time
import logging
from tayuya import MIDIParser
import base64
import re
from pathlib import Path
import html

# ─── Silence TF / Basic Pitch debug noise ────────────────────────────────────
logging.getLogger().setLevel(logging.WARNING)
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# ─── Page config (must be first Streamlit call) ───────────────────────────────
st.set_page_config(
    page_title="Tab Gener8or — MP3/WAV to Guitar Tab",
    page_icon="🎸",
    layout="wide",
)

# ─── Session state ────────────────────────────────────────────────────────────
if "theme" not in st.session_state:
    st.session_state.theme = "dark"
if "version" not in st.session_state:
    st.session_state.version = "1.1.0"

# ─── CSS themes ──────────────────────────────────────────────────────────────
DARK_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
body,.stApp{background:#0a0a0a;color:#e0e0e0;font-family:'Inter',sans-serif}
#MainMenu,footer,header{visibility:hidden}
[data-testid="stSidebar"],[data-testid="stSidebarContent"]{background:#0a0a0a!important}
h1,h2,h3,h4,h5,h6{color:#fff!important;font-weight:700!important}
h1{font-size:2.2rem!important;letter-spacing:-.025em!important}
p,li,div{color:#e0e0e0}
a{color:#ff4d4d!important;text-decoration:none!important}
hr{border-color:#333!important;margin:2rem 0!important}
.stButton button{background:#ff4d4d!important;color:#fff!important;border:none!important;border-radius:6px!important;font-weight:600!important;transition:all .2s!important}
.stButton button:hover{background:#e63939!important;transform:translateY(-2px);box-shadow:0 4px 12px rgba(255,77,77,.3)}
.stFileUploader{background:#121212!important;border:2px dashed #333!important;border-radius:8px!important}
.tab-container{font-family:'Courier New',monospace;font-size:13px;white-space:pre!important;overflow-x:auto!important;background:#121212!important;padding:1.5rem!important;border-radius:8px!important;border:1px solid #333!important;line-height:1.4;color:#e0e0e0!important;margin-top:1rem}
pre{white-space:pre;overflow-x:auto;font-size:13px;color:#e0e0e0!important;margin:0;padding:0}
.download-btn{display:inline-block;background:#121212!important;color:#fff!important;padding:10px 20px!important;border-radius:6px!important;border:1px solid #ff4d4d!important;font-weight:600;text-decoration:none!important;transition:all .2s;margin:0.5rem .5rem 1rem 0}
.download-btn:hover{background:#ff4d4d!important;transform:translateY(-2px);box-shadow:0 4px 12px rgba(255,77,77,.3)}
audio{width:100%!important;border-radius:8px!important}
.app-footer{position:fixed;bottom:0;left:0;width:100%;padding:8px 20px;background:#0a0a0a;color:#555;font-size:12px;text-align:center;border-top:1px solid #222}
.hero-wrap{position:relative;width:100%;height:420px;overflow:hidden;border-radius:12px;margin-bottom:2.5rem;background:#121212;display:flex;align-items:center;justify-content:center;box-shadow:0 10px 30px rgba(0,0,0,.5)}
.hero-img{position:absolute;width:100%;height:100%;object-fit:cover;opacity:.45}
.hero-text{position:relative;z-index:2;text-align:center;padding:0 2rem;max-width:800px}
.hero-title{font-size:3rem!important;color:#fff!important;text-shadow:0 2px 10px rgba(0,0,0,.8)}
.hero-sub{font-size:1.2rem;color:#e0e0e0;margin:.5rem 0 0}
.badge{display:inline-block;background:#1e1e1e;border:1px solid #333;border-radius:20px;padding:4px 12px;font-size:12px;color:#aaa;margin-right:6px}
.block-container{max-width:95%!important;padding-top:1rem;padding-bottom:4rem}
</style>
"""

LIGHT_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
body,.stApp{background:#fff;color:#333;font-family:'Inter',sans-serif}
#MainMenu,footer,header{visibility:hidden}
[data-testid="stSidebar"],[data-testid="stSidebarContent"]{background:#fff!important}
h1,h2,h3,h4,h5,h6{color:#1a1a1a!important;font-weight:700!important}
h1{font-size:2.2rem!important;letter-spacing:-.025em!important}
p,li,div{color:#444}
a{color:#ff4d4d!important;text-decoration:none!important}
hr{border-color:#eee!important;margin:2rem 0!important}
.stButton button{background:#ff4d4d!important;color:#fff!important;border:none!important;border-radius:6px!important;font-weight:600!important;transition:all .2s!important}
.stButton button:hover{background:#e63939!important;transform:translateY(-2px);box-shadow:0 4px 12px rgba(255,77,77,.25)}
.tab-container{font-family:'Courier New',monospace;font-size:13px;white-space:pre!important;overflow-x:auto!important;background:#f8f9fa!important;padding:1.5rem!important;border-radius:8px!important;border:1px solid #dee2e6!important;line-height:1.4;color:#333!important;margin-top:1rem}
pre{white-space:pre;overflow-x:auto;font-size:13px;color:#333!important;margin:0;padding:0}
.download-btn{display:inline-block;background:#fff!important;color:#ff4d4d!important;padding:10px 20px!important;border-radius:6px!important;border:1px solid #ff4d4d!important;font-weight:600;text-decoration:none!important;transition:all .2s;margin:0.5rem .5rem 1rem 0}
.download-btn:hover{background:#ff4d4d!important;color:#fff!important;transform:translateY(-2px)}
audio{width:100%!important;border-radius:8px!important}
.app-footer{position:fixed;bottom:0;left:0;width:100%;padding:8px 20px;background:#fff;color:#aaa;font-size:12px;text-align:center;border-top:1px solid #eee}
.hero-wrap{position:relative;width:100%;height:420px;overflow:hidden;border-radius:12px;margin-bottom:2.5rem;background:#f0f0f0;display:flex;align-items:center;justify-content:center;box-shadow:0 10px 30px rgba(0,0,0,.1)}
.hero-img{position:absolute;width:100%;height:100%;object-fit:cover;opacity:.6}
.hero-text{position:relative;z-index:2;text-align:center;padding:0 2rem;max-width:800px}
.hero-title{font-size:3rem!important;color:#1a1a1a!important;text-shadow:0 2px 10px rgba(255,255,255,.8)}
.hero-sub{font-size:1.2rem;color:#444;margin:.5rem 0 0}
.badge{display:inline-block;background:#f1f1f1;border:1px solid #ddd;border-radius:20px;padding:4px 12px;font-size:12px;color:#666;margin-right:6px}
.block-container{max-width:95%!important;padding-top:1rem;padding-bottom:4rem}
</style>
"""

# ─── Helpers ──────────────────────────────────────────────────────────────────

@contextlib.contextmanager
def _capture_stdout():
    old = sys.stdout
    buf = StringIO()
    sys.stdout = buf
    try:
        yield buf
    finally:
        sys.stdout = old


def _img_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def _download_link(data: bytes, filename: str, label: str) -> str:
    b64 = base64.b64encode(data).decode()
    return (
        f'<a href="data:application/octet-stream;base64,{b64}" '
        f'download="{filename}" class="download-btn">{label}</a>'
    )


def _get_audio_mime(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return {"mp3": "audio/mpeg", "wav": "audio/wav", "ogg": "audio/ogg"}.get(ext.lstrip("."), "audio/mpeg")


def _format_tab(raw: str) -> str:
    """Clean ANSI codes and split very long tab lines for readability."""
    raw = re.sub(r"\x1B\[[0-9;]*[mK]", "", raw)
    lines = raw.strip().split("\n")
    out, i = [], 0
    SEG = 100
    while i < len(lines):
        if i + 5 < len(lines) and all("|" in l for l in lines[i : i + 6]):
            chunk = lines[i : i + 6]
            maxlen = max(len(l) for l in chunk)
            if maxlen > SEG:
                segs = (maxlen + SEG - 1) // SEG
                for s in range(segs):
                    for l in chunk:
                        sep = l.index("|") if "|" in l else 0
                        prefix = l[: sep + 1] if s > 0 else ""
                        body = l[sep + 1 :] if "|" in l else l
                        start = s * SEG - (sep + 1 if s > 0 else 0)
                        start = max(0, start)
                        out.append(prefix + body[start : start + SEG])
                    if s < segs - 1:
                        out.append("")
            else:
                out.extend(chunk)
            out.append("")
            i += 6
        else:
            out.append(lines[i])
            i += 1
    return "\n".join(out)


# ─── Core processing ──────────────────────────────────────────────────────────

def process_audio(uploaded_file) -> dict | None:
    """Convert an uploaded audio file to guitar tablature.

    Supports MP3, WAV, OGG.
    Returns dict with keys: tabs, midi_bytes, midi_filename.
    """
    from basic_pitch.inference import predict  # lazy import keeps startup fast

    suffix = Path(uploaded_file.name).suffix.lower() or ".mp3"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_audio:
        tmp_audio.write(uploaded_file.getvalue())
        audio_path = tmp_audio.name

    with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as tmp_midi:
        midi_path = tmp_midi.name

    try:
        with st.spinner("🎵 Analysing audio with Basic Pitch AI…"):
            with contextlib.redirect_stdout(StringIO()), contextlib.redirect_stderr(StringIO()):
                _, midi_data, _ = predict(audio_path)
            midi_data.write(midi_path)

        with st.spinner("🎸 Building guitar tablature…"):
            mid = MIDIParser(midi_path, track=1)
            with _capture_stdout() as buf:
                mid.render_tabs()
            tabs = buf.getvalue()

        with open(midi_path, "rb") as f:
            midi_bytes = f.read()

        midi_filename = Path(uploaded_file.name).stem + ".mid"
        return {"tabs": tabs, "midi_bytes": midi_bytes, "midi_filename": midi_filename}

    except Exception as exc:
        st.error(f"Conversion failed: {exc}")
        return None

    finally:
        for p in (audio_path, midi_path):
            try:
                os.unlink(p)
            except OSError:
                pass


# ─── UI helpers ───────────────────────────────────────────────────────────────

def render_hero():
    image_candidates = [
        "assets/images/player-piano-7.png",
        "assets/images/player-piano-5.png",
        "assets/images/player-piano.png",
    ]
    img_html = ""
    for p in image_candidates:
        if os.path.exists(p):
            b64 = _img_b64(p)
            img_html = f'<img src="data:image/png;base64,{b64}" class="hero-img" alt="Hero">'
            break

    st.markdown(
        f"""
        <div class="hero-wrap">
            {img_html}
            <div class="hero-text">
                <h1 class="hero-title">Tab Gener8or</h1>
                <p class="hero-sub">Transform your audio recordings into guitar tablature using AI</p>
                <p style="margin-top:1.2rem">
                    <span class="badge">🤖 Basic Pitch AI</span>
                    <span class="badge">🎸 Tayuya</span>
                    <span class="badge">🎵 MP3 · WAV · OGG</span>
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─── Main app ─────────────────────────────────────────────────────────────────

def main():
    # Sidebar
    with st.sidebar:
        st.title("⚙️ Tab Gener8or")
        st.divider()

        st.subheader("How to use")
        st.markdown(
            """
            1. Upload an audio file (MP3, WAV or OGG)
            2. Click **Convert to Guitar Tab**
            3. View the tablature and download MIDI or .txt
            """
        )
        st.markdown(
            """
            **Best results with:**
            - Clean, dry guitar recordings
            - Single-instrument tracks
            - Well-defined single notes
            """
        )
        st.divider()

        st.subheader("How it works")
        st.markdown(
            """
            **[Basic Pitch](https://github.com/spotify/basic-pitch)** (Spotify) detects notes
            from audio and outputs MIDI.
            **[Tayuya](https://github.com/vipul-sharma20/tayuya)** converts MIDI to guitar tabs.
            """
        )
        st.divider()

        theme_choice = st.radio("Theme", ["🌙 Dark", "☀️ Light"],
                                index=0 if st.session_state.theme == "dark" else 1)
        st.session_state.theme = "dark" if theme_choice.startswith("🌙") else "light"

    # Apply theme CSS
    st.markdown(DARK_CSS if st.session_state.theme == "dark" else LIGHT_CSS, unsafe_allow_html=True)

    # Hero
    render_hero()

    # Title
    st.title("🎸 Audio → Guitar Tab Converter")
    st.write(
        "Upload a guitar recording and get playable tablature in seconds. "
        "Supports **MP3**, **WAV**, and **OGG** files up to 100 MB."
    )

    # File upload — accept mp3, wav, ogg
    uploaded = st.file_uploader(
        "Choose an audio file",
        type=["mp3", "wav", "ogg"],
        help="Best results: clean, single-instrument guitar recordings.",
    )

    if uploaded is not None:
        size_kb = len(uploaded.getvalue()) / 1024
        theme_bg = "#121212" if st.session_state.theme == "dark" else "#f8f9fa"
        theme_border = "#333" if st.session_state.theme == "dark" else "#dee2e6"
        theme_text = "#e0e0e0" if st.session_state.theme == "dark" else "#333"
        theme_sub = "#999" if st.session_state.theme == "dark" else "#666"

        st.markdown(
            f"""
            <div style="display:flex;align-items:center;background:{theme_bg};
                        padding:10px 14px;border-radius:6px;border:1px solid {theme_border};margin-bottom:1rem">
                <span style="font-size:1.5rem;margin-right:12px">🎵</span>
                <div>
                    <div style="font-weight:600;color:{theme_text}">{uploaded.name}</div>
                    <div style="font-size:12px;color:{theme_sub}">{size_kb:.1f} KB · {Path(uploaded.name).suffix.upper().lstrip('.')}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_left, col_right = st.columns([1, 2], gap="large")

        with col_left:
            st.subheader("Preview")
            st.audio(uploaded, format=_get_audio_mime(uploaded.name))
            st.caption("Large files take longer to process.")
            convert = st.button("🎸 Convert to Guitar Tab", use_container_width=True, type="primary")

        if convert:
            progress = st.progress(0)
            status = st.empty()

            status.info("Starting conversion…")
            progress.progress(15)

            status.info("Converting audio → MIDI (Basic Pitch AI)…")
            progress.progress(35)

            result = process_audio(uploaded)

            if result:
                status.info("Rendering guitar tablature…")
                progress.progress(80)
                time.sleep(0.3)
                progress.progress(100)
                status.empty()

                tabs = result["tabs"]
                if tabs and tabs.strip():
                    st.success("✅ Conversion complete!")

                    # Download buttons
                    dl_midi = _download_link(result["midi_bytes"], result["midi_filename"], "⬇️ Download MIDI")
                    dl_txt = _download_link(
                        tabs.encode(),
                        result["midi_filename"].replace(".mid", "_tab.txt"),
                        "⬇️ Download Tab (.txt)",
                    )
                    st.markdown(dl_midi + dl_txt, unsafe_allow_html=True)

                    # Tab display
                    st.subheader("Guitar Tablature")
                    formatted = _format_tab(tabs)
                    st.markdown(
                        f"""
                        <div class="tab-container">
                            <pre>{html.escape(formatted)}</pre>
                            <div style="text-align:right;margin-top:.5rem;font-size:12px;
                                        color:{'#666' if st.session_state.theme == 'dark' else '#999'}">
                                ← scroll to see more →
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    progress.empty()
                    st.error("No notes detected. Try a cleaner, single-instrument recording.")
                    st.info("💡 Tips: use a dry guitar signal, avoid heavy distortion or reverb.")
            else:
                progress.empty()

    st.divider()
    st.markdown(
        f'<div class="app-footer">Tab Gener8or v{st.session_state.version} &nbsp;·&nbsp; '
        'Built with Basic Pitch &amp; Tayuya &nbsp;·&nbsp; '
        '<a href="https://github.com/spotify/basic-pitch" target="_blank">Basic Pitch</a> &nbsp;·&nbsp; '
        '<a href="https://github.com/vipul-sharma20/tayuya" target="_blank">Tayuya</a>'
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
