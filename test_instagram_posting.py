#!/usr/bin/env python3
"""
Test script to verify Instagram posting functionality
"""

import os
import sys
import requests
import json
from dotenv import load_dotenv

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

def test_image_upload_service():
    """Test the image upload service"""
    print("🧪 Testing Image Upload Service...")
    
    try:
        from services.image_upload_service import ImageUploadService
        
        # Check if we have a generated image to test with
        images_dir = "./generated_images"
        if not os.path.exists(images_dir):
            print("❌ No generated_images directory found")
            return False
            
        # Find any image file
        image_files = [f for f in os.listdir(images_dir) if f.endswith('.png')]
        if not image_files:
            print("❌ No image files found in generated_images")
            return False
        
        test_image_path = os.path.join(images_dir, image_files[0])
        print(f"📸 Testing with image: {test_image_path}")
        
        # Test the upload service
        public_url = ImageUploadService.get_public_url(test_image_path)
        
        if public_url:
            print(f"✅ Image upload successful: {public_url}")
            return True
        else:
            print("❌ Image upload failed")
            return False
            
    except Exception as e:
        print(f"❌ Image upload test error: {e}")
        return False

def test_instagram_agent():
    """Test the Instagram agent without actually posting"""
    print("\n🧪 Testing Instagram Agent...")
    
    try:
        from instagram_agent import InstagramAgent
        
        # Test initialization
        agent = InstagramAgent()
        print("✅ Instagram agent initialized")
        
        # Check if we have valid credentials
        if not agent.access_token or agent.access_token == "your_facebook_access_token_here":
            print("⚠️  No valid Facebook access token found")
            return False
            
        if not agent.instagram_account_id or agent.instagram_account_id == "your_instagram_business_account_id_here":
            print("⚠️  No valid Instagram account ID found")
            return False
            
        print(f"✅ Valid credentials found")
        print(f"   Account ID: {agent.instagram_account_id}")
        print(f"   Token: {agent.access_token[:20]}...")
        
        return True
        
    except ValueError as e:
        print(f"⚠️  Instagram agent error: {e}")
        return False
    except Exception as e:
        print(f"❌ Instagram agent test error: {e}")
        return False

def test_instagram_posting_endpoint():
    """Test the actual Instagram posting endpoint"""
    print("\n🧪 Testing Instagram Posting Endpoint...")
    
    # First we need to authenticate and get a token
    print("🔐 Getting authentication token...")
    
    # Try to register/login a test user
    auth_data = {
        "email": "test@example.com",
        "password": "testpassword123"
    }
    
    try:
        # Try login first
        login_response = requests.post("http://localhost:8000/auth/login", json=auth_data)
        
        if login_response.status_code == 200:
            token_data = login_response.json()
            auth_token = token_data['access_token']
            print("✅ Login successful")
        else:
            # Try registration
            register_response = requests.post("http://localhost:8000/auth/register", json=auth_data)
            
            if register_response.status_code == 200:
                token_data = register_response.json()
                auth_token = token_data['access_token']
                print("✅ Registration successful")
            else:
                print(f"❌ Authentication failed: {register_response.status_code}")
                print(f"   Response: {register_response.text}")
                return False
        
        # Now test the Instagram posting endpoint
        print("📤 Testing Instagram posting endpoint...")
        
        # Find an image to test with
        images_dir = "./generated_images"
        if os.path.exists(images_dir):
            image_files = [f for f in os.listdir(images_dir) if f.endswith('.png')]
            if image_files:
                test_filename = image_files[0]
                print(f"📸 Using test image: {test_filename}")
                
                # Prepare the form data
                form_data = {
                    'image_filename': test_filename,
                    'caption': 'Test posting from automated script 🤖 #test #automation',
                    'topic_id': '1'
                }
                
                headers = {
                    'Authorization': f'Bearer {auth_token}'
                }
                
                # Make the request
                response = requests.post(
                    "http://localhost:8000/post-to-instagram",
                    data=form_data,
                    headers=headers
                )
                
                print(f"📊 Instagram posting response:")
                print(f"   Status Code: {response.status_code}")
                print(f"   Response: {response.text}")
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        print("✅ Instagram posting successful!")
                        return True
                    else:
                        print(f"❌ Instagram posting failed: {result.get('error')}")
                        return False
                else:
                    print(f"❌ HTTP error: {response.status_code}")
                    return False
            else:
                print("❌ No image files found for testing")
                return False
        else:
            print("❌ No generated_images directory found")
            return False
            
    except Exception as e:
        print(f"❌ Endpoint test error: {e}")
        return False

def main():
    """Run all Instagram posting tests"""
    print("🧪 Instagram Posting Test Suite")
    print("=" * 50)
    
    tests = [
        ("Image Upload Service", test_image_upload_service),
        ("Instagram Agent", test_instagram_agent),
        ("Instagram Posting Endpoint", test_instagram_posting_endpoint)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name} Test")
        print("-" * 30)
        success = test_func()
        results.append((test_name, success))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:<30} {status}")
        if success:
            passed += 1
    
    print(f"\nResults: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All tests passed! Instagram posting is ready.")
    else:
        print(f"\n⚠️  {len(results) - passed} test(s) failed.")
        print("\n💡 Common fixes:")
        print("   1. Check your .env file has valid Facebook/Instagram credentials")
        print("   2. Ensure the web server is running (python app.py)")
        print("   3. Generate at least one advertisement first")
        print("   4. Add IMGBB_API_KEY for public image hosting")
        
    return passed == len(results)

if __name__ == "__main__":
    main()