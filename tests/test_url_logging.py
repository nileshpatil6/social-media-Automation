#!/usr/bin/env python3
"""
Test script for URL logging functionality
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.ad_generation_service import AdGenerationService
import json

def test_url_logging():
    """Test the URL logging functionality"""
    print("🧪 Testing URL logging functionality...")
    
    try:
        # Create an instance of AdGenerationService
        ad_service = AdGenerationService()
        
        # Test logging a sample URL
        print("\n1. Testing URL logging:")
        ad_service.log_ideogram_url(
            image_url="https://ideogram.ai/api/images/direct/test123.jpg",
            workflow_id="test-workflow-123",
            topic="Test Advertisement",
            attempt=1,
            prompt="Create a beautiful test advertisement with modern design"
        )
        
        # Test logging another URL
        ad_service.log_ideogram_url(
            image_url="https://ideogram.ai/api/images/direct/test456.jpg",
            workflow_id="test-workflow-456",
            topic="Another Test Ad",
            attempt=2,
            prompt="Design a colorful promotional banner for social media marketing"
        )
        
        print("✅ URL logging test completed!")
        
        # Test reading logged URLs
        print("\n2. Testing URL retrieval:")
        logged_urls = ad_service.get_logged_urls(limit=10)
        
        print(f"Found {len(logged_urls)} logged URLs:")
        for i, url_data in enumerate(logged_urls):
            print(f"  {i+1}. {url_data['timestamp'][:19]} - {url_data['topic']}")
            print(f"      URL: {url_data['image_url']}")
            print(f"      Workflow: {url_data['workflow_id']}")
            print(f"      Attempt: {url_data['attempt']}")
            print()
        
        print("✅ URL retrieval test completed!")
        
        # Check if log file exists
        print(f"\n3. Log file location: {ad_service.url_log_file}")
        if os.path.exists(ad_service.url_log_file):
            file_size = os.path.getsize(ad_service.url_log_file)
            print(f"   Log file exists and is {file_size} bytes")
            
            # Show raw content
            print("\n4. Raw log file content (last 5 lines):")
            with open(ad_service.url_log_file, 'r') as f:
                lines = f.readlines()
                for line in lines[-5:]:
                    try:
                        data = json.loads(line.strip())
                        print(f"   {data['timestamp'][:19]} | {data['topic'][:30]}")
                    except:
                        print(f"   {line.strip()[:50]}...")
        else:
            print("   ❌ Log file does not exist")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting URL Logging Tests")
    print("=" * 50)
    
    success = test_url_logging()
    
    print("\n" + "=" * 50)
    if success:
        print("🏁 All tests passed!")
    else:
        print("❌ Some tests failed!")