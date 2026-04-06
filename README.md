# rtsp-stream-simulator

Yerel video dosyalarini RTSP olarak yayınlamayı ve çalışan cms instance'ına; oluşan rtsp url'i içerecek şekilde kamera ekleme, silme isteği göndermeyi sağlar.

## Gereksinimler

- Python 3.7+
- [ffmpeg](https://ffmpeg.org/download.html) (PATH'e ekli olmali)

## Kurulum

```
pip install -r requirements.txt
```

## Yapilandirma

Eğer cms'ye `.env` dosyasindaki adresten farklı bir adresten ulaşılıyorsa CMS_REST_URL'in değerini değiştirin.

```
CMS_REST_URL=https://<backend-ip>/api
```

## Calistirma

```
python simulator.py
```

## Komutlar

| Komut | Aciklama |
|---|---|
| `start <anahtar> <video_yolu>` | Videoyu sonsuz dongu ile RTSP olarak yayinlar |
| `stop <anahtar>` | Yayini durdurur |
| `list` | Aktif yayinlari tablo olarak gosterir |
| `token <jwt>` | Backend istekleri icin JWT token ayarlar |
| `admin-url <url>` | Backend URL'ini gunceller |
| `admin-add <anahtar> [isim]` | Yayini backend'e kamera olarak ekler |
| `admin-remove <anahtar>` | Kamerayi backend'den siler |
| `help` | Komut listesini gosterir |
| `quit` | Her seyi kapatir ve cikar |

## Ornek Akis

```
> token eyJhbGciOi...
> start kapi1 C:/videos/sehir.mp4
> list
> admin-add kapi1 Giris-Kamerasi
> admin-remove kapi1
> quit
```
