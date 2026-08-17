from unittest.mock import MagicMock, patch

import pytest

from app.storage.local import LocalImageStorageProvider
from app.storage.s3 import S3ImageStorageProvider


class TestLocalImageStorageProvider:
    async def test_save_then_load_roundtrips_the_same_bytes(self, tmp_path):
        provider = LocalImageStorageProvider(str(tmp_path))
        original = b"fake-jpeg-bytes"

        url = await provider.save(original, key="abc123", content_type="image/jpeg")
        assert url == "/media/abc123.jpg"

        loaded = await provider.load(url)
        assert loaded == original

    async def test_path_traversal_in_the_url_is_rejected(self, tmp_path):
        provider = LocalImageStorageProvider(str(tmp_path))
        # A secret file that must never be reachable through the
        # /media/{...} URL scheme, regardless of what a client requests.
        secret = tmp_path.parent / "secret.txt"
        secret.write_text("should never be readable via /media")

        result = await provider.load("/media/../secret.txt")
        assert result is None

    async def test_load_of_a_nonexistent_file_returns_none_not_an_error(self, tmp_path):
        provider = LocalImageStorageProvider(str(tmp_path))
        assert await provider.load("/media/does-not-exist.jpg") is None

    def test_is_available_reflects_directory_writability(self, tmp_path):
        provider = LocalImageStorageProvider(str(tmp_path / "nested" / "uploads"))
        assert provider.is_available is True


class TestS3ImageStorageProvider:
    def _provider(self, **overrides) -> S3ImageStorageProvider:
        kwargs = dict(
            bucket_name="meowverse-photos",
            region="auto",
            endpoint_url=None,
            access_key_id="key",
            secret_access_key="secret",
            public_url_base=None,
        )
        kwargs.update(overrides)
        return S3ImageStorageProvider(**kwargs)

    def test_is_available_false_without_a_bucket_configured(self):
        provider = self._provider(bucket_name="")
        assert provider.is_available is False

    def test_is_available_true_with_a_bucket_configured(self):
        assert self._provider().is_available is True

    async def test_save_uploads_and_returns_a_public_url(self):
        provider = self._provider(public_url_base="https://cdn.example.com")
        mock_client = MagicMock()
        with patch("boto3.client", return_value=mock_client):
            url = await provider.save(b"fake-bytes", key="abc123", content_type="image/png")

        assert url == "https://cdn.example.com/abc123.png"
        mock_client.put_object.assert_called_once_with(
            Bucket="meowverse-photos",
            Key="abc123.png",
            Body=b"fake-bytes",
            ContentType="image/png",
        )

    async def test_save_falls_back_to_the_bucket_url_without_a_cdn_configured(self):
        provider = self._provider(region="us-east-1")
        mock_client = MagicMock()
        with patch("boto3.client", return_value=mock_client):
            url = await provider.save(b"fake-bytes", key="abc123", content_type="image/jpeg")

        assert url == "https://meowverse-photos.s3.us-east-1.amazonaws.com/abc123.jpg"

    async def test_load_downloads_by_reversing_the_public_url(self):
        provider = self._provider(public_url_base="https://cdn.example.com")
        mock_client = MagicMock()
        mock_body = MagicMock()
        mock_body.read.return_value = b"downloaded-bytes"
        mock_client.get_object.return_value = {"Body": mock_body}

        with patch("boto3.client", return_value=mock_client):
            result = await provider.load("https://cdn.example.com/abc123.png")

        assert result == b"downloaded-bytes"
        mock_client.get_object.assert_called_once_with(
            Bucket="meowverse-photos", Key="abc123.png"
        )

    async def test_load_of_an_unrecognized_url_returns_none_not_an_error(self):
        provider = self._provider(public_url_base="https://cdn.example.com")
        assert await provider.load("https://not-our-cdn.example.com/x.png") is None

    async def test_load_failure_is_caught_and_returns_none(self):
        provider = self._provider(public_url_base="https://cdn.example.com")
        mock_client = MagicMock()
        mock_client.get_object.side_effect = RuntimeError("network error")

        with patch("boto3.client", return_value=mock_client):
            result = await provider.load("https://cdn.example.com/abc123.png")

        assert result is None


def test_unknown_storage_provider_raises_a_clear_error(monkeypatch):
    from app.core.config import get_settings
    from app.storage import get_image_storage

    monkeypatch.setenv("IMAGE_STORAGE_PROVIDER", "dropbox")
    get_settings.cache_clear()
    get_image_storage.cache_clear()
    try:
        with pytest.raises(ValueError, match="Unknown image_storage_provider"):
            get_image_storage()
    finally:
        get_settings.cache_clear()
        get_image_storage.cache_clear()
