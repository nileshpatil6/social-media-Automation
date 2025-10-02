import os
import requests
import json
import time
from typing import Dict, Any, Optional, List
from PIL import Image
import io

class IdeogramService:
    def __init__(self):
        self.api_key = os.getenv('IDEOGRAM_API_KEY')
        if not self.api_key:
            raise ValueError("IDEOGRAM_API_KEY not found in environment variables")
        
        self.base_url = "https://api.ideogram.ai/v1"
        self.headers = {
            "Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum seconds between requests
    
    def _rate_limit(self):
        """Ensure we don't exceed rate limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        
        self.last_request_time = time.time()
    
    def generate_image(self, prompt_data: Dict[str, Any], retry_count: int = 0) -> Dict[str, Any]:
        """
        Generate an image using Ideogram API based on Gemini-generated prompt
        """
        self._rate_limit()
        
        # Extract prompt components
        main_prompt = prompt_data.get('prompt', '')
        negative_prompt = prompt_data.get('negative_prompt', '')
        style = prompt_data.get('style', 'REALISTIC')
        aspect_ratio = prompt_data.get('aspect_ratio', '1:1')
        
        # Enhance prompt with realistic photography modifiers to avoid anime/cartoon style
        photorealistic_prompt = f"{main_prompt}, photorealistic, professional photography, real life, high quality photograph, detailed realistic textures, natural lighting, shot on DSLR camera"
        
        # Strengthen negative prompt to explicitly avoid anime/cartoon styles
        enhanced_negative_prompt = f"{negative_prompt}, anime, cartoon, illustrated, drawn, painting, animated, manga, comic style, stylized, cel shaded, 2D art, artistic rendering, digital art, CGI, 3D render"
        
        # Map aspect ratios to Ideogram format (as shown in the API docs)
        aspect_ratio_map = {
            '1:1': '1x1',
            '16:9': '16x9', 
            '9:16': '9x16',
            '4:3': '4x3',
            '3:4': '3x4',
            '2:1': '2x1',
            '1:2': '1x2',
            '3:1': '3x1',
            '1:3': '1x3',
            '3:2': '3x2',
            '2:3': '2x3',
            '5:4': '5x4',
            '4:5': '4x5',
            '16:10': '16x10',
            '10:16': '10x16'
        }
        
        ideogram_aspect_ratio = aspect_ratio_map.get(aspect_ratio, '1x1')
        
        # Map styles to Ideogram format
        style_map = {
            'modern-commercial': 'REALISTIC',
            'flat-illustration': 'REALISTIC', 
            'photography': 'GENERAL',
            'realistic': 'GENERAL',
            'artistic': 'GENERAL',
            'AUTO': 'AUTO'
        }
        
        ideogram_style = style_map.get(style, 'REALISTIC')
        
        # Construct the request payload for Ideogram API v3
        payload = {
            "prompt": photorealistic_prompt,
            "aspect_ratio": ideogram_aspect_ratio,
            "rendering_speed": "QUALITY",
            "magic_prompt": "ON",
            "num_images": 1,
            "style_type": "REALISTIC"  # Force realistic style
        }
        
        # Add enhanced negative prompt
        if enhanced_negative_prompt:
            payload["negative_prompt"] = enhanced_negative_prompt
        
     
        
        try:
            response = requests.post(
                f"{self.base_url}/ideogram-v3/generate",
                headers=self.headers,
                json=payload,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'image_data': result.get('data', []),
                    'request_id': result.get('request_id'),
                    'model_used': 'ideogram-v3',
                    'retry_count': retry_count,
                    'original_prompt': prompt_data
                }
            else:
                error_msg = f"Ideogram API error: {response.status_code} - {response.text}"
                print(error_msg)
                
                return {
                    'success': False,
                    'error': error_msg,
                    'retry_count': retry_count,
                    'original_prompt': prompt_data
                }
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            print(error_msg)
            
            return {
                'success': False,
                'error': error_msg,
                'retry_count': retry_count,
                'original_prompt': prompt_data
            }
    
    def edit_image(self, image_url: str, edit_instructions: str, original_prompt: str) -> Dict[str, Any]:
        """
        Edit an existing image using Ideogram's edit capabilities
        """
        self._rate_limit()
        
        # For Ideogram, editing typically involves a new generation with modified prompt
        # Since direct image editing may not be available, we'll modify the prompt
        
        enhanced_prompt = f"{original_prompt} | EDIT: {edit_instructions}"
        
        edit_payload = {
            "prompt": enhanced_prompt,
            "aspect_ratio": "1x1",
            "rendering_speed": "QUALITY",
            "magic_prompt": "ON",
            "style_type": "GENERAL",
            "num_images": 1
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/ideogram-v3/generate",
                headers=self.headers,
                json=edit_payload,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'image_data': result.get('data', []),
                    'request_id': result.get('request_id'),
                    'edit_type': 'prompt_modification',
                    'edit_instructions': edit_instructions
                }
            else:
                return {
                    'success': False,
                    'error': f"Edit failed: {response.status_code} - {response.text}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Edit request failed: {str(e)}"
            }
    
    def download_image(self, image_url: str, save_path: str) -> bool:
        """
        Download generated image from Ideogram's URL
        """
        try:
            response = requests.get(image_url, timeout=30)
            
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                return True
            else:
                print(f"Failed to download image: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Error downloading image: {e}")
            return False
    
    def get_image_info(self, request_id: str) -> Dict[str, Any]:
        """
        Get information about a generated image using request ID
        """
        try:
            response = requests.get(
                f"{self.base_url}/images/{request_id}",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'data': response.json()
                }
            else:
                return {
                    'success': False,
                    'error': f"Failed to get image info: {response.status_code}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Error getting image info: {str(e)}"
            }
    
    def validate_image_quality(self, image_path: str) -> Dict[str, Any]:
        """
        Perform basic image quality validation
        """
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                file_size = os.path.getsize(image_path)
                
                # Basic quality checks
                quality_score = 10.0
                issues = []
                
                # Check minimum resolution
                if width < 512 or height < 512:
                    quality_score -= 3.0
                    issues.append("Low resolution")
                
                # Check file size (too small might indicate poor quality)
                if file_size < 50000:  # 50KB
                    quality_score -= 2.0
                    issues.append("Suspiciously small file size")
                
                # Check aspect ratio for square images
                aspect_ratio = width / height
                if abs(aspect_ratio - 1.0) > 0.1:  # Not square enough
                    quality_score -= 1.0
                    issues.append("Aspect ratio not square")
                
                return {
                    'width': width,
                    'height': height,
                    'file_size': file_size,
                    'quality_score': max(0, quality_score),
                    'issues': issues,
                    'is_valid': quality_score >= 7.0
                }
                
        except Exception as e:
            return {
                'width': 0,
                'height': 0,
                'file_size': 0,
                'quality_score': 0.0,
                'issues': [f"Failed to analyze image: {str(e)}"],
                'is_valid': False
            }