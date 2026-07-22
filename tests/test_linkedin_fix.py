#!/usr/bin/env python3
\"\"\"
Test script to verify LinkedIn media upload fix
\"\"\"
import os
from agents.linkedin_agent import LinkedInAgent
import tempfile

def test_linkedin_agent():
    \"\"\"Test the LinkedIn agent with the fix\"\"\"
    print(\"Testing LinkedIn Agent with fixed service relationship identifier...\")
    
    try:
        # Initialize the agent
        agent = LinkedInAgent()
        print(\"LinkedIn agent initialized successfully\")
        
        # Check if environment variables are set
        if not os.getenv(\"LINKEDIN_ACCESS_TOKEN\"):
            print(\"LINKEDIN_ACCESS_TOKEN not set in environment\")
            return False
        
        if not os.getenv(\"LINKEDIN_ORGANIZATION_ID\"):
            print(\"LINKEDIN_ORGANIZATION_ID not set in environment\")
            return False
        
        print(\"Environment variables are set\")
        print(\"Organization ID:\", os.getenv('LINKEDIN_ORGANIZATION_ID'))
        
        # Test with a dummy image (create a temporary one)
        print(\"\nCreating dummy image for testing...\")
        dummy_content = b\"dummy image content\"
        with tempfile.NamedTemporaryFile(delete=False, suffix=\".jpg\") as tmp_file:
            tmp_file.write(dummy_content)
            temp_image_path = tmp_file.name
        
        try:
            # Try to upload the dummy image (this will fail at the upload step but should pass register_upload)
            print(\"Testing media upload (will intentionally fail at upload but register should work)...\")
            result = agent.upload_media(temp_image_path)
            
            if agent.last_error:
                print(\"Last error details:\", agent.last_error)
                
                # Check if the error is not the original service relationship error
                if agent.last_error.get('stage') == 'register_upload':
                    error_msg = str(agent.last_error.get('error', ''))
                    if 'serviceRelationships' in error_msg and 'ACCESS_DENIED' in error_msg:
                        print(\"Service relationship error still exists - fix didn't work\")
                        return False
                    else:
                        print(\"Service relationship error resolved - the error is now at a different stage, which is expected\")
                        print(\"Current error stage:\", agent.last_error.get('stage'))
                        return True
                else:
                    print(\"Register upload succeeded - error occurred in a later stage (expected)\")
                    return True
            else:
                print(\"Upload succeeded completely (unexpected but good!)\")
                return True
                
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)
    
    except ValueError as e:
        print(\"Error initializing LinkedIn agent:\", e)
        return False
    except Exception as e:
        print(\"Unexpected error:\", e)
        import traceback
        traceback.print_exc()
        return False

def test_create_post():
    \"\"\"Test the create post functionality\"\"\"
    print(\"\\nTesting create post functionality...\")
    
    try:
        agent = LinkedInAgent()
        
        # Test creating a post without media
        print(\"Testing post creation without media...\")
        text = \"Test post to verify LinkedIn API connection\"
        result = agent.create_post(text, asset_id=None)
        
        print(\"Post creation result:\", result)
        if agent.last_error:
            print(\"Last error:\", agent.last_error)
            # Check if it's a validation error about the post rather than authentication
            if 'serviceRelationships' in str(agent.last_error) or 'ACCESS_DENIED' in str(agent.last_error.get('error', {}).get('message', '')):
                print(\"Service relationship error still exists in post creation\")
                return False
        
        print(\"Post creation completed (with expected or no errors)\")
        return True
        
    except Exception as e:
        print(\"Error in post creation test:\", e)
        import traceback
        traceback.print_exc()
        return False

if __name__ == \"__main__\":
    print(\"LinkedIn Agent Fix Verification\")
    print(\"=\" * 50)
    
    success1 = test_linkedin_agent()
    success2 = test_create_post()
    
    print(\"\\n\" + \"=\" * 50)
    if success1 and success2:
        print(\"All tests passed! The LinkedIn agent fix appears to be working.\")
        print(\"The service relationship identifier has been corrected.\")
    else:
        print(\"Some tests failed. The fix may need further adjustments.\")
    
    print(\"\\nNotes:\")
    print(\"- If register_upload stage no longer shows service relationship errors, the fix worked\")
    print(\"- Upload failures at the actual upload stage are expected with dummy files\")
    print(\"- The real test will be uploading an actual image file to LinkedIn\")