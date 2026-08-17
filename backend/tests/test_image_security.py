"""Phase 17 §11 image-upload security audit — the specific attack list
the spec named, gathered in one place. Several of these are already
covered elsewhere (decompression bombs and oversized dimensions in
tests/test_analyses.py, path traversal *in the stored URL* in
tests/test_storage.py, duplicate images in tests/test_similarity.py) —
this file covers what wasn't: empty files, SVG rejection, an
executable disguised as an image, and proof that the client-supplied
*filename* (malicious or Unicode) is inert, since it's never used to
construct a storage path in the first place.
"""

import io

from PIL import Image


def _make_jpeg_bytes(size=(128, 128), color=(200, 150, 100)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


def test_rejects_an_empty_file(client):
    files = {"file": ("cat.jpg", b"", "image/jpeg")}
    response = client.post("/api/v1/analyses", files=files)

    assert response.status_code == 422
    assert "valid image" in response.json()["detail"]


def test_rejects_svg_content_type_outright(client):
    # SVG can embed <script>, making it a real XSS vector if ever
    # served back inline — never in the content-type allowlist to
    # begin with, so this never reaches image decoding at all.
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    files = {"file": ("cat.svg", svg, "image/svg+xml")}
    response = client.post("/api/v1/analyses", files=files)

    assert response.status_code == 422


def test_rejects_an_executable_disguised_with_an_image_content_type(client):
    # A real Windows PE header (MZ magic bytes) wearing an image/jpeg
    # label and a .jpg filename — content-type and filename are both
    # client-supplied and untrustworthy; what actually protects this
    # endpoint is that Pillow can't decode it as an image at all.
    fake_exe = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff" + b"\x00" * 200
    files = {"file": ("totally-a-cat.jpg", fake_exe, "image/jpeg")}
    response = client.post("/api/v1/analyses", files=files)

    assert response.status_code == 422
    assert "valid image" in response.json()["detail"]


def test_path_traversal_filename_is_completely_inert(client):
    # The client-supplied filename is never used to construct a storage
    # path (server-generated UUIDs are — see app/storage/local.py) so
    # this must behave *exactly* like any other valid upload, not
    # merely "not crash."
    files = {"file": ("../../../../etc/passwd.jpg", _make_jpeg_bytes(), "image/jpeg")}
    response = client.post("/api/v1/analyses", files=files)

    assert response.status_code == 200
    assert response.json()["breed"]["label"]


def test_unicode_filename_is_completely_inert(client):
    files = {"file": ("猫の写真🐱.jpg", _make_jpeg_bytes(), "image/jpeg")}
    response = client.post("/api/v1/analyses", files=files)

    assert response.status_code == 200
    assert response.json()["breed"]["label"]


def test_mismatched_extension_with_a_real_image_body_still_succeeds(client):
    # Extension is cosmetic — content-type + actual decodability are
    # what's enforced, so a real JPEG uploaded with a misleading
    # filename extension is not itself an attack and must not be
    # rejected on that basis alone.
    files = {"file": ("photo.txt", _make_jpeg_bytes(), "image/jpeg")}
    response = client.post("/api/v1/analyses", files=files)

    assert response.status_code == 200
