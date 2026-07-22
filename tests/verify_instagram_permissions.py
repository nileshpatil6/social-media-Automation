"""
Verify Instagram Business Account permissions and get correct account ID
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

FACEBOOK_ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN")
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")

def check_token_permissions():
    """Check what permissions the access token has"""
    print("\n🔍 Checking Access Token Permissions...")
    print("=" * 60)
    
    url = "https://graph.facebook.com/v21.0/me/permissions"
    params = {"access_token": FACEBOOK_ACCESS_TOKEN}
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        permissions = data.get("data", [])
        
        print("\n✅ Current Permissions:")
        granted = [p["permission"] for p in permissions if p["status"] == "granted"]
        declined = [p["permission"] for p in permissions if p["status"] == "declined"]
        
        print("\n✓ Granted:")
        for perm in granted:
            print(f"  • {perm}")
        
        if declined:
            print("\n✗ Declined:")
            for perm in declined:
                print(f"  • {perm}")
        
        # Check required Instagram permissions
        required = [
            "instagram_basic",
            "instagram_content_publish",
            "pages_show_list",
            "pages_read_engagement",
            "business_management"
        ]
        
        missing = [p for p in required if p not in granted]
        if missing:
            print("\n⚠️  MISSING REQUIRED PERMISSIONS:")
            for perm in missing:
                print(f"  • {perm}")
            print("\n📌 You need to regenerate your token with these permissions!")
        else:
            print("\n✅ All required permissions are granted!")
        
        return granted
    else:
        print(f"\n❌ Error checking permissions: {response.status_code}")
        print(response.json())
        return []

def get_facebook_page_info():
    """Get Facebook Page information"""
    print("\n\n🔍 Checking Facebook Page...")
    print("=" * 60)
    
    url = f"https://graph.facebook.com/v21.0/{FACEBOOK_PAGE_ID}"
    params = {
        "fields": "id,name,access_token,instagram_business_account",
        "access_token": FACEBOOK_ACCESS_TOKEN
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Page Name: {data.get('name')}")
        print(f"✅ Page ID: {data.get('id')}")
        
        if "instagram_business_account" in data:
            ig_account = data["instagram_business_account"]
            print(f"\n✅ Connected Instagram Business Account:")
            print(f"   ID: {ig_account.get('id')}")
            return ig_account.get('id')
        else:
            print("\n❌ No Instagram Business Account connected to this page!")
            print("\n📌 Steps to fix:")
            print("   1. Go to your Facebook Page")
            print("   2. Click Settings → Instagram")
            print("   3. Connect your Instagram Business Account")
            return None
    else:
        print(f"\n❌ Error getting page info: {response.status_code}")
        print(response.json())
        return None

def verify_instagram_account(account_id):
    """Verify Instagram Business Account access"""
    print("\n\n🔍 Verifying Instagram Business Account...")
    print("=" * 60)
    
    url = f"https://graph.facebook.com/v21.0/{account_id}"
    params = {
        "fields": "id,username,name,profile_picture_url,followers_count",
        "access_token": FACEBOOK_ACCESS_TOKEN
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Instagram Account Verified!")
        print(f"   ID: {data.get('id')}")
        print(f"   Username: @{data.get('username')}")
        print(f"   Name: {data.get('name')}")
        print(f"   Followers: {data.get('followers_count', 'N/A')}")
        return True
    else:
        error = response.json()
        print(f"\n❌ Cannot access Instagram account: {response.status_code}")
        print(f"   Error: {error}")
        
        if response.status_code == 400:
            error_code = error.get('error', {}).get('code')
            if error_code == 100:
                print("\n📌 This means:")
                print("   • The account ID is wrong, OR")
                print("   • You don't have permission to access this account, OR")
                print("   • The Instagram account is not a Business Account")
        
        return False

def test_content_publishing(account_id):
    """Test if we can publish content to Instagram"""
    print("\n\n🔍 Testing Content Publishing Capability...")
    print("=" * 60)
    
    # Just check if we can access the account's media endpoint
    url = f"https://graph.facebook.com/v21.0/{account_id}/media"
    params = {
        "fields": "id",
        "limit": 1,
        "access_token": FACEBOOK_ACCESS_TOKEN
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        print("\n✅ Can access media endpoint - publishing should work!")
        return True
    else:
        print(f"\n❌ Cannot access media endpoint: {response.status_code}")
        print(response.json())
        return False

def main():
    print("\n" + "=" * 60)
    print("   INSTAGRAM PERMISSIONS & ACCOUNT VERIFICATION")
    print("=" * 60)
    
    if not FACEBOOK_ACCESS_TOKEN:
        print("\n❌ FACEBOOK_ACCESS_TOKEN not found in .env file!")
        return
    
    if not FACEBOOK_PAGE_ID:
        print("\n❌ FACEBOOK_PAGE_ID not found in .env file!")
        return
    
    print(f"\n📝 Current Configuration:")
    print(f"   Facebook Page ID: {FACEBOOK_PAGE_ID}")
    print(f"   Instagram Account ID (from .env): {INSTAGRAM_BUSINESS_ACCOUNT_ID}")
    
    # Step 1: Check token permissions
    permissions = check_token_permissions()
    
    if not permissions:
        print("\n❌ Cannot proceed - token validation failed")
        return
    
    # Step 2: Get correct Instagram Business Account ID from Facebook Page
    correct_ig_id = get_facebook_page_info()
    
    if not correct_ig_id:
        print("\n❌ Cannot proceed - no Instagram account connected")
        return
    
    # Step 3: Check if the ID in .env matches
    if correct_ig_id != INSTAGRAM_BUSINESS_ACCOUNT_ID:
        print(f"\n⚠️  WARNING: Instagram Account ID mismatch!")
        print(f"   .env file has: {INSTAGRAM_BUSINESS_ACCOUNT_ID}")
        print(f"   Correct ID is: {correct_ig_id}")
        print(f"\n📌 Update your .env file:")
        print(f"   INSTAGRAM_BUSINESS_ACCOUNT_ID={correct_ig_id}")
    
    # Step 4: Verify we can access the account
    if verify_instagram_account(correct_ig_id):
        # Step 5: Test content publishing capability
        test_content_publishing(correct_ig_id)
        
        print("\n\n" + "=" * 60)
        print("   ✅ VERIFICATION COMPLETE")
        print("=" * 60)
        
        if correct_ig_id != INSTAGRAM_BUSINESS_ACCOUNT_ID:
            print(f"\n🔧 ACTION REQUIRED:")
            print(f"   Update .env with: INSTAGRAM_BUSINESS_ACCOUNT_ID={correct_ig_id}")
    else:
        print("\n\n" + "=" * 60)
        print("   ❌ VERIFICATION FAILED")
        print("=" * 60)
        print("\n📌 Possible solutions:")
        print("   1. Make sure the Instagram account is a Business Account")
        print("   2. Ensure it's connected to your Facebook Page")
        print("   3. Regenerate your access token with all required permissions")
        print("   4. Use the Facebook Graph API Explorer to get a new token")

if __name__ == "__main__":
    main()
