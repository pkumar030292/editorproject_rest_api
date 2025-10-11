import os
import yt_dlp
import ffmpeg
from urllib.parse import urlparse, parse_qs

FFMPEG_EXE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "ffmpeg-8.0-full_build",
        "ffmpeg-8.0-full_build",
        "bin",
        "ffmpeg.exe"
    )
)

if not os.path.exists(FFMPEG_EXE_PATH):
    raise FileNotFoundError(f"FFmpeg executable not found at: {FFMPEG_EXE_PATH}")

DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "YTD", "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def sanitize_url(url):
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    video_id = query.get("v", [""])[0]
    return f"https://www.youtube.com/watch?v={video_id}"

def get_available_formats(youtube_url):
    try:
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'ffmpeg_location': FFMPEG_EXE_PATH
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            formats = []
            for f in info.get("formats", []):
                if f.get("ext") in ["mp4", "webm", "m4a", "mp3"]:
                    formats.append({
                        "format_id": f["format_id"],
                        "ext": f["ext"],
                        "resolution": f.get("resolution") or f.get("height"),
                        "filesize": f.get("filesize"),
                        "abr": f.get("abr"),
                        "vcodec": f.get("vcodec"),
                        "acodec": f.get("acodec"),
                        "note": f.get("format_note")
                    })
            return formats
    except Exception as e:
        raise RuntimeError(f"yt-dlp error: {str(e)}")

def convert_to_mp3(input_path):
    base, _ = os.path.splitext(input_path)
    output_path = base + '.mp3'
    ffmpeg.input(input_path).output(output_path, format='mp3', acodec='libmp3lame').run(
        overwrite_output=True,
        cmd=FFMPEG_EXE_PATH
    )
    return output_path