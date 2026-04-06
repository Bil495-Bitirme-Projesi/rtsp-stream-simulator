"""
RTSP Streamer
=============
Mimari:
  1. mediamtx  --  tools/mock_cms/bin/mediamtx.exe olarak calisir, port 8554'u acar.
  2. ffmpeg    --  her stream icin videoyu sonsuz dongu ile mediamtx'e push eder.
  3. VLC / AIS --  rtsp://localhost:8554/<key> adresine direkt baglanir.

Kullanim:
  start_mediamtx()
  url = start_stream(key, video_path)
  stop_stream(key)
  stop_mediamtx()
"""

import shutil
import subprocess
import time
from pathlib import Path

_BIN_DIR = Path(__file__).parent / "bin"
RTSP_HOST = "localhost"
RTSP_PORT = 8554

_mediamtx_proc = None
_streams = {}


# ---------------------------------------------------------------------------
# Dahili yardimcilar
# ---------------------------------------------------------------------------

def _find_mediamtx():
    for candidate in [_BIN_DIR / "mediamtx.exe", _BIN_DIR / "mediamtx"]:
        if candidate.exists():
            return str(candidate)
    found = shutil.which("mediamtx")
    if found:
        return found
    raise FileNotFoundError(
        "mediamtx binary bulunamadi.\n"
        f"  Indir  -> https://github.com/bluenviron/mediamtx/releases\n"
        f"  Koy    -> {_BIN_DIR / 'mediamtx.exe'}"
    )


def _find_ffmpeg():
    found = shutil.which("ffmpeg")
    if found is None:
        raise FileNotFoundError("ffmpeg bulunamadi. PATH'e ekli oldugundan emin olun.")
    return found


# ---------------------------------------------------------------------------
# mediamtx yasam dongusu
# ---------------------------------------------------------------------------

def _kill_stale_mediamtx() -> None:
    """Varsa daha onceki mediamtx process'lerini oldur (port 8554 serbest kalsin)."""
    result = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq mediamtx.exe", "/FO", "CSV", "/NH"],
        capture_output=True, text=True
    )
    for line in result.stdout.splitlines():
        parts = line.strip().strip('"').split('","')
        if len(parts) >= 2:
            try:
                subprocess.run(["taskkill", "/PID", parts[1], "/F"],
                               capture_output=True)
            except Exception:
                pass


def start_mediamtx():
    global _mediamtx_proc
    if _mediamtx_proc and _mediamtx_proc.poll() is None:
        return  # zaten calisiyor

    # Kalan eski mediamtx surecleri ve port TIME_WAIT'ini temizle
    _kill_stale_mediamtx()
    time.sleep(0.5)

    mtx = _find_mediamtx()
    print(f"[RTSP] mediamtx baslatiliyor: {mtx}")
    _mediamtx_proc = subprocess.Popen(
        [mtx],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(_BIN_DIR),
    )
    time.sleep(1.5)
    if _mediamtx_proc.poll() is not None:
        raise RuntimeError("mediamtx hemen kapandi. Binary'yi kontrol edin.")
    print(f"[RTSP] Hazir -> rtsp://{RTSP_HOST}:{RTSP_PORT}/<isim>")


def stop_mediamtx():
    global _mediamtx_proc
    if _mediamtx_proc:
        _mediamtx_proc.terminate()
        _mediamtx_proc = None
        print("[RTSP] mediamtx durduruldu.")


def mediamtx_running():
    return _mediamtx_proc is not None and _mediamtx_proc.poll() is None


# ---------------------------------------------------------------------------
# Yayin yonetimi
# ---------------------------------------------------------------------------

def start_stream(key, video_path):
    """
    Verilen video dosyasini key adina RTSP olarak yayinlar.
    Daha once acik bir yayin varsa once kapatir.
    Yayin URL'ini dondurur.
    """
    if not mediamtx_running():
        raise RuntimeError("mediamtx calisiyor olmali. Once start_mediamtx() cagirin.")

    if key in _streams:
        stop_stream(key)

    rtsp_url = f"rtsp://{RTSP_HOST}:{RTSP_PORT}/{key}"

    cmd = [
        _find_ffmpeg(),
        "-re",
        "-stream_loop", "-1",
        "-i", str(video_path),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "zerolatency",
        "-pix_fmt", "yuv420p",
        "-an",
        "-f", "rtsp",
        "-rtsp_transport", "tcp",
        rtsp_url,
    ]

    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _streams[key] = {
        "proc":       proc,
        "rtsp_url":   rtsp_url,
        "video_path": str(video_path),
    }

    print(f"[RTSP] Yayin baslatildi: {rtsp_url}")
    return rtsp_url


def stop_stream(key):
    info = _streams.pop(key, None)
    if info:
        info["proc"].terminate()
        print(f"[RTSP] Yayin durduruldu: {key}")


def stop_all_streams():
    for key in list(_streams.keys()):
        stop_stream(key)


def list_streams():
    """stream_key --> {rtsp_url, video_path}"""
    return {
        key: {"rtsp_url": info["rtsp_url"], "video_path": info["video_path"]}
        for key, info in _streams.items()
    }
