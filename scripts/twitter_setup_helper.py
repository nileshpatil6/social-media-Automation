#!/usr/bin/env python3
\"\"\"
Twitter Configuration Helper
This script helps set up Twitter API credentials for the application
\"\"\"

import os
from pathlib import Path

def check_twitter_credentials():
    \"\"\"Check if Twitter credentials are properly set\"\"\"
    required_vars = [
        'TWITTER_API_KEY',
        'TWITTER_API_SECRET_KEY', 
        'TWITTER_ACCESS_TOKEN',
        'TWITTER_ACCESS_TOKEN_SECRET'
    ]
    
    print(\"🐦 Twitter API Credentials Check\")
    print(\"=\" * 40)
    
    all_set = True
    for var in required_vars:
        value = os.getenv(var, '')
        status = \"SET\" if value and not value.startswith('your-') else \"NOT SET/INVALID\"
        if status == \"NOT SET/INVALID\":
            all_set = False
        print(f\"  {var:30} : {status}\")
    
    print()
    if all_set:
        print(\"✅ All Twitter credentials are properly configured!\")
        print(\"You can now post to Twitter from the application.\")
    else:
        print(\"❌ Twitter credentials are missing or invalid.\")
        print(\"\\nTo configure Twitter posting:\")
        print(\"1. Go to https://developer.twitter.com/en/apps\")
        print(\"2. Create a new Twitter App or use an existing one\")
        print(\"3. Get the following credentials from your app settings:\")
        print(\"   - API Key\")
        print(\"   - API Secret Key\") 
        print(\"   - Access Token\")
        print(\"   - Access Token Secret\")
        print(\"4. Update your .env file with the actual values\")
        print(\"5. Restart the application\")
    
    return all_set

def update_env_file():
    \"\"\"Helper to update .env file with Twitter credentials\"\"\"
    print(\"\\n🔧 Twitter Credentials Setup Assistant\")
    print(\"=\" * 45)
    
    # Check if .env file exists
    env_file = Path(\".env\")
    if not env_file.exists():
        print(\"❌ .env file not found!\")
        print(\"Please create one by copying .env.example\")
        return False
    
    print(\"Current Twitter credentials in .env:\")
    
    # Read current .env file
    with open(env_file, 'r') as f:
        content = f.read()
    
    # Check for current values
    import re
    twitter_vars = {
        'TWITTER_API_KEY': re.search(r'TWITTER_API_KEY=(.*)', content),
        'TWITTER_API_SECRET_KEY': re.search(r'TWITTER_API_SECRET_KEY=(.*)', content), 
        'TWITTER_ACCESS_TOKEN': re.search(r'TWITTER_ACCESS_TOKEN=(.*)', content),
        'TWITTER_ACCESS_TOKEN_SECRET': re.search(r'TWITTER_ACCESS_TOKEN_SECRET=(.*)', content)
    }
    
    for var, match in twitter_vars.items():
        value = match.group(1) if match else \"NOT FOUND\"
        status = \"SET ✓\" if value and not value.startswith('your-') else \"NEEDS UPDATE ✗\"
        print(f\"  {var}: {status}\")
    
    print(\"\\n💡 To set your Twitter credentials:\")
    print(\"  Edit the .env file and replace placeholder values with your actual credentials\")
    print(\"  Then restart your application server\")
    
    return True

def main():
    print(\"🐦 Twitter Configuration Helper\")
    print(\"Check and setup Twitter API credentials for your application\\n\")
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    check_twitter_credentials()
    update_env_file()
    
    print(\"\\n📋 Steps to get Twitter API credentials:\")
    print(\"1. Visit https://developer.twitter.com/en/apps\")
    print(\"2. Apply for a developer account if you don't have one\")
    print(\"3. Create a new app\")
    print(\"4. Go to your app's Keys and Tokens section\")
    print(\"5. Copy the credentials to your .env file\")
    print(\"6. Restart the application server\")

if __name__ == \"__main__\":
    main()