import io

from PIL import Image


def _make_jpeg_bytes(size=(128, 128), color=(200, 150, 100)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


def test_mismatched_origin_is_rejected_on_a_mutating_authenticated_endpoint(client, register_user):
    """verify_same_origin (app/core/csrf.py) is applied to every
    mutating endpoint that acts on the ambient session cookie. Every
    other test in this suite calls these endpoints same-origin (no
    Origin header sent by TestClient by default, which the dependency
    deliberately allows through — see its docstring), so none of them
    actually exercise the *rejection* path. This one does.
    """
    register_user()
    files = {"file": ("cat.jpg", _make_jpeg_bytes(), "image/jpeg")}
    analysis_id = client.post("/api/v1/analyses", files=files).json()["id"]

    response = client.post(
        f"/api/v1/analyses/{analysis_id}/favorite",
        headers={"Origin": "https://evil-site.example"},
    )

    assert response.status_code == 403


def test_matching_origin_is_allowed(client, register_user):
    register_user()
    files = {"file": ("cat.jpg", _make_jpeg_bytes(), "image/jpeg")}
    analysis_id = client.post("/api/v1/analyses", files=files).json()["id"]

    response = client.post(
        f"/api/v1/analyses/{analysis_id}/favorite",
        headers={"Origin": "http://localhost:3000"},
    )

    assert response.status_code == 200


def test_no_origin_header_is_allowed(client, register_user):
    """Same-origin navigations and non-browser clients (curl,
    server-to-server, this very test client by default) don't send an
    Origin header at all — requiring one would break legitimate
    same-origin usage, not just cross-site attacks."""
    register_user()
    files = {"file": ("cat.jpg", _make_jpeg_bytes(), "image/jpeg")}
    analysis_id = client.post("/api/v1/analyses", files=files).json()["id"]

    response = client.post(f"/api/v1/analyses/{analysis_id}/favorite")

    assert response.status_code == 200
