#!/usr/bin/env python3
"""
Test script to verify Ideogram URL direct usage
"""

import os
import sys
sys.path.append(os.path.dirname(__file__))

from services.image_upload_service import ImageUploadService

def test_ideogram_url_detection():
    """Test if the system can find and use Ideogram URLs directly"""
    
    # Test with an existing image file that should have a logged Ideogram URL
    test_image = "c:\\code\\.miscellanious\\n8ntocode\\generated_images\\dae7fa76-d9b2-4b6d-a899-d783bfd770a1_attempt_1.png"
    
    if os.path.exists(test_image):
        print(f"🔍 Testing Ideogram URL detection for: {test_image}")
        
        # Test the get_ideogram_url_for_image function
        ideogram_url = ImageUploadService.get_ideogram_url_for_image(test_image)
        
        if ideogram_url:
            print(f"✅ Found Ideogram URL: {ideogram_url}")
            
            # Test the full get_public_url function
            public_url = ImageUploadService.get_public_url(test_image)
            print(f"🌐 Public URL returned: {public_url}")
            
            if public_url == ideogram_url:
                print("✅ SUCCESS: System is using Ideogram URL directly!")
            else:
                print("⚠️ System fell back to re-uploading instead of using Ideogram URL")
        else:
            print("❌ No Ideogram URL found - system will try re-uploading")
    else:
        print(f"❌ Test image not found: {test_image}")
        
        # List available images
        images_dir = "c:\\code\\.miscellanious\\n8ntocode\\generated_images"
        if os.path.exists(images_dir):
            files = [f for f in os.listdir(images_dir) if f.endswith('.png')]
            print(f"Available images: {files[:5]}")  # Show first 5

if __name__ == "__main__":
    test_ideogram_url_detection()