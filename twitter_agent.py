import os
import tempfile
from typing import Any, Dict, Optional

import requests
from requests import Response
from requests.exceptions import RequestException
from requests_oauthlib import OAuth1
from dotenv import load_dotenv

load_dotenv()


class TwitterAgent:
    """Simple helper for posting tweets with optional media."""

    TWEET_CHARACTER_LIMIT = 280

    def __init__(self) -> None:
        self.api_key = os.getenv("TWITTER_API_KEY")
        self.api_secret = (
            os.getenv("TWITTER_API_SECRET_KEY")
            or os.getenv("TWITTER_API_SECRET")
        )
        self.access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        self.access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

        if not self.api_key or not self.api_secret:
            raise ValueError("Missing required environment variables TWITTER_API_KEY and TWITTER_API_SECRET_KEY")

        if not self.access_token or not self.access_token_secret:
            raise ValueError(
                "Missing Twitter user access tokens. Set TWITTER_ACCESS_TOKEN and TWITTER_ACCESS_TOKEN_SECRET"
            )

        self.auth = OAuth1(
            self.api_key,
            self.api_secret,
            self.access_token,
            self.access_token_secret,
        )

        self.upload_url = "https://upload.twitter.com/1.1/media/upload.json"
        self.tweet_url = "https://api.twitter.com/2/tweets"
        self.last_error: Optional[Dict[str, Any]] = None

    def _prepare_caption(self, caption: str) -> Dict[str, Any]:
        caption = (caption or "").strip()
        truncated = False
        if len(caption) > self.TWEET_CHARACTER_LIMIT:
            caption = caption[: self.TWEET_CHARACTER_LIMIT - 1].rstrip() + "\u2026"
            truncated = True
        return {"caption": caption, "truncated": truncated}

    def _infer_suffix(self, response: Response) -> str:
        content_type = response.headers.get("Content-Type", "").lower()
        if "png" in content_type:
            return ".png"
        if "jpeg" in content_type or "jpg" in content_type:
            return ".jpg"
        if "gif" in content_type:
            return ".gif"
        return ".img"

    def _download_image(self, image_url: str) -> str:
        try:
            response = requests.get(image_url, stream=True, timeout=30)
            response.raise_for_status()
        except RequestException as exc:
            self.last_error = {
                "stage": "download_image",
                "error": str(exc),
                "url": image_url,
            }
            raise

        suffix = self._infer_suffix(response)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        try:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    tmp.write(chunk)
        finally:
            tmp.close()
        return tmp.name

    def upload_media(self, image_path: str) -> Optional[str]:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        self.last_error = None
        try:
            with open(image_path, "rb") as media_file:
                files = {"media": media_file}
                response = requests.post(
                    self.upload_url,
                    files=files,
                    auth=self.auth,
                    timeout=30,
                )
        except RequestException as exc:
            self.last_error = {
                "stage": "upload_media",
                "error": str(exc),
                "image_path": image_path,
            }
            return None

        if response.status_code >= 400:
            error_payload: Dict[str, Any]
            try:
                error_payload = response.json()
            except ValueError:
                error_payload = {"raw": response.text}
            self.last_error = {
                "stage": "upload_media",
                "status": response.status_code,
                "error": error_payload,
            }
            return None

        data = response.json()
        media_id = data.get("media_id_string") or data.get("media_id")
        if not media_id:
            self.last_error = {
                "stage": "upload_media",
                "status": response.status_code,
                "error": data,
            }
            return None

        return str(media_id)

    def create_tweet(self, caption: str, media_ids: Optional[list] = None) -> Optional[Dict[str, Any]]:
        payload: Dict[str, Any] = {"text": caption}
        if media_ids:
            payload["media"] = {"media_ids": media_ids}

        self.last_error = None
        try:
            response = requests.post(
                self.tweet_url,
                json=payload,
                auth=self.auth,
                timeout=30,
            )
        except RequestException as exc:
            self.last_error = {
                "stage": "create_tweet",
                "error": str(exc),
                "payload": payload,
            }
            return None

        if response.status_code >= 400:
            try:
                error_payload = response.json()
            except ValueError:
                error_payload = {"raw": response.text}
            self.last_error = {
                "stage": "create_tweet",
                "status": response.status_code,
                "error": error_payload,
            }
            return None

        try:
            return response.json()
        except ValueError:
            self.last_error = {
                "stage": "create_tweet",
                "status": response.status_code,
                "error": {"raw": response.text},
            }
            return None

    def post_to_twitter(
        self,
        caption: str,
        *,
        image_path: Optional[str] = None,
        image_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "success": False,
            "tweet": None,
            "media_id": None,
            "error": None,
        }

        prepared = self._prepare_caption(caption)
        caption_text = prepared["caption"]
        result["caption_truncated"] = prepared["truncated"]

        local_path = image_path
        temp_path: Optional[str] = None

        try:
            if local_path and not os.path.exists(local_path):
                raise FileNotFoundError(f"Image not found: {local_path}")

            if not local_path and image_url:
                temp_path = self._download_image(image_url)
                local_path = temp_path

            media_id: Optional[str] = None
            if local_path:
                media_id = self.upload_media(local_path)
                if not media_id:
                    result["error"] = "Failed to upload media to Twitter"
                    if self.last_error:
                        result["error_details"] = self.last_error
                    return result
                result["media_id"] = media_id

            tweet_data = self.create_tweet(caption_text, [media_id] if media_id else None)
            if not tweet_data:
                result["error"] = "Failed to publish tweet"
                if self.last_error:
                    result["error_details"] = self.last_error
                return result

            result["tweet"] = tweet_data
            result["success"] = True
            result["caption"] = caption_text
            return result
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
