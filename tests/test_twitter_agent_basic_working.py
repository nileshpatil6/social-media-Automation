#!/usr/bin/env python3
\"\"\"
Simple test to verify TwitterAgent import and basic functionality
\"\"\"

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_import():
    \"\"\"Test that TwitterAgent can be imported\"\"\"
    try:
        from agents.twitter_agent import TwitterAgent
        print(\"[PASS] TwitterAgent imported successfully\")
        return True
    except ImportError as e:
        print(f\"[FAIL] Failed to import TwitterAgent: {e}\")
        return False
    except Exception as e:
        print(f\"[FAIL] Error importing TwitterAgent: {e}\")
        return False

def test_basic_functionality():
    \"\"\"Test basic TwitterAgent functionality\"\"\"
    try:
        from agents.twitter_agent import TwitterAgent
        
        # Test character limit constant
        if hasattr(TwitterAgent, 'TWEET_CHARACTER_LIMIT'):
            print(f\"[PASS] TWEET_CHARACTER_LIMIT is {TwitterAgent.TWEET_CHARACTER_LIMIT}\")
        else:
            print(\"[FAIL] TWEET_CHARACTER_LIMIT not found\")
            return False
        
        # Test prepare_caption method exists
        if hasattr(TwitterAgent, '_prepare_caption'):
            print(\"[PASS] _prepare_caption method exists\")
        else:
            print(\"[FAIL] _prepare_caption method not found\")
            return False
            
        return True
    except Exception as e:
        print(f\"[FAIL] Error testing basic functionality: {e}\")
        return False

def check_env_vars():
    \"\"\"Check if required environment variables are set\"\"\"
    required_vars = [
        'TWITTER_API_KEY',
        'TWITTER_API_SECRET_KEY', 
        'TWITTER_ACCESS_TOKEN',
        'TWITTER_ACCESS_TOKEN_SECRET'
    ]
    
    print(\"\\n[INFO] Checking environment variables:\")
    all_set = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f\"  [SET] {var}: Set\")
        else:
            print(f\"  [MISSING] {var}: Not set\")
            all_set = False
    
    return all_set

def main():
    print(\"[TWITTER] Testing TwitterAgent Import and Setup\\n\")
    
    import_success = test_import()
    if not import_success:
        return False
    
    functionality_success = test_basic_functionality()
    env_vars_set = check_env_vars()
    
    print(f\"\\n[RESULTS] Results:\")
    print(f\"  Import: {'PASS' if import_success else 'FAIL'}\")
    print(f\"  Functionality: {'PASS' if functionality_success else 'FAIL'}\")
    print(f\"  Environment variables: {'ALL SET' if env_vars_set else 'SOME MISSING'}\")
    
    if import_success and functionality_success:
        print(\"\\n[TWITTER] TwitterAgent is ready to use!\")
        if not env_vars_set:
            print(\"[WARNING] Remember to set your Twitter API credentials to post to Twitter\")
        return True
    else:
        print(\"\\n[TWITTER] TwitterAgent setup failed\")
        return False

if __name__ == \"__main__\":
    success = main()
    sys.exit(0 if success else 1)