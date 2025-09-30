#!/usr/bin/env python3
\"\"\"
Test script to verify the Facebook agent
\"\"\"
import os
from facebook_agent import FacebookAgent

def test_facebook_agent():
    \"\"\"Test that the Facebook agent can be initialized\"\"\"
    print(\"Testing Facebook agent...\")
    
    try:
        # Initialize the agent
        agent = FacebookAgent()
        print(\"Facebook agent initialized successfully\")
        print(f\"Page ID: {agent.page_id}\")
        
        # Check if environment variables are set
        if not os.getenv(\"FACEBOOK_ACCESS_TOKEN\"):
            print(\"FACEBOOK_ACCESS_TOKEN not set in environment\")
            return False
        
        if not os.getenv(\"FACEBOOK_PAGE_ID\"):
            print(\"FACEBOOK_PAGE_ID not set in environment\")
            return False
        
        print(\"All required environment variables are set\")
        print(f\"Base URL: {agent.base_url}\")
        print(f\"Headers: {agent.headers}\")
        
        return True
        
    except ValueError as e:
        print(f\"ValueError initializing Facebook agent: {e}\")
        return False
    except Exception as e:
        print(f\"Unexpected error: {e}\")
        import traceback
        traceback.print_exc()
        return False

if __name__ == \"__main__\":
    print(\"Testing Facebook Agent\")
    print(\"=\" * 50)
    
    success = test_facebook_agent()
    
    print(\"\\n\" + \"=\" * 50)
    if success:
        print(\"Facebook agent test passed!\")
    else:
        print(\"Facebook agent test failed.\")