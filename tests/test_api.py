import cv2
import numpy as np
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def make_png() -> bytes:
    image = np.zeros((20, 20, 3), dtype=np.uint8)
    image[:] = (255, 255, 255)
    ok, buffer = cv2.imencode(".png", image)
    assert ok
    return buffer.tobytes()


def make_webp() -> bytes:
    image = np.zeros((20, 20, 3), dtype=np.uint8)
    image[:] = (255, 255, 255)
    ok, buffer = cv2.imencode(".webp", image)
    assert ok
    return buffer.tobytes()


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers.get("X-Request-ID")


def test_ready() -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ui() -> None:
    response = client.get("/ui")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<form id=\"upload-form\">" in response.text


def test_remove_bg() -> None:
    data = make_png()
    files = {"file": ("test.png", data, "image/png")}
    response = client.post("/remove-bg", files=files)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")
    assert len(response.content) > 0


def test_remove_bg_opencv_engine() -> None:
    data = make_png()
    files = {"file": ("test.png", data, "image/png")}
    response = client.post("/remove-bg?engine=opencv", files=files)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")
    assert len(response.content) > 0


def test_remove_bg_compare() -> None:
    data = make_png()
    files = {"file": ("test.png", data, "image/png")}
    response = client.post("/remove-bg-compare", files=files)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/zip")
    assert len(response.content) > 0


def test_remove_bg_webp() -> None:
    data = make_webp()
    files = {"file": ("test.webp", data, "image/webp")}
    response = client.post("/remove-bg", files=files)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")
    assert len(response.content) > 0
