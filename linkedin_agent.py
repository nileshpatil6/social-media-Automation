import os
import tempfile
from typing import Any, Dict, Optional
import requests
from requests import Response
from requests.exceptions import RequestException
from dotenv import load_dotenv

load_dotenv()


class LinkedInAgent:
    """Simple helper for posting to LinkedIn with optional media."""

    def __init__(self) -> None:
        self.access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        self.person_urn = os.getenv("LINKEDIN_PERSON_URN")  # Changed to use person URN
        
        if not self.access_token:
            raise ValueError("Missing required environment variable LINKEDIN_ACCESS_TOKEN")
        
        if not self.person_urn:
            raise ValueError("Missing required environment variable LINKEDIN_PERSON_URN")
        
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        self.upload_url = "https://api.linkedin.com/v2/assets"
        self.post_url = "https://api.linkedin.com/v2/ugcPosts"
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

    def upload_media(self, image_path: str) -> Optional[str]:
        """Upload media to LinkedIn and return asset ID"""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        self.last_error = None
        try:
            # Step 1: Register the asset (using working approach from your example)
            register_payload = {
                "registerUploadRequest": {
                    "owner": self.person_urn,
                    "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                    "serviceRelationships": [
                        {
                            "relationshipType": "OWNER",
                            "identifier": "urn:li:userGeneratedContent"
                        }
                    ],
                    "supportedUploadMechanism": ["SYNCHRONOUS_UPLOAD"]
                }
            }
            
            register_response = requests.post(
                "https://api.linkedin.com/v2/assets?action=registerUpload",
                headers=self.headers,
                json=register_payload
            )
            
            if register_response.status_code >= 400:
                error_payload = register_response.json() if register_response.content else {"raw": register_response.text}
                self.last_error = {
                    "stage": "register_upload",
                    "status": register_response.status_code,
                    "error": error_payload,
                }
                return None
            
            register_data = register_response.json()
            upload_mechanism = register_data.get('value', {}).get('uploadMechanism', {})
            upload_url = upload_mechanism.get('com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest', {}).get('uploadUrl')
            asset = register_data.get('value', {}).get('asset')
            
            if not upload_url or not asset:
                self.last_error = {
                    "stage": "register_upload",
                    "status": register_response.status_code,
                    "error": "Failed to get upload URL or asset",
                }
                return None
            
            # Step 2: Upload the file
            with open(image_path, "rb") as image_file:
                upload_headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "image/jpeg",  # or appropriate image type
                    "media-type-family": "STILLIMAGE"
                }
                upload_response = requests.put(
                    upload_url,
                    headers=upload_headers,
                    data=image_file
                )
            
            if upload_response.status_code >= 400:
                error_payload = upload_response.json() if upload_response.content else {"raw": upload_response.text}
                self.last_error = {
                    "stage": "upload_file",
                    "status": upload_response.status_code,
                    "error": error_payload,
                }
                return None
            
            return asset  # Return asset instead of asset_id
            
        except RequestException as exc:
            self.last_error = {
                "stage": "upload_media",
                "error": str(exc),
                "image_path": image_path,
            }
            return None

    def create_post(self, text: str, asset: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Create a LinkedIn post"""
        
        # Create the post entity (using working approach from your example)
        post_payload = {
            "author": self.person_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": text
                    },
                    "shareMediaCategory": "IMAGE" if asset else "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        # Add media if provided
        if asset:
            post_payload["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [
                {
                    "status": "READY",
                    "media": asset,
                    "title": {"text": "Image"},
                    "description": {"text": text}
                }
            ]
        
        self.last_error = None
        try:
            response = requests.post(
                self.post_url,
                headers=self.headers,
                json=post_payload
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

    def post_to_linkedin(
        self,
        text: str,
        *,
        image_path: Optional[str] = None,
        image_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "success": False,
            "post": None,
            "asset_id": None,
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

            asset: Optional[str] = None
            if local_path:
                asset = self.upload_media(local_path)
                if not asset:
                    result["error"] = "Failed to upload media to LinkedIn"
                    if self.last_error:
                        result["error_details"] = self.last_error
                    return result
                result["asset_id"] = asset  # Keep the name for compatibility

            post_data = self.create_post(text, asset)
            if not post_data:
                result["error"] = "Failed to publish post to LinkedIn"
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