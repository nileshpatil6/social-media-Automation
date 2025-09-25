import os
import requests
import base64
from typing import Optional
import requests
import json

class ImageUploadService:
    @staticmethod
    def get_ideogram_url_for_image(image_path: str) -> Optional[str]:
        """
        Get the logged Ideogram URL for an image file by extracting workflow_id from filename
        """
        try:
            # Extract workflow_id from filename (e.g., "dae7fa76-d9b2-4b6d-a899-d783bfd770a1_attempt_1.png")
            filename = os.path.basename(image_path)
            if '_attempt_' in filename:
                workflow_id = filename.split('_attempt_')[0]
                
                # Check the URL log file
                url_log_file = os.path.join(os.path.dirname(image_path), 'ideogram_urls.log')
                if os.path.exists(url_log_file):
                    with open(url_log_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            try:
                                log_entry = json.loads(line.strip())
                                if log_entry.get('workflow_id') == workflow_id:
                                    ideogram_url = log_entry.get('image_url')
                                    if ideogram_url:
                                        print(f"🎯 Found logged Ideogram URL for {filename}: {ideogram_url}")
                                        # Validate the URL is still accessible
                                        if ImageUploadService._is_public_image_url(ideogram_url):
                                            print(f"✅ Ideogram URL validated and accessible")
                                            return ideogram_url
                                        else:
                                            print(f"⚠️ Ideogram URL no longer accessible: {ideogram_url}")
                            except json.JSONDecodeError:
                                continue
                
                print(f"🔍 No logged Ideogram URL found for workflow: {workflow_id}")
            else:
                print(f"🔍 Image filename doesn't match workflow pattern: {filename}")
                
        except Exception as e:
            print(f"⚠️ Error checking for Ideogram URL: {e}")
        
        return None
    
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
    def upload_to_imgur(image_path: str, client_id: str = None) -> Optional[str]:
        """
        Upload image to Imgur (better Instagram compatibility)
        Get client ID from https://api.imgur.com/oauth2/addclient
        """
        if not client_id:
            client_id = os.getenv('IMGUR_CLIENT_ID')
        
        if not client_id:
            print("⚠️  No Imgur client ID provided. Cannot upload to Imgur.")
            return None
        
        try:
            url = "https://api.imgur.com/3/upload"
            
            with open(image_path, 'rb') as image_file:
                files = {'image': image_file}
                headers = {
                    'Authorization': f'Client-ID {client_id}'
                }
                
                response = requests.post(url, files=files, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data['success']:
                    public_url = data['data']['link']
                    print(f"✅ Image uploaded to Imgur: {public_url}")
                    return public_url
                else:
                    print(f"❌ Imgur upload failed: {data}")
                    return None
            else:
                print(f"❌ Imgur API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error uploading to Imgur: {e}")
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
        Get a public URL for the image file.
        First tries to use logged Ideogram URL, then falls back to re-uploading
        """
        if not os.path.exists(image_path):
            print(f"❌ Image file not found: {image_path}")
            return None
            
        print(f"🌐 Attempting to get public URL for: {image_path}")
        
        # First, try to get the original Ideogram URL
        ideogram_url = ImageUploadService.get_ideogram_url_for_image(image_path)
        if ideogram_url:
            print(f"🚀 Using original Ideogram URL directly: {ideogram_url}")
            return ideogram_url
        
        print(f"💡 No Ideogram URL available, trying image upload services...")
        
        # Try Imgur first (best for Instagram)
        imgur_client_id = os.getenv('IMGUR_CLIENT_ID')
        if imgur_client_id:
            public_url = ImageUploadService.upload_to_imgur(image_path, imgur_client_id)
            if public_url:
                return public_url
        
        # Try imgbb if API key is available
        imgbb_key = os.getenv('IMGBB_API_KEY')
        if imgbb_key:
            public_url = ImageUploadService.upload_to_imgbb(image_path, imgbb_key)
            if public_url:
                return public_url
        
        # Fallback to postimg (no API key required, but less reliable for Instagram)
        public_url = ImageUploadService.upload_to_postimg(image_path)
        if public_url:
            return public_url
        
        print("❌ Failed to upload image to any public service")
        print("💡 Suggestions to fix Instagram posting issues:")
        print("   1. Add IMGUR_CLIENT_ID to your .env file (best for Instagram, free at https://api.imgur.com/oauth2/addclient)")
        print("   2. Add IMGBB_API_KEY to your .env file (free at https://api.imgbb.com/)")
        print("   3. Use ngrok to expose localhost publicly")
        print("   4. Deploy the app to a public server with direct image URLs")
        print("   5. Instagram is picky about image hosts - some free services may not work")
        
        return None

    @staticmethod
    def validate_image_url_for_instagram(url: str) -> bool:
        """
        Test if an image URL is accessible and meets Instagram requirements
        """
        try:
            print(f"🔍 Validating image URL for Instagram: {url}")
            response = requests.head(url, timeout=10)
            
            # Check if accessible
            if response.status_code != 200:
                print(f"⚠️ Image URL not accessible: {response.status_code}")
                return False
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if not any(ct in content_type for ct in ['image/jpeg', 'image/png', 'image/jpg']):
                print(f"⚠️ Invalid content type for Instagram: {content_type}")
                return False
            
            # Check content length (Instagram has size limits)
            content_length = response.headers.get('content-length')
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                if size_mb > 8:  # Instagram limit is 8MB
                    print(f"⚠️ Image too large for Instagram: {size_mb:.1f}MB (max 8MB)")
                    return False
            
            print(f"✅ Image URL validated for Instagram")
            return True
            
        except Exception as e:
            print(f"⚠️ Error validating image URL: {e}")
            return False