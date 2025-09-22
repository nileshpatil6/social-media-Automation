#!/usr/bin/env python3
"""
Simple test for Instagram posting without requiring the web server
"""

import os
import sys
from dotenv import load_dotenv

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

def test_instagram_direct():
    """Test Instagram agent directly"""
    print("🧪 Direct Instagram API Test")
    print("=" * 40)
    
    try:
        from instagram_agent import InstagramAgent
        
        agent = InstagramAgent()
        print("✅ Instagram agent initialized")
        print(f"   Account ID: {agent.instagram_account_id}")
        print(f"   Access Token: {agent.access_token[:20]}...")
        
        # Test with a publicly accessible image URL
        test_image_url = "https://images.unsplash.com/photo-1503023345310-bd7c1de61c7d?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8aHVtYW58ZW58MHx8MHx8fDA%3D&w=1000&q=80"
        test_caption = "Test post from AI Advertisement System 🤖 #test #automation #ai"
        
        print(f"\n📸 Testing with public image URL:")
        print(f"   URL: {test_image_url}")
        print(f"   Caption: {test_caption}")
        
        result = agent.post_to_instagram(test_image_url, test_caption)
        
        print(f"\n📊 Result:")
        print(f"   Success: {result['success']}")
        
        if result['success']:
            print(f"   Container ID: {result['container_id']}")
            print(f"   Media ID: {result['media_id']}")
            print("🎉 Instagram posting works!")
        else:
            print(f"   Error: {result['error']}")
            print("❌ Instagram posting failed")
        
        return result['success']
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def test_credentials():
    """Test if we have valid credentials"""
    print("🔑 Checking Instagram Credentials")
    print("=" * 40)
    
    facebook_token = os.getenv('FACEBOOK_ACCESS_TOKEN')
    instagram_id = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID')
    
    if not facebook_token or facebook_token == "your_facebook_access_token_here":
        print("❌ Invalid Facebook access token")
        print("💡 Get token from: https://developers.facebook.com/tools/explorer/")
        return False
    
    if not instagram_id or instagram_id == "your_instagram_business_account_id_here":
        print("❌ Invalid Instagram business account ID")
        print("💡 Get ID from Instagram Business Account settings")
        return False
    
    print("✅ Valid credentials found")
    print(f"   Facebook Token: {facebook_token[:20]}...")
    print(f"   Instagram ID: {instagram_id}")
    
    return True

def main():
    """Run simple Instagram tests"""
    print("🧪 Simple Instagram Test")
    print("=" * 50)
    
    # Test credentials first
    if not test_credentials():
        print("\n❌ Cannot proceed without valid credentials")
        return False
    
    print("\n")
    
    # Test direct posting
    success = test_instagram_direct()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Instagram posting is working!")
        print("💡 You can now use the web interface safely")
    else:
        print("❌ Instagram posting failed")
        print("💡 Check the error messages above and verify:")
        print("   1. Your Facebook access token is valid and has Instagram permissions")
        print("   2. Your Instagram account is a Business account")
        print("   3. The Business account is connected to your Facebook page")
    
    return success

if __name__ == "__main__":
    main()