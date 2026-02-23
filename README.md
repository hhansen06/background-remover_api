Background Remover API

REST-API mit FastAPI, die den Hintergrund von Bildern entfernt.
Die Hintergrund-Entfernung nutzt rembg (U2-Net). Beim ersten Start wird ein Modell geladen.

Voraussetzungen
- Python 3.11+
- Optional: Docker + Docker Compose

Lokaler Start
1) Abhaengigkeiten installieren
   pip install -r requirements.txt
2) Server starten
   uvicorn src.main:app --host 0.0.0.0 --port 8040

Docker Start
1) Image bauen und starten
   docker compose up --build

Beispiel-Request
curl -X POST "http://localhost:8040/remove-bg" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/image.jpg" \
  --output output.png

Vergleichs-Request (rembg vs opencv)
curl -X POST "http://localhost:8040/remove-bg-compare" \
   -H "Content-Type: multipart/form-data" \
   -F "file=@/path/to/image.jpg" \
   --output outputs.zip

Konfiguration
- MAX_IMAGE_BYTES: maximale Bildgroesse in Bytes (Default 8388608)
- LOG_LEVEL: Log-Level (Default INFO)
- CORS_ORIGINS: Komma-separierte Origins fuer CORS (leer = deaktiviert)
- REQUEST_ID_HEADER: Response-Header fuer Request-ID (Default X-Request-ID)

Unterstuetzte Formate
- image/jpeg
- image/png
- image/webp

Endpoints
- GET /health
- GET /ready
- GET /version
- POST /remove-bg
- POST /remove-bg-compare

Hinweise
- Jeder Response enthaelt eine Request-ID im Header (Default X-Request-ID).
- CORS_ORIGINS="*" erlaubt alle Origins (Credentials werden dann deaktiviert).
