import os
import tempfile
import requests
from typing import Any, Dict, Optional
from dotenv import load_dotenv

# Import Google libraries, but handle if they're not available
try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google.auth.exceptions import RefreshError
    import json
    GOOGLE_LIBRARIES_AVAILABLE = True
except ImportError:
    GOOGLE_LIBRARIES_AVAILABLE = False
    build = None
    MediaFileUpload = None
    Credentials = None
    Request = None
    RefreshError = None
    json = None

load_dotenv()


class YouTubeAgent:
    """Helper for posting to YouTube with videos or image-based content."""

    def __init__(self) -> None:
        if not GOOGLE_LIBRARIES_AVAILABLE:
            raise ImportError(
                "Google API libraries not available. "
                "Install them with: pip install google-api-python-client google-auth"
            )
        
        # YouTube upload operations require OAuth 2.0 authentication
        self.oauth_client_secrets_file = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE")
        self.oauth_credentials_file = os.getenv("YOUTUBE_CREDENTIALS_FILE")
        
        if not (self.oauth_client_secrets_file and self.oauth_credentials_file):
            raise ValueError(
                "Missing required environment variables. "
                "YouTube upload operations require OAuth 2.0 authentication. "
                "Set both YOUTUBE_CLIENT_SECRETS_FILE and YOUTUBE_CREDENTIALS_FILE."
            )
        
        # Build the YouTube service using OAuth
        self.youtube = self._get_authenticated_service()
        
        self.last_error: Optional[Dict[str, Any]] = None

    def _get_authenticated_service(self):
        """Get authenticated YouTube service using OAuth credentials."""
        try:
            # This is a simplified version - in real applications, you'd need
            # to handle the full OAuth flow properly
            credentials = None
            
            # Load existing credentials
            if os.path.exists(self.oauth_credentials_file):
                with open(self.oauth_credentials_file, 'r') as token:
                    credentials = Credentials.from_authorized_user_info(json.load(token))
            
            # Refresh if needed
            if credentials and credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                    # Save the refreshed credentials
                    with open(self.oauth_credentials_file, 'w') as token:
                        token.write(credentials.to_json())
                except RefreshError:
                    # If refresh fails, credentials are invalid
                    credentials = None
            
            if not credentials:
                raise ValueError("OAuth credentials are not valid or available")
            
            return build('youtube', 'v3', credentials=credentials)
        except Exception as e:
            raise ValueError(f"Failed to authenticate with YouTube: {str(e)}")

    def _download_file(self, file_url: str) -> str:
        """Download a file from URL and save temporarily"""
        try:
            response = requests.get(file_url, stream=True, timeout=30)
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            self.last_error = {
                "stage": "download_file",
                "error": str(exc),
                "url": file_url,
            }
            raise

        # Get file extension from content type or URL
        content_type = response.headers.get("Content-Type", "").lower()
        if "video" in content_type:
            ext = ".mp4"  # Default to mp4 for video content
        elif "png" in content_type:
            ext = ".png"
        elif "jpeg" in content_type or "jpg" in content_type:
            ext = ".jpg"
        else:
            ext = ".tmp"  # Default extension

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        try:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    tmp.write(chunk)
        finally:
            tmp.close()
        return tmp.name

    def upload_video(
        self, 
        file_path: str, 
        title: str, 
        description: str = "", 
        tags: list = None,
        privacy_status: str = "private"
    ) -> Optional[Dict[str, Any]]:
        """Upload a video file to YouTube"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        if tags is None:
            tags = []

        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': '22'  # People & Blogs, can be changed as needed
            },
            'status': {
                'privacyStatus': privacy_status
            }
        }

        self.last_error = None
        try:
            if MediaFileUpload is None:
                raise ImportError("MediaFileUpload not available. Google API libraries not properly installed.")
                
            media = MediaFileUpload(file_path, chunksize=1024*1024, resumable=True)
            
            request = self.youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            # Execute the upload
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    print(f"Uploaded {int(status.progress() * 100)}%")
            
            return {
                "success": True,
                "video_id": response.get("id"),
                "video_url": f"https://www.youtube.com/watch?v={response.get('id')}",
                "response": response
            }
            
        except Exception as exc:
            self.last_error = {
                "stage": "upload_video",
                "error": str(exc),
                "file_path": file_path,
            }
            return None

    def post_to_youtube(
        self,
        title: str,
        description: str = "",
        *,
        file_path: Optional[str] = None,
        file_url: Optional[str] = None,
        tags: list = None,
        privacy_status: str = "private"
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "success": False,
            "video": None,
            "error": None,
        }

        local_path = file_path
        temp_path: Optional[str] = None

        try:
            if local_path and not os.path.exists(local_path):
                raise FileNotFoundError(f"File not found: {local_path}")

            if not local_path and file_url:
                temp_path = self._download_file(file_url)
                local_path = temp_path

            if not local_path:
                result["error"] = "Either file_path or file_url must be provided"
                return result

            # Determine file type
            import mimetypes
            mime_type, _ = mimetypes.guess_type(local_path)
            
            if not mime_type or not mime_type.startswith('video'):
                result["error"] = "YouTube primarily accepts video files. This implementation focuses on video uploads. For images, consider converting to video first."
                return result

            upload_result = self.upload_video(
                file_path=local_path,
                title=title,
                description=description,
                tags=tags,
                privacy_status=privacy_status
            )
            
            if not upload_result:
                result["error"] = "Failed to upload video to YouTube"
                if self.last_error:
                    result["error_details"] = self.last_error
                return result

            result["video"] = upload_result
            result["success"] = True
            result["title"] = title
            return result
            
        except Exception as e:
            result["error"] = str(e)
            return result
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass