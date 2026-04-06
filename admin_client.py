"""
Admin HTTP Client
=================
Normalde frontend admin panelinin backend'e attığı kamera yönetim
isteklerini simüle eder.

Sertifika doğrulama:
  tools/mock_cms/certs/ca.pem  dosyası varsa HTTPS isteklerinde kullanılır.
  Dosya yoksa varsayılan sistem sertifikası doğrulaması uygulanır.

JWT Token:
  set_token(jwt_string)  →  sonraki tüm isteklere  Authorization: Bearer <token>
"""

import os
import random
import string
from pathlib import Path

import requests
from dotenv import load_dotenv

_CERTS_DIR = Path(__file__).parent / "certs"
_CA_CERT_PATH = _CERTS_DIR / "ca.pem"

# Ayni klasordeki veya ust klasordeki .env'i yükle
load_dotenv(Path(__file__).parent / ".env")
load_dotenv(Path(__file__).parent.parent / ".env")


def _random_name(prefix: str = "Kamera") -> str:
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}-{suffix}"


class AdminClient:
    def __init__(self, base_url: str | None = None):
        if base_url is None:
            base_url = os.getenv("CMS_REST_URL", "https://localhost:8443")
        self.base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._token: str | None = None

    # ------------------------------------------------------------------
    # Token yönetimi
    # ------------------------------------------------------------------

    def set_token(self, token: str) -> None:
        """JWT token'ı set eder; sonraki tüm isteklerde Authorization header'ı olarak gider."""
        self._token = token
        self._session.headers.update({"Authorization": f"Bearer {token}"})
        print(f"[AdminClient] Token ayarlandı.")

    def clear_token(self) -> None:
        self._token = None
        self._session.headers.pop("Authorization", None)
        print("[AdminClient] Token temizlendi.")

    # ------------------------------------------------------------------
    # Dahili yardımcılar
    # ------------------------------------------------------------------

    def _verify(self):
        """SSL doğrulama parametresi: PEM dosyası varsa onu kullan, yoksa True (sistem CA)."""
        if _CA_CERT_PATH.exists():
            return str(_CA_CERT_PATH)
        return True

    def _request(self, method: str, path: str, **kwargs):
        url = f"{self.base_url}{path}"
        try:
            resp = self._session.request(
                method, url, verify=self._verify(), timeout=10, **kwargs
            )
            return resp
        except requests.exceptions.SSLError as e:
            print(
                f"[AdminClient] SSL hatası: {e}\n"
                f"  İpucu: CA sertifikasını şuraya koy → {_CA_CERT_PATH}"
            )
            return None
        except requests.exceptions.ConnectionError as e:
            print(f"[AdminClient] Bağlantı hatası: {e}")
            return None
        except requests.RequestException as e:
            print(f"[AdminClient] İstek hatası: {e}")
            return None

    def _check(self, resp, label: str, action: str) -> bool:
        if resp is None:
            return False
        if resp.status_code in (200, 201, 204):
            return True
        print(f"[AdminClient] {action} başarısız: HTTP {resp.status_code}  →  {resp.text[:200]}")
        return False

    # ------------------------------------------------------------------
    # Kamera yönetim işlemleri
    # ------------------------------------------------------------------

    def add_camera(
        self,
        rtsp_url: str,
        detection_enabled: bool = True,
        name: str | None = None,
        threshold: float = 0.2,
        **extra,
    ) -> dict | None:
        """
        Admin panelinin kamera ekleme isteğini taklit eder.
        name verilmezse rastgele üretilir.
        Backend'den dönen JSON'u (kamera ID dahil) döndürür.
        Endpoint: POST {base_url}/api/cameras
        """
        payload = {
            "name": name or _random_name(),
            "rtspUrl": rtsp_url,
            "detectionEnabled": detection_enabled,
            "threshold": threshold,
            **extra,
        }
        resp = self._request("POST", "/admin/cameras", json=payload)
        if resp is None:
            return None
        if resp.status_code in (200, 201):
            try:
                data = resp.json()
            except Exception:
                data = {}
            backend_id = data.get("id") or data.get("cameraId")
            print(f"[AdminClient] ADD başarılı  →  backend ID: {backend_id}")
            return data
        print(f"[AdminClient] ADD başarısız: HTTP {resp.status_code}  →  {resp.text[:200]}")
        return None

    def remove_camera(self, backend_id) -> bool:
        """
        Backend'in oluşturduğu ID ile kamera silme isteği atar.
        Endpoint: DELETE {base_url}/api/cameras/{id}
        """
        resp = self._request("DELETE", f"/admin/cameras/{backend_id}")
        if self._check(resp, backend_id, "DELETE"):
            print(f"[AdminClient] DELETE başarılı: ID {backend_id}")
            return True
        return False

    def update_camera(self, backend_id, **fields) -> bool:
        """
        Backend'in oluşturduğu ID ile kamera güncelleme isteği atar.
        Endpoint: PUT {base_url}/api/cameras/{id}
        """
        resp = self._request("PUT", f"/admin/cameras/{backend_id}", json=fields)
        if self._check(resp, backend_id, "UPDATE"):
            print(f"[AdminClient] UPDATE başarılı: ID {backend_id}")
            return True
        return False

    def raw(self, method: str, path: str, **kwargs):
        """
        Özel bir endpoint'e ham istek atmak için.
        Örn: client.raw("POST", "/api/some-endpoint", json={"key": "val"})
        """
        return self._request(method, path, **kwargs)
