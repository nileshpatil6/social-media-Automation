#!/usr/bin/env python3
"""
Test script to verify Ideogram API connection
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_ideogram_api():
    """Test Ideogram API with the correct endpoint"""
    
    api_key = os.getenv('IDEOGRAM_API_KEY')
    if not api_key:
        print("❌ IDEOGRAM_API_KEY not found in environment")
        return False
    
    print(f"🔑 Using API Key: {api_key[:10]}...")
    
    # Correct endpoint from your working JavaScript code
    url = "https://api.ideogram.ai/v1/ideogram-v3/generate"
    
    headers = {
        "Api-Key": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "prompt": "A futuristic city skyline at sunset",
        "aspect_ratio": "1x1",
        "rendering_speed": "DEFAULT",
        "magic_prompt": "AUTO",
        "style_type": "GENERAL",
        "num_images": 1
    }
    
    print("🚀 Testing Ideogram API...")
    print(f"📡 Endpoint: {url}")
    print(f"📝 Payload: {payload}")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📄 Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API Success!")
            print(f"📸 Response keys: {list(data.keys())}")
            return True
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"📄 Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request Error: {e}")
        return False

def test_mock_service():
    """Test mock image service as fallback"""
    
    print("\n🎭 Testing Mock Image Service...")
    
    try:
        # Add current directory to path
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        from services.mock_image_service import MockImageService
        
        mock_service = MockImageService()
        
        prompt_data = {
            'prompt': 'Test advertisement for summer sale',
            'original_topic': 'Summer Sale',
            'style': 'modern-commercial',
            'aspect_ratio': '1:1'
        }
        
        result = mock_service.generate_image(prompt_data)
        
        if result['success']:
            print("✅ Mock service working!")
            image_path = result['image_data'][0]['local_path']
            print(f"📸 Generated image: {image_path}")
            
            if os.path.exists(image_path):
                file_size = os.path.getsize(image_path)
                print(f"📏 File size: {file_size} bytes")
                return True
            else:
                print(f"❌ Image file not found: {image_path}")
                return False
        else:
            print(f"❌ Mock service failed: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Mock service error: {e}")
        return False

def main():
    """Run API tests"""
    
    print("🧪 Ideogram API Test Suite")
    print("=" * 40)
    
    # Test real API
    ideogram_success = test_ideogram_api()
    
    # Test mock service
    mock_success = test_mock_service()
    
    print("\n" + "=" * 40)
    print("📊 Test Results:")
    print(f"Ideogram API: {'✅ Working' if ideogram_success else '❌ Failed'}")
    print(f"Mock Service: {'✅ Working' if mock_success else '❌ Failed'}")
    
    if ideogram_success:
        print("\n🎉 Ideogram API is ready! Your system will use real AI generation.")
    elif mock_success:
        print("\n⚠️  Ideogram API failed, but mock service works. You can test the system with mock images.")
    else:
        print("\n❌ Both services failed. Check your API key and configuration.")
    
    return ideogram_success or mock_success

if __name__ == "__main__":
    main()