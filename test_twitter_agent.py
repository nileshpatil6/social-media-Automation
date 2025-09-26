import json
import os
from pathlib import Path

import pytest

from twitter_agent import TwitterAgent


class MockResponse:
    def __init__(self, status_code: int, payload: dict, headers: dict | None = None):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {"Content-Type": "application/json"}
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def twitter_env(monkeypatch):
    monkeypatch.setenv("TWITTER_API_KEY", "test_key")
    monkeypatch.setenv("TWITTER_API_SECRET_KEY", "test_secret")
    monkeypatch.setenv("TWITTER_ACCESS_TOKEN", "test_access")
    monkeypatch.setenv("TWITTER_ACCESS_TOKEN_SECRET", "test_access_secret")


def test_twitter_agent_post_with_local_image(tmp_path, monkeypatch):
    image_path = tmp_path / "sample.png"
    image_path.write_bytes(b"fake-bytes")

    def fake_post(url, *args, **kwargs):
        if "upload.twitter.com" in url:
            return MockResponse(200, {"media_id_string": "12345"})
        if "api.twitter.com/2/tweets" in url:
            body = kwargs.get("json", {})
            return MockResponse(201, {"data": {"id": "67890", "text": body.get("text")}})
        raise AssertionError(f"Unexpected POST url: {url}")

    monkeypatch.setattr("twitter_agent.requests.post", fake_post)

    agent = TwitterAgent()
    result = agent.post_to_twitter("Hello Twitter!", image_path=str(image_path))

    assert result["success"] is True
    assert result["media_id"] == "12345"
    assert result["tweet"]["data"]["id"] == "67890"
    assert result["caption"] == "Hello Twitter!"
    assert result["caption_truncated"] is False


def test_twitter_agent_post_with_remote_image(tmp_path, monkeypatch):
    downloaded_path = tmp_path / "remote.png"
    downloaded_path.write_bytes(b"remote-bytes")

    def fake_download(self, image_url: str):
        return str(downloaded_path)

    def fake_post(url, *args, **kwargs):
        if "upload.twitter.com" in url:
            return MockResponse(200, {"media_id_string": "22222"})
        if "api.twitter.com/2/tweets" in url:
            body = kwargs.get("json", {})
            return MockResponse(201, {"data": {"id": "33333", "text": body.get("text")}})
        raise AssertionError(f"Unexpected POST url: {url}")

    monkeypatch.setattr("twitter_agent.TwitterAgent._download_image", fake_download)
    monkeypatch.setattr("twitter_agent.requests.post", fake_post)

    agent = TwitterAgent()
    result = agent.post_to_twitter("Remote image caption", image_url="https://example.com/image.png")

    assert result["success"] is True
    assert result["media_id"] == "22222"
    assert result["tweet"]["data"]["id"] == "33333"
    assert result["caption"] == "Remote image caption"
    assert result["caption_truncated"] is False
    assert not downloaded_path.exists()

