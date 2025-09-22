import os
import requests
import base64
from typing import Optional
import requests

class ImageUploadService:
    @staticmethod
    def _is_public_image_url(url: str) -> bool:
        """Return True if URL is publicly accessible and is an image/* content-type."""
        try:
            # Use HEAD first; some hosts may not support HEAD, fallback to GET with stream
            resp = requests.head(url, allow_redirects=True, timeout=8)
            if resp.status_code >= 400 or 'image' not in resp.headers.get('Content-Type', '').lower():
                # Fallback GET (stream) to check headers without downloading whole image
                resp = requests.get(url, allow_redirects=True, timeout=10, stream=True)
                if resp.status_code >= 400:
                    return False
                ctype = resp.headers.get('Content-Type', '').lower()
                return 'image' in ctype
            return True
        except Exception as e:
            print(f"❌ URL validation failed for {url}: {e}")
            return False
    """
    Service to upload images to publicly accessible URLs for Instagram posting
    """
    
    @staticmethod
    def upload_to_imgbb(image_path: str, api_key: str = None) -> Optional[str]:
        """
        Upload image to imgbb.com (free service)
        Returns public URL if successful
        """
        if not api_key:
            # You can get a free API key from https://api.imgbb.com/
            print("⚠️  No imgbb API key provided. Cannot upload to public URL.")
            return None
        
        try:
            with open(image_path, 'rb') as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            url = "https://api.imgbb.com/1/upload"
            payload = {
                'key': api_key,
                'image': image_data,
                'expiration': 3600  # 1 hour expiration
            }
            
            response = requests.post(url, data=payload)
            
            if response.status_code == 200:
                data = response.json()
                if data['success']:
                    # Prefer the direct image URL for Graph API compatibility
                    direct_url = data['data'].get('image', {}).get('url')
                    display_url = data['data'].get('display_url')
                    # Validate direct first, then display
                    public_url = None
                    if direct_url and ImageUploadService._is_public_image_url(direct_url):
                        public_url = direct_url
                    elif display_url and ImageUploadService._is_public_image_url(display_url):
                        public_url = display_url
                    print(f"✅ Image uploaded to imgbb: {public_url}")
                    print(f"🔍 Available URLs:")
                    print(f"   - image.url (direct): {direct_url}")
                    print(f"   - display_url: {display_url}")
                    print(f"   - url: {data['data'].get('url')}")
                    return public_url
                else:
                    print(f"❌ imgbb upload failed: {data}")
                    return None
            else:
                print(f"❌ imgbb API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error uploading to imgbb: {e}")
            return None
    
    @staticmethod
    def upload_to_postimg(image_path: str) -> Optional[str]:
        """
        Upload image to postimg.cc (no API key required)
        Returns public URL if successful
        """
        try:
            url = "https://postimg.cc/json"
            
            with open(image_path, 'rb') as image_file:
                files = {'upload': image_file}
                data = {'adult': 'no'}
                
                response = requests.post(url, files=files, data=data)
            
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'OK':
                    # Try to find a direct image URL (some fields may vary)
                    candidates = [
                        data.get('hotlink'),
                        data.get('image'),
                        data.get('url')
                    ]
                    public_url = None
                    for url in candidates:
                        if url and ImageUploadService._is_public_image_url(url):
                            public_url = url
                            break
                    print(f"✅ Image uploaded to postimg: {public_url}")
                    print(f"🔍 postimg response keys: {list(data.keys())}")
                    return public_url
                else:
                    print(f"❌ postimg upload failed: {data}")
                    return None
            else:
                print(f"❌ postimg API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error uploading to postimg: {e}")
            return None
    
    @staticmethod
    def get_public_url(image_path: str) -> Optional[str]:
        """
        Try multiple services to get a public URL for the image
        """
        print(f"🌐 Attempting to get public URL for: {image_path}")
        
        # Prefer imgbb first if API key is available to get a clean direct URL
        imgbb_key = os.getenv('IMGBB_API_KEY')
        if imgbb_key:
            public_url = ImageUploadService.upload_to_imgbb(image_path, imgbb_key)
            if public_url:
                return public_url
        
        # Fallback to postimg (no API key required)
        public_url = ImageUploadService.upload_to_postimg(image_path)
        if public_url:
            return public_url
        
        print("❌ Failed to upload image to any public service")
        print("💡 Suggestions:")
        print("   1. Add IMGBB_API_KEY to your .env file (free at https://api.imgbb.com/)")
        print("   2. Use ngrok to expose localhost publicly")
        print("   3. Deploy the app to a public server")
        
        return None