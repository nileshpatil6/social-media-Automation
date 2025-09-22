#!/usr/bin/env python3
"""
Test script for the direct image posting functionality
"""
import requests
import json

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_IMAGE_URL = "https://picsum.photos/800/600.jpg"  # Random image for testing
TEST_CAPTION = "Testing direct image posting functionality! 📸 #test #automation"

def test_direct_post_endpoint():
    """Test the direct image posting endpoint without authentication"""
    print("🧪 Testing direct image posting endpoint...")
    
    # Test without authentication (should fail)
    print("\n1. Testing without authentication (should fail):")
    response = requests.post(
        f"{BASE_URL}/post-direct-image",
        json={
            "image_url": TEST_IMAGE_URL,
            "caption": TEST_CAPTION
        }
    )
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text}")
    
    # Test endpoint structure
    print("\n2. Testing endpoint existence:")
    try:
        response = requests.options(f"{BASE_URL}/post-direct-image")
        print(f"   Status: {response.status_code} (OPTIONS request)")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n3. Testing with invalid data (should fail):")
    response = requests.post(
        f"{BASE_URL}/post-direct-image",
        json={}
    )
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text}")

def test_registration_login():
    """Test user registration and login to get auth token"""
    print("\n🔐 Testing authentication flow...")
    
    # Test user registration
    print("\n1. Testing user registration:")
    test_user = {
        "email": f"test_direct_post@example.com",
        "password": "testpassword123"
    }
    
    response = requests.post(
        f"{BASE_URL}/auth/register",
        json=test_user
    )
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        print(f"   ✅ Registration successful! Token obtained.")
        return token
    else:
        print(f"   Response: {response.text}")
        
        # Try login instead
        print("\n2. Trying login instead:")
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json=test_user
        )
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print(f"   ✅ Login successful! Token obtained.")
            return token
        else:
            print(f"   Response: {response.text}")
            return None

def test_authenticated_direct_post(token):
    """Test direct image posting with authentication"""
    if not token:
        print("❌ No authentication token available")
        return
    
    print("\n📤 Testing authenticated direct image posting...")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "image_url": TEST_IMAGE_URL,
        "caption": TEST_CAPTION
    }
    
    response = requests.post(
        f"{BASE_URL}/post-direct-image",
        headers=headers,
        json=data
    )
    
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text}")
    
    if response.status_code == 200:
        print("   ✅ Direct image posting endpoint is working!")
    else:
        print("   ⚠️ Check the response for any issues")

if __name__ == "__main__":
    print("🚀 Starting Direct Image Posting Tests")
    print("=" * 50)
    
    # Test endpoint without auth
    test_direct_post_endpoint()
    
    # Test authentication
    token = test_registration_login()
    
    # Test with authentication
    test_authenticated_direct_post(token)
    
    print("\n" + "=" * 50)
    print("🏁 Testing completed!")