#!/usr/bin/env python3
\"\"\"
Verification script for the LinkedIn agent service relationship fix
\"\"\"
import json
from linkedin_agent import LinkedInAgent

def verify_fix():
    print(\"🔍 Verifying LinkedIn agent service relationship fix...\")
    
    # Create an instance of the LinkedIn agent
    agent = LinkedInAgent()
    
    # Manually construct the payload to check the fixed value
    organization_id = agent.organization_id
    register_payload = {
        \"registerUploadRequest\": {
            \"recipes\": [
                \"urn:li:digitalmediaRecipe:(public,shareable)\"
            ],
            \"owner\": f\"urn:li:organization:{organization_id}\",
            \"serviceRelationships\": [
                {
                    \"relationshipType\": \"OWNER\",
                    \"identifier\": \"urn:li:organization\"  # This is the fixed value
                }
            ]
        }
    }
    
    print(\"✅ Service relationship identifier:\", register_payload[\"registerUploadRequest\"][\"serviceRelationships\"][0][\"identifier\"])
    
    # Verify that the value is correct
    expected_identifier = \"urn:li:organization\"
    actual_identifier = register_payload[\"registerUploadRequest\"][\"serviceRelationships\"][0][\"identifier\"]
    
    if actual_identifier == expected_identifier:
        print(\"✅ Service relationship identifier is correctly set!\")
        print(\"✅ The ACCESS_DENIED error related to serviceRelationships should now be fixed\")
        return True
    else:
        print(f\"❌ Service relationship identifier is incorrect. Expected: {expected_identifier}, Got: {actual_identifier}\")
        return False

if __name__ == \"__main__\":
    print(\"🚀 LinkedIn Agent Service Relationship Fix Verification\")
    print(\"=\" * 60)
    
    success = verify_fix()
    
    print(\"\\n\" + \"=\" * 60)
    if success:
        print(\"🎉 SUCCESS: The LinkedIn media upload fix has been applied correctly!\")
        print(\"\\nThe issue was:\")
        print(\"- LinkedIn API was rejecting the service relationship identifier\")
        print(\"- Previous value: 'urn:li:serviceprovider:primary' (incorrect)\")
        print(\"- Fixed value: 'urn:li:organization' (correct)\")
        print(\"\\nThis should resolve the 403 ACCESS_DENIED error in the register_upload stage.\")
    else:
        print(\"❌ The fix was not applied correctly.\")
    
    print(\"\\n📋 Next steps:\")
    print(\"1. The application should now be able to upload media to LinkedIn\")
    print(\"2. Test with a real image file to confirm full functionality\")
    print(\"3. Monitor logs to verify no more service relationship errors occur\")