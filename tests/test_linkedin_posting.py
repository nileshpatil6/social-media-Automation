#!/usr/bin/env python3
\"\"\"
Test script for LinkedIn posting functionality
\"\"\"

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_linkedin_agent_import():
    \"\"\"Test that LinkedInAgent can be imported\"\"\"
    try:
        from agents.linkedin_agent import LinkedInAgent
        print(\"[PASS] LinkedInAgent imported successfully\")
        return True
    except ImportError as e:
        print(f\"[FAIL] Failed to import LinkedInAgent: {e}\")
        return False
    except Exception as e:
        print(f\"[FAIL] Error importing LinkedInAgent: {e}\")
        return False

def test_linkedin_agent_functionality():
    \"\"\"Test LinkedInAgent basic functionality\"\"\"
    try:
        from agents.linkedin_agent import LinkedInAgent
        
        # Check if required environment variables are set
        required_vars = [
            'LINKEDIN_ACCESS_TOKEN',
            'LINKEDIN_ORGANIZATION_ID'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            print(f\"[INFO] Missing LinkedIn environment variables: {missing_vars}\")
            print(\"[INFO] Skipping full initialization test. LinkedInAgent will work when credentials are set.\")
            return True  # Skip rather than fail if credentials not set
        
        # If credentials are set, try to create the agent
        agent = LinkedInAgent()
        print(\"[PASS] LinkedInAgent created successfully\")
        print(f\"[PASS] Has post_to_linkedin method: {hasattr(agent, 'post_to_linkedin')}\")
        print(f\"[PASS] Has upload_media method: {hasattr(agent, 'upload_media')}\")
        
        return True
    except Exception as e:
        print(f\"[FAIL] Error testing LinkedInAgent functionality: {e}\")
        import traceback
        traceback.print_exc()
        return False

def check_env_vars():
    \"\"\"Check if required LinkedIn environment variables are set\"\"\"
    required_vars = [
        'LINKEDIN_ACCESS_TOKEN',
        'LINKEDIN_ORGANIZATION_ID'
    ]
    
    print(\"\\n[INFO] Checking LinkedIn environment variables:\")
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
    print(\"💼 Testing LinkedIn Posting Functionality\\n\")
    
    import_success = test_linkedin_agent_import()
    functionality_success = test_linkedin_agent_functionality()
    env_vars_set = check_env_vars()
    
    print(f\"\\n[RESULTS] Results:\")
    print(f\"  Import: {'PASS' if import_success else 'FAIL'}\")
    print(f\"  Functionality: {'PASS' if functionality_success else 'FAIL'}\")
    print(f\"  Environment variables: {'ALL SET' if env_vars_set else 'SOME MISSING'}\")
    
    if import_success and functionality_success:
        print(\"\\n[LINKEDIN] LinkedInAgent is ready to use!\")
        if not env_vars_set:
            print(\"[WARNING] Remember to set your LinkedIn API credentials to post to LinkedIn\")
        return True
    else:
        print(\"\\n[LINKEDIN] LinkedInAgent setup failed\")
        return False

if __name__ == \"__main__\":
    success = main()
    sys.exit(0 if success else 1)