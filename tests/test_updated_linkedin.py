#!/usr/bin/env python3
"""
Test script to verify the updated LinkedIn agent
"""
import os
from agents.linkedin_agent import LinkedInAgent

def test_linkedin_agent():
    """Test that the LinkedIn agent can be initialized with the new variables"""
    print("Testing updated LinkedIn agent...")
    
    try:
        # Initialize the agent
        agent = LinkedInAgent()
        print("LinkedIn agent initialized successfully with new configuration")
        print(f"   Person URN: {agent.person_urn}")
        
        # Check if environment variables are set
        if not os.getenv("LINKEDIN_ACCESS_TOKEN"):
            print("LINKEDIN_ACCESS_TOKEN not set in environment")
            return False
        
        if not os.getenv("LINKEDIN_PERSON_URN"):
            print("LINKEDIN_PERSON_URN not set in environment")
            return False
        
        print("All required environment variables are set")
        
        # Test that agent has correct attributes
        assert hasattr(agent, 'access_token')
        assert hasattr(agent, 'person_urn')
        print("Agent has correct attributes")
        
        # Check the headers
        expected_headers = {
            "Authorization": f"Bearer {agent.access_token}",
            "Content-Type": "application/json"
        }
        assert agent.headers == expected_headers
        print("Headers are correctly configured")
        
        return True
        
    except ValueError as e:
        print(f"Error initializing LinkedIn agent: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == \"__main__\":\n    print(\"Testing Updated LinkedIn Agent\")\n    print(\"=\" * 50)\n    \n    success = test_linkedin_agent()\n    \n    print(\"\\n\" + \"=\" * 50)\n    if success:\n        print(\"LinkedIn agent test passed!\")\n        print(\"The updated agent should work with your working test code approach.\")\n    else:\n        print(\"LinkedIn agent test failed.\")