"""
Get the correct Page Access Token and Instagram Business Account ID
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

USER_ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN")
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")

def get_pages_and_tokens():
    """Get all pages and their access tokens"""
    print("\n🔍 Fetching your Facebook Pages...")
    print("=" * 80)
    
    url = "https://graph.facebook.com/v21.0/me/accounts"
    params = {
        "access_token": USER_ACCESS_TOKEN,
        "fields": "id,name,access_token,instagram_business_account"
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        pages = data.get("data", [])
        
        if not pages:
            print("\n❌ No Facebook Pages found!")
            print("\n📌 Make sure:")
            print("   1. You have a Facebook Page")
            print("   2. You are an admin of the page")
            print("   3. Your access token has 'pages_show_list' permission")
            return None, None
        
        print(f"\n✅ Found {len(pages)} page(s):\n")
        
        target_page = None
        for i, page in enumerate(pages, 1):
            page_id = page.get("id")
            page_name = page.get("name")
            has_ig = "instagram_business_account" in page
            
            print(f"{i}. {page_name}")
            print(f"   Page ID: {page_id}")
            print(f"   Instagram Connected: {'✅ Yes' if has_ig else '❌ No'}")
            
            if has_ig:
                ig_account = page["instagram_business_account"]
                ig_id = ig_account.get("id")
                print(f"   Instagram Account ID: {ig_id}")
            
            print()
            
            if page_id == FACEBOOK_PAGE_ID:
                target_page = page
        
        if target_page:
            return target_page, pages
        else:
            print(f"⚠️  Page ID {FACEBOOK_PAGE_ID} not found in your pages!")
            return None, pages
    else:
        print(f"\n❌ Error: {response.status_code}")
        error = response.json()
        print(error)
        
        if response.status_code == 400:
            print("\n📌 Your token might be expired or invalid!")
            print("   Go to: https://developers.facebook.com/tools/explorer/")
            print("   And generate a new User Access Token with these permissions:")
            print("   • pages_show_list")
            print("   • pages_read_engagement")
            print("   • instagram_basic")
            print("   • instagram_content_publish")
            print("   • business_management")
        
        return None, None

def test_page_token(page_access_token, instagram_id):
    """Test if the page token works for Instagram posting"""
    print("\n🔍 Testing Instagram Access with Page Token...")
    print("=" * 80)
    
    # Test 1: Get Instagram account info
    url = f"https://graph.facebook.com/v21.0/{instagram_id}"
    params = {
        "fields": "id,username,name,profile_picture_url,followers_count",
        "access_token": page_access_token
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Instagram Account Info:")
        print(f"   ID: {data.get('id')}")
        print(f"   Username: @{data.get('username')}")
        print(f"   Name: {data.get('name')}")
        print(f"   Followers: {data.get('followers_count', 'N/A')}")
        
        # Test 2: Check media endpoint
        print("\n🔍 Testing Media Endpoint...")
        media_url = f"https://graph.facebook.com/v21.0/{instagram_id}/media"
        media_params = {
            "fields": "id",
            "limit": 1,
            "access_token": page_access_token
        }
        
        media_response = requests.get(media_url, params=media_params)
        
        if media_response.status_code == 200:
            print("   ✅ Media endpoint accessible - posting should work!")
            return True
        else:
            print(f"   ❌ Media endpoint error: {media_response.status_code}")
            print(f"   {media_response.json()}")
            return False
    else:
        print(f"\n❌ Cannot access Instagram account: {response.status_code}")
        print(response.json())
        return False

def main():
    print("\n" + "=" * 80)
    print("   FACEBOOK PAGE ACCESS TOKEN GENERATOR")
    print("=" * 80)
    
    if not USER_ACCESS_TOKEN:
        print("\n❌ FACEBOOK_ACCESS_TOKEN not found in .env file!")
        print("\n📌 Steps to fix:")
        print("   1. Go to: https://developers.facebook.com/tools/explorer/")
        print("   2. Select your app")
        print("   3. Click 'Generate Access Token'")
        print("   4. Select these permissions:")
        print("      • pages_show_list")
        print("      • pages_read_engagement")
        print("      • instagram_basic")
        print("      • instagram_content_publish")
        print("      • business_management")
        print("   5. Copy the token and add to .env as FACEBOOK_ACCESS_TOKEN")
        return
    
    print(f"\n📝 Current Configuration:")
    print(f"   Facebook Page ID: {FACEBOOK_PAGE_ID}")
    print(f"   Token Type: User Access Token (first 20 chars): {USER_ACCESS_TOKEN[:20]}...")
    
    # Get pages
    target_page, all_pages = get_pages_and_tokens()
    
    if not target_page:
        if all_pages:
            print("\n📌 Available pages above - update FACEBOOK_PAGE_ID in .env to one of them")
        return
    
    # Extract info
    page_name = target_page.get("name")
    page_id = target_page.get("id")
    page_token = target_page.get("access_token")
    
    if not page_token:
        print("\n❌ Could not get page access token!")
        print("   This might be a permissions issue with your User Access Token")
        return
    
    print("\n" + "=" * 80)
    print("   ✅ FOUND YOUR PAGE")
    print("=" * 80)
    print(f"\nPage: {page_name}")
    print(f"Page ID: {page_id}")
    
    # Check for Instagram
    if "instagram_business_account" not in target_page:
        print("\n❌ No Instagram Business Account connected to this page!")
        print("\n📌 Steps to connect:")
        print(f"   1. Go to: https://www.facebook.com/{page_id}")
        print("   2. Click Settings → Instagram")
        print("   3. Click 'Connect Account'")
        print("   4. Make sure it's a Business or Creator account")
        return
    
    ig_account = target_page["instagram_business_account"]
    ig_id = ig_account.get("id")
    
    print(f"\n✅ Instagram Business Account ID: {ig_id}")
    
    # Test the page token
    if test_page_token(page_token, ig_id):
        print("\n\n" + "=" * 80)
        print("   ✅ SUCCESS - UPDATE YOUR .ENV FILE")
        print("=" * 80)
        print("\n📝 Replace these values in your .env file:\n")
        print(f"FACEBOOK_ACCESS_TOKEN={page_token}")
        print(f"INSTAGRAM_BUSINESS_ACCOUNT_ID={ig_id}")
        print(f"FACEBOOK_PAGE_ID={page_id}")
        print("\n⚠️  IMPORTANT: Use the PAGE ACCESS TOKEN above, not your user token!")
        print("   Page tokens have different permissions and work for posting.")
        
        # Show token info
        print(f"\n📊 Token Info:")
        print(f"   User Token (old):  {USER_ACCESS_TOKEN[:30]}...")
        print(f"   Page Token (new):  {page_token[:30]}...")
        print(f"\n   The page token will work for Instagram posting!")
    else:
        print("\n\n" + "=" * 80)
        print("   ⚠️  VERIFICATION FAILED")
        print("=" * 80)
        print("\n📌 The page token was obtained but couldn't access Instagram.")
        print("   This usually means:")
        print("   1. Instagram account is not a Business account")
        print("   2. Instagram account is not properly connected to the Facebook Page")
        print("   3. Missing permissions on the original user token")

if __name__ == "__main__":
    main()
