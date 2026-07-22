import os
import tempfile
from typing import Any, Dict, Optional
import requests
from requests import Response
from requests.exceptions import RequestException
from dotenv import load_dotenv

load_dotenv()


class FacebookAgent:
    """Simple helper for posting to Facebook with optional media."""

    def __init__(self) -> None:
        self.access_token = os.getenv("FACEBOOK_ACCESS_TOKEN")
        self.page_id = os.getenv("FACEBOOK_PAGE_ID")
        
        if not self.access_token:
            raise ValueError("Missing required environment variable FACEBOOK_ACCESS_TOKEN")
        
        if not self.page_id:
            raise ValueError("Missing required environment variable FACEBOOK_PAGE_ID")
        
        self.base_url = "https://graph.facebook.com/v22.0"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
        }
        
        self.last_error: Optional[Dict[str, Any]] = None

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

    def upload_photo(self, image_path: str, caption: str) -> Optional[str]:
        """Upload photo to Facebook and return photo ID"""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        self.last_error = None
        try:
            # Upload photo to Facebook Page
            upload_url = f"{self.base_url}/{self.page_id}/photos"
            
            with open(image_path, "rb") as image_file:
                files = {
                    'source': image_file,
                    'caption': (None, caption),
                }
                # Include access_token in the data, not files, for this endpoint
                data = {
                    'access_token': self.access_token
                }
                
                upload_response = requests.post(
                    upload_url,
                    files=files,
                    data=data
                )
            
            if upload_response.status_code >= 400:
                error_payload = upload_response.json() if upload_response.content else {"raw": upload_response.text}
                self.last_error = {
                    "stage": "upload_photo",
                    "status": upload_response.status_code,
                    "error": error_payload,
                }
                return None
            
            upload_data = upload_response.json()
            photo_id = upload_data.get('id')
            
            return photo_id
            
        except RequestException as exc:
            self.last_error = {
                "stage": "upload_photo",
                "error": str(exc),
                "image_path": image_path,
            }
            return None

    def create_post(self, text: str, photo_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Create a Facebook post"""
        
        post_url = f"{self.base_url}/{self.page_id}/feed"
        
        post_payload = {
            "message": text,
            "access_token": self.access_token
        }
        
        # Add photo if provided
        if photo_id:
            # For photo posts, we can use the photo_id as attached_media
            post_payload["attached_media[0]"] = {"media_fbid": photo_id}
        
        self.last_error = None
        try:
            response = requests.post(
                post_url,
                headers=self.headers,
                data=post_payload
            )
        except RequestException as exc:
            self.last_error = {
                "stage": "create_post",
                "error": str(exc),
                "payload": post_payload,
            }
            return None

        if response.status_code >= 400:
            try:
                error_payload = response.json()
            except ValueError:
                error_payload = {"raw": response.text}
            self.last_error = {
                "stage": "create_post",
                "status": response.status_code,
                "error": error_payload,
            }
            return None

        try:
            return response.json()
        except ValueError:
            self.last_error = {
                "stage": "create_post",
                "status": response.status_code,
                "error": {"raw": response.text},
            }
            return None

    def post_to_facebook(
        self,
        text: str,
        *,
        image_path: Optional[str] = None,
        image_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "success": False,
            "post": None,
            "photo_id": None,
            "error": None,
        }

        local_path = image_path
        temp_path: Optional[str] = None

        try:
            if local_path and not os.path.exists(local_path):
                raise FileNotFoundError(f"Image not found: {local_path}")

            if not local_path and image_url:
                temp_path = self._download_image(image_url)
                local_path = temp_path

            photo_id: Optional[str] = None
            if local_path:
                photo_id = self.upload_photo(local_path, text)
                if not photo_id:
                    result["error"] = "Failed to upload photo to Facebook"
                    if self.last_error:
                        result["error_details"] = self.last_error
                    return result
                result["photo_id"] = photo_id

            post_data = self.create_post(text, photo_id)
            if not post_data:
                result["error"] = "Failed to publish post to Facebook"
                if self.last_error:
                    result["error_details"] = self.last_error
                return result

            result["post"] = post_data
            result["success"] = True
            result["text"] = text
            return result
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass