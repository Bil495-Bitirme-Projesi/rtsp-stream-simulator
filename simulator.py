"""
RTSP + Admin Simulator  —  Interaktif CLI
==========================================
Gerçek backend'e karşı çalışır.

Çalıştır:
  python tools/mock_cms/simulator.py

Tipik akış:
  1. 'token' ile JWT'yi gir
  2. 'start kapi1 C:/videos/clip.mp4'  →  RTSP yayın açılır
  3. 'admin-add kapi1'                 →  Gerçek backend'e POST /api/cameras atılır
                                          Response'taki ID saklanır
  4. 'list'                            →  Anahtar / Video / RTSP / Backend ID tablosu
  5. 'stop kapi1'                      →  RTSP yayın kapanır
  6. 'admin-remove kapi1'              →  Backend'e DELETE atılır
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rtsp_streamer
from admin_client import AdminClient

# Anahtar --> {rtsp_url, video_path, backend_id}
_registry: dict[str, dict] = {}

_BANNER = """
+--------------------------------------------------+
|         RTSP + ADMIN SIMULATOR                   |
+--------------------------------------------------+
|  RTSP  ->  rtsp://localhost:<port>/<anahtar>     |
+--------------------------------------------------+
|  Baslamadan once:                                |
|    > token eyJhbGciOi...                         |
+--------------------------------------------------+
"""

_HELP = """
Komutlar
--------
  start <anahtar> <video_yolu>
      RTSP yayınını başlatır. Anahtar kısa, anlamlı bir isim olabilir.
      Örn: start kapi1 C:/videos/clip.mp4

  stop <anahtar>
      RTSP yayınını durdurur.

  list
      Aktif yayınları tablo olarak gösterir:
      Anahtar | Video Yolu | RTSP URL | Backend ID

  token <jwt_string>
      Admin HTTP isteklerinde kullanılacak JWT token'ı ayarlar.

  admin-url <url>
      Admin HTTP isteklerinin gideceği gerçek backend URL'ini ayarlar.
      (Varsayılan: .env'deki CMS_REST_URL)

  admin-add <anahtar> [name]
      Açık RTSP yayınını gerçek backend'e kamera olarak ekler.
      name verilmezse otomatik üretilir.
      Response'tan backend ID alınır ve 'list'te görünür.

  admin-remove <anahtar>
      Kaydedilmiş backend ID ile gerçek backend'e DELETE atar.

  help
      Bu metni gösterir.

  quit / exit
      Her şeyi kapatır ve çıkar.
"""


def _print_list() -> None:
    if not _registry:
        print("  Kayıtlı yayın yok.")
        return
    col = [12, 40, 44, 14]
    header = (
        f"  {'Anahtar':<{col[0]}} | {'Video Yolu':<{col[1]}} | "
        f"{'RTSP URL':<{col[2]}} | {'Backend ID':<{col[3]}}"
    )
    sep = "  " + "-" * col[0] + "-+-" + "-" * col[1] + "-+-" + "-" * col[2] + "-+-" + "-" * col[3]
    print(header)
    print(sep)
    for key, info in _registry.items():
        bid = str(info.get("backend_id") or "-")
        vp  = info.get("video_path", "-")
        ru  = info.get("rtsp_url", "-")
        print(f"  {key:<{col[0]}} | {vp:<{col[1]}} | {ru:<{col[2]}} | {bid:<{col[3]}}")


def main() -> None:
    print(_BANNER)

    admin = AdminClient()
    print(f"[SIM] Admin URL: {admin.base_url}")
    print("Hazir. Komut icin 'help' yazin.\n")

    try:
        while True:
            try:
                line = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not line:
                continue

            parts = line.split()
            cmd   = parts[0].lower()
            args  = parts[1:]

            if cmd in ("quit", "exit"):
                break

            elif cmd == "help":
                print(_HELP)

            elif cmd == "list":
                _print_list()

            elif cmd == "start":
                if len(args) < 2:
                    print("Kullanim: start <anahtar> <video_yolu>")
                    continue
                key        = args[0]
                video_path = " ".join(args[1:])
                if not os.path.exists(video_path):
                    print(f"[HATA] Dosya bulunamadı: {video_path}")
                    continue
                if not rtsp_streamer.mediamtx_running():
                    try:
                        rtsp_streamer.start_mediamtx()
                    except RuntimeError as e:
                        print(f"[HATA] mediamtx baslatılamadı: {e}")
                        continue
                rtsp_url = rtsp_streamer.start_stream(key, video_path)
                _registry[key] = {
                    "rtsp_url":   rtsp_url,
                    "video_path": video_path,
                    "backend_id": None,
                }
                print(f"[SIM] Yayın hazır: {rtsp_url}")
                print(f"[SIM] Şimdi 'admin-add {key}' ile gerçek backend'e kamera ekle.")

            elif cmd == "stop":
                if len(args) < 1:
                    print("Kullanım: stop <anahtar>")
                    continue
                key = args[0]
                if key not in _registry:
                    print(f"[HATA] '{key}' bulunamadı.")
                    continue
                rtsp_streamer.stop_stream(key)
                bid = _registry[key].get("backend_id")
                del _registry[key]
                if bid:
                    print(f"[SIM] Yayın durduruldu. Backend'den silmek için backend ID kullan: {bid}")

            elif cmd == "token":
                if not args:
                    print("Kullanım: token <jwt_string>")
                    continue
                admin.set_token(args[0])

            elif cmd == "admin-url":
                if not args:
                    print("Kullanım: admin-url <url>")
                    continue
                admin.base_url = args[0].rstrip("/")
                print(f"[AdminClient] Base URL: {admin.base_url}")

            elif cmd == "admin-add":
                if len(args) < 1:
                    print("Kullanım: admin-add <anahtar> [name]")
                    continue
                key  = args[0]
                name = args[1] if len(args) > 1 else None
                if key not in _registry:
                    print(f"[HATA] '{key}' için aktif yayın yok. Önce 'start {key} <video>' çalıştır.")
                    continue
                if _registry[key].get("backend_id"):
                    print(f"[UYARI] '{key}' zaten backend'e eklendi (ID: {_registry[key]['backend_id']}).")
                    continue
                rtsp_url = _registry[key]["rtsp_url"]
                data = admin.add_camera(rtsp_url, name=name)
                if data:
                    backend_id = data.get("id") or data.get("cameraId")
                    _registry[key]["backend_id"] = backend_id
                    print(f"[SIM] '{key}' → backend ID: {backend_id}")

            elif cmd == "admin-remove":
                if len(args) < 1:
                    print("Kullanım: admin-remove <anahtar>")
                    continue
                key  = args[0]
                info = _registry.get(key)
                if info is None:
                    print(f"[HATA] '{key}' bulunamadı.")
                    continue
                backend_id = info.get("backend_id")
                if not backend_id:
                    print(f"[HATA] '{key}' için kayıtlı backend ID yok. Önce 'admin-add {key}' çalıştır.")
                    continue
                if admin.remove_camera(backend_id):
                    _registry[key]["backend_id"] = None

            else:
                print(f"Bilinmeyen komut: '{cmd}'. 'help' yazın.")

    finally:
        print("\n[SIM] Kapatiliyor...")
        rtsp_streamer.stop_all_streams()
        rtsp_streamer.stop_mediamtx()
        print("[SIM] Cikti.")


if __name__ == "__main__":
    main()

