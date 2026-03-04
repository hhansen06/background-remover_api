import io
import logging
import os
import time
import uuid
import zipfile

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from rembg import remove as rembg_remove

app = FastAPI(title="Background Remover API", version="0.1.0")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_BYTES", str(8 * 1024 * 1024)))
REQUEST_ID_HEADER = os.getenv("REQUEST_ID_HEADER", "X-Request-ID")
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
START_TIME = time.time()

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("bg_remover")


def parse_cors_origins(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


cors_origins = parse_cors_origins(os.getenv("CORS_ORIGINS"))
if cors_origins:
    allow_credentials = "*" not in cors_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.time()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.time() - start_time) * 1000
        logger.exception(
            "%s %s failed %.2fms",
            request.method,
            request.url.path,
            duration_ms,
        )
        raise

    response.headers[REQUEST_ID_HEADER] = request_id
    duration_ms = (time.time() - start_time) * 1000
    logger.info(
        "%s %s %s %.2fms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None)
    logger.exception("Unhandled error", exc_info=exc)
    payload = {"detail": "Internal server error"}
    headers = None
    if request_id:
        payload["request_id"] = request_id
        headers = {REQUEST_ID_HEADER: request_id}
    return JSONResponse(status_code=500, content=payload, headers=headers)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict:
    return {"status": "ok", "model": "rembg"}


@app.get("/")
def root() -> dict:
    return {
        "name": app.title,
        "version": app.version,
        "description": "Remove image backgrounds and return PNG with alpha.",
        "endpoints": {
            "health": "/health",
            "ready": "/ready",
            "version": "/version",
            "ui": "/ui",
            "remove_bg": "/remove-bg",
            "remove_bg_compare": "/remove-bg-compare",
        },
        "supported_types": sorted(ALLOWED_TYPES),
        "max_image_bytes": MAX_IMAGE_BYTES,
        "uptime_seconds": int(time.time() - START_TIME),
    }


@app.get("/version")
def version() -> dict:
    return {"version": app.version}


@app.get("/ui", response_class=HTMLResponse)
def ui() -> str:
        return """<!doctype html>
<html lang="de">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Background Remover</title>
    <style>
        :root { color-scheme: light dark; }
        body {
            font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
            margin: 2rem auto;
            max-width: 560px;
            padding: 0 1rem;
        }
        form { display: grid; gap: .75rem; }
        button { width: fit-content; padding: .5rem .9rem; cursor: pointer; }
        #status { min-height: 1.2rem; }
    </style>
</head>
<body>
    <h1>Background Remover</h1>
    <p>Bild hochladen und Ergebnis als PNG herunterladen.</p>

    <form id="upload-form">
        <input id="file" name="file" type="file" accept="image/png,image/jpeg,image/webp" required />
        <button id="submit" type="submit">Hintergrund entfernen</button>
    </form>
    <p id="status"></p>

    <script>
        const form = document.getElementById('upload-form');
        const statusEl = document.getElementById('status');
        const submitBtn = document.getElementById('submit');
        const fileInput = document.getElementById('file');

        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            if (!fileInput.files || !fileInput.files.length) {
                statusEl.textContent = 'Bitte zuerst eine Datei auswählen.';
                return;
            }

            const file = fileInput.files[0];
            const formData = new FormData();
            formData.append('file', file);

            statusEl.textContent = 'Verarbeite Bild...';
            submitBtn.disabled = true;

            try {
                const response = await fetch('/remove-bg', {
                    method: 'POST',
                    body: formData,
                });

                if (!response.ok) {
                    let detail = 'Unbekannter Fehler';
                    try {
                        const payload = await response.json();
                        detail = payload.detail || detail;
                    } catch (_) {
                        detail = await response.text();
                    }
                    throw new Error(detail);
                }

                const blob = await response.blob();
                const url = URL.createObjectURL(blob);

                const baseName = file.name.includes('.')
                    ? file.name.slice(0, file.name.lastIndexOf('.'))
                    : file.name;
                const downloadName = `${baseName}-no-bg.png`;

                const link = document.createElement('a');
                link.href = url;
                link.download = downloadName;
                document.body.appendChild(link);
                link.click();
                link.remove();

                URL.revokeObjectURL(url);
                statusEl.textContent = 'Fertig. Download wurde gestartet.';
            } catch (error) {
                statusEl.textContent = `Fehler: ${error.message}`;
            } finally {
                submitBtn.disabled = false;
            }
        });
    </script>
</body>
</html>
"""


def decode_image(data: bytes) -> np.ndarray | None:
    array = np.frombuffer(data, dtype=np.uint8)
    return cv2.imdecode(array, cv2.IMREAD_COLOR)


def remove_background_bgr(image: np.ndarray) -> np.ndarray:
    height, width = image.shape[:2]
    margin = max(1, int(min(height, width) * 0.05))
    rect_width = max(1, width - 2 * margin)
    rect_height = max(1, height - 2 * margin)
    rect = (margin, margin, rect_width, rect_height)

    mask = np.zeros((height, width), np.uint8)
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)

    cv2.grabCut(image, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)
    fg_mask = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0).astype(
        "uint8"
    )

    rgba = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
    rgba[:, :, 3] = fg_mask * 255
    return rgba


def encode_png(image: np.ndarray) -> bytes:
    ok, buffer = cv2.imencode(".png", image)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to encode output image")
    return buffer.tobytes()


async def read_and_validate(file: UploadFile) -> tuple[bytes, np.ndarray]:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported media type")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="File too large")

    image = decode_image(data)
    if image is None:
        raise HTTPException(status_code=400, detail="Invalid image data")

    return data, image


@app.post("/remove-bg")
async def remove_bg(
    file: UploadFile = File(...),
    engine: str = Query("rembg", description="rembg or opencv"),
) -> StreamingResponse:
    data, image = await read_and_validate(file)

    if engine == "opencv":
        rgba = remove_background_bgr(image)
        output = encode_png(rgba)
    elif engine == "rembg":
        try:
            output = rembg_remove(data)
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail="Background removal failed"
            ) from exc
    else:
        raise HTTPException(status_code=400, detail="Unsupported engine")

    return StreamingResponse(io.BytesIO(output), media_type="image/png")


@app.post("/remove-bg-compare")
async def remove_bg_compare(file: UploadFile = File(...)) -> StreamingResponse:
    data, image = await read_and_validate(file)

    try:
        rembg_output = rembg_remove(data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Background removal failed") from exc

    opencv_output = encode_png(remove_background_bgr(image))

    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("rembg.png", rembg_output)
        zip_file.writestr("opencv.png", opencv_output)

    headers = {"Content-Disposition": "attachment; filename=outputs.zip"}
    return StreamingResponse(
        io.BytesIO(payload.getvalue()), media_type="application/zip", headers=headers
    )
