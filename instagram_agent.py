import os
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

class InstagramAgent:
    def __init__(self):
        self.access_token = os.getenv('FACEBOOK_ACCESS_TOKEN')
        self.instagram_account_id = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID')
        self.base_url = "https://graph.facebook.com/v22.0"
        self.last_error: Optional[Dict[str, Any]] = None
        
        if not self.access_token or not self.instagram_account_id:
            raise ValueError("Missing required environment variables: FACEBOOK_ACCESS_TOKEN and INSTAGRAM_BUSINESS_ACCOUNT_ID")
    
    def create_media_container(self, image_url: str, caption: str) -> Optional[str]:
        """
        Create a media container for Instagram post
        Returns the container ID if successful
        """
        # Validate image URL first
        from services.image_upload_service import ImageUploadService
        if not ImageUploadService.validate_image_url_for_instagram(image_url):
            print(f"❌ Image URL failed Instagram validation: {image_url}")
            self.last_error = {
                'stage': 'validate_url', 
                'status': 400, 
                'error': {'message': 'Image URL does not meet Instagram requirements'}
            }
            return None
        
        url = f"{self.base_url}/{self.instagram_account_id}/media"
        
        # Graph API for Instagram requires image_url accessible publicly
        # Send as form data for compatibility
        data = {
            'image_url': image_url,
            'caption': caption,
            'access_token': self.access_token
        }
        
        print(f"📸 Creating Instagram media container:")
        print(f"   API URL: {url}")
        print(f"   Image URL: {image_url}")
        print(f"   Caption: {caption[:100]}...")
        print(f"   Account ID: {self.instagram_account_id}")
        print(f"   Access Token: {self.access_token[:20]}...")
        
        try:
            response = requests.post(url, data=data)
            
            print(f"📊 Instagram API Response:")
            print(f"   Status Code: {response.status_code}")
            print(f"   Response Headers: {dict(response.headers)}")
            print(f"   Response Body: {response.text}")
            
            # Do not raise immediately; inspect body for errors first
            if response.status_code >= 400:
                try:
                    err = response.json()
                except Exception:
                    err = {'raw': response.text}
                print(f"❌ Instagram API error creating container: {err}")
                self.last_error = {'stage': 'create_container', 'status': response.status_code, 'error': err}
                return None
            
            data = response.json()
            container_id = data.get('id')
            
            if container_id:
                print(f"✅ Media container created: {container_id}")
            else:
                print(f"❌ No container ID in response: {data}")
            
            return container_id
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error creating media container: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"📄 Error response: {e.response.text}")
                print(f"📊 Error status: {e.response.status_code}")
                self.last_error = {
                    'stage': 'create_container',
                    'status': e.response.status_code,
                    'error': getattr(e.response, 'text', None)
                }
            return None
    
    def publish_media(self, creation_id: str) -> Optional[str]:
        """
        Publish the media container to Instagram
        Returns the published media ID if successful
        """
        url = f"{self.base_url}/{self.instagram_account_id}/media_publish"
        
        data = {
            'creation_id': creation_id,
            'access_token': self.access_token
        }
        
        try:
            response = requests.post(url, data=data)
            if response.status_code >= 400:
                try:
                    err = response.json()
                except Exception:
                    err = {'raw': response.text}
                print(f"❌ Instagram API error publishing media: {err}")
                self.last_error = {'stage': 'publish_media', 'status': response.status_code, 'error': err}
                return None
            
            data = response.json()
            return data.get('id')
            
        except requests.exceptions.RequestException as e:
            print(f"Error publishing media: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response: {e.response.text}")
                self.last_error = {
                    'stage': 'publish_media',
                    'status': e.response.status_code if hasattr(e.response, 'status_code') else None,
                    'error': getattr(e.response, 'text', None)
                }
            return None
    
    def post_to_instagram(self, image_url: str, caption: str) -> Dict[str, Any]:
        """
        Complete workflow to post an image to Instagram
        """
        result = {
            'success': False,
            'container_id': None,
            'media_id': None,
            'error': None
        }
        
        # Step 1: Create media container
        self.last_error = None
        container_id = self.create_media_container(image_url, caption)
        if not container_id:
            result['error'] = "Failed to create media container"
            if self.last_error:
                result['error_details'] = self.last_error
            return result
        
        result['container_id'] = container_id
        
        # Step 2: Publish media
        media_id = self.publish_media(container_id)
        if not media_id:
            result['error'] = "Failed to publish media"
            if self.last_error:
                result['error_details'] = self.last_error
            return result
        
        result['media_id'] = media_id
        result['success'] = True
        
        return result