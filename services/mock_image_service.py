import os
import uuid
from typing import Dict, Any
from PIL import Image, ImageDraw, ImageFont
import textwrap

class MockImageService:
    """
    Mock image generation service for testing when external APIs are unavailable
    """
    
    def __init__(self):
        self.storage_path = os.getenv('STORAGE_PATH', './generated_images')
        os.makedirs(self.storage_path, exist_ok=True)
    
    def generate_image(self, prompt_data: Dict[str, Any], retry_count: int = 0) -> Dict[str, Any]:
        """
        Generate a mock advertisement image with the prompt text
        """
        try:
            # Extract prompt info
            main_prompt = prompt_data.get('prompt', 'Advertisement')
            topic = prompt_data.get('original_topic', 'Product')
            
            # Create image
            width, height = 512, 512  # Square format
            background_color = '#f0f0f0'
            text_color = '#333333'
            accent_color = '#4CAF50'
            
            # Create image
            img = Image.new('RGB', (width, height), background_color)
            draw = ImageDraw.Draw(img)
            
            # Try to use a nice font, fall back to default
            try:
                title_font = ImageFont.truetype("arial.ttf", 32)
                subtitle_font = ImageFont.truetype("arial.ttf", 20)
                text_font = ImageFont.truetype("arial.ttf", 16)
            except:
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
                text_font = ImageFont.load_default()
            
            # Draw accent rectangle
            draw.rectangle([0, 0, width, 80], fill=accent_color)
            
            # Draw title
            title_text = "MOCK ADVERTISEMENT"
            title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
            title_width = title_bbox[2] - title_bbox[0]
            title_x = (width - title_width) // 2
            draw.text((title_x, 20), title_text, fill='white', font=title_font)
            
            # Draw topic
            topic_y = 120
            topic_bbox = draw.textbbox((0, 0), topic, font=subtitle_font)
            topic_width = topic_bbox[2] - topic_bbox[0]
            topic_x = (width - topic_width) // 2
            draw.text((topic_x, topic_y), topic, fill=text_color, font=subtitle_font)
            
            # Draw wrapped prompt text
            prompt_y = 180
            wrapped_text = textwrap.fill(main_prompt, width=45)
            lines = wrapped_text.split('\n')
            
            line_height = 25
            for i, line in enumerate(lines[:8]):  # Max 8 lines
                line_bbox = draw.textbbox((0, 0), line, font=text_font)
                line_width = line_bbox[2] - line_bbox[0]
                line_x = (width - line_width) // 2
                draw.text((line_x, prompt_y + i * line_height), line, fill=text_color, font=text_font)
            
            # Draw AI-generated badge
            badge_y = height - 60
            badge_text = "🤖 AI Generated Mock"
            badge_bbox = draw.textbbox((0, 0), badge_text, font=text_font)
            badge_width = badge_bbox[2] - badge_bbox[0]
            badge_x = (width - badge_width) // 2
            draw.text((badge_x, badge_y), badge_text, fill=accent_color, font=text_font)
            
            # Save image
            image_filename = f"mock_ad_{uuid.uuid4().hex[:8]}.png"
            image_path = os.path.join(self.storage_path, image_filename)
            img.save(image_path, 'PNG')
            
            return {
                'success': True,
                'image_data': [{
                    'url': f"http://localhost:8000/images/{image_filename}",
                    'local_path': image_path
                }],
                'request_id': f"mock_{uuid.uuid4().hex[:8]}",
                'model_used': 'mock-generator',
                'retry_count': retry_count,
                'original_prompt': prompt_data
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Mock image generation failed: {str(e)}",
                'retry_count': retry_count,
                'original_prompt': prompt_data
            }
    
    def edit_image(self, image_url: str, edit_instructions: str, original_prompt: str) -> Dict[str, Any]:
        """
        Mock edit function - creates a new variation
        """
        # For mock, just generate a new image with edit instructions added
        prompt_data = {
            'prompt': f"{original_prompt} | EDITED: {edit_instructions}",
            'original_topic': 'Edited Product'
        }
        return self.generate_image(prompt_data)
    
    def download_image(self, image_url: str, save_path: str) -> bool:
        """
        Mock download - image is already saved locally
        """
        return True  # Mock images are already saved
    
    def validate_image_quality(self, image_path: str) -> Dict[str, Any]:
        """
        Mock validation - always returns good quality
        """
        if os.path.exists(image_path):
            return {
                'width': 512,
                'height': 512,
                'file_size': os.path.getsize(image_path),
                'quality_score': 8.0,
                'issues': [],
                'is_valid': True
            }
        else:
            return {
                'width': 0,
                'height': 0,
                'file_size': 0,
                'quality_score': 0.0,
                'issues': ['File not found'],
                'is_valid': False
            }