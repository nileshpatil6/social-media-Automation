#!/usr/bin/env python3
"""
Simple test for URL logging functionality without API dependencies
"""
import os
import json
import uuid
from datetime import datetime

def test_simple_logging():
    """Test URL logging without dependencies"""
    print("🧪 Testing simple URL logging...")
    
    # Create the storage directory if it doesn't exist
    storage_path = './generated_images'
    os.makedirs(storage_path, exist_ok=True)
    
    # Define log file path
    url_log_file = os.path.join(storage_path, 'ideogram_urls.log')
    
    # Test logging function
    def log_ideogram_url(image_url: str, workflow_id: str, topic: str, attempt: int, prompt: str = ""):
        try:
            timestamp = datetime.now().isoformat()
            log_entry = {
                "timestamp": timestamp,
                "workflow_id": workflow_id,
                "topic": topic,
                "attempt": attempt,
                "image_url": image_url,
                "prompt": prompt[:200] + "..." if len(prompt) > 200 else prompt
            }
            
            # Append to log file
            with open(url_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
            
            print(f"📝 Logged Ideogram URL for workflow {workflow_id}: {image_url}")
            return True
            
        except Exception as e:
            print(f"⚠️ Failed to log Ideogram URL: {e}")
            return False
    
    # Test reading function
    def get_logged_urls(limit: int = 50):
        try:
            if not os.path.exists(url_log_file):
                return []
            
            urls = []
            with open(url_log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    try:
                        url_data = json.loads(line.strip())
                        urls.append(url_data)
                    except json.JSONDecodeError:
                        continue
            
            return list(reversed(urls))
            
        except Exception as e:
            print(f"⚠️ Failed to read URL log: {e}")
            return []
    
    # Test logging some URLs
    test_data = [
        {
            "url": "https://ideogram.ai/api/images/direct/test123.jpg",
            "workflow_id": str(uuid.uuid4()),
            "topic": "Test Advertisement 1",
            "prompt": "Create a beautiful test advertisement with modern design"
        },
        {
            "url": "https://ideogram.ai/api/images/direct/test456.jpg", 
            "workflow_id": str(uuid.uuid4()),
            "topic": "Test Advertisement 2",
            "prompt": "Design a colorful promotional banner for social media marketing"
        },
        {
            "url": "https://ideogram.ai/api/images/direct/edited789.jpg",
            "workflow_id": str(uuid.uuid4()),
            "topic": "Edited Test Ad",
            "prompt": "EDITED: Make the text more prominent and add a call-to-action"
        }
    ]
    
    print("\n1. Testing URL logging:")
    success_count = 0
    for i, data in enumerate(test_data):
        result = log_ideogram_url(
            image_url=data["url"],
            workflow_id=data["workflow_id"],
            topic=data["topic"],
            attempt=i + 1,
            prompt=data["prompt"]
        )
        if result:
            success_count += 1
    
    print(f"✅ Successfully logged {success_count}/{len(test_data)} URLs")
    
    print("\n2. Testing URL retrieval:")
    logged_urls = get_logged_urls(limit=10)
    print(f"Found {len(logged_urls)} logged URLs:")
    
    for i, url_data in enumerate(logged_urls[-3:]):  # Show last 3
        print(f"  {i+1}. {url_data['timestamp'][:19]} - {url_data['topic']}")
        print(f"      URL: {url_data['image_url']}")
        print(f"      Workflow: {url_data['workflow_id'][:8]}...")
        print(f"      Attempt: {url_data['attempt']}")
        print()
    
    print(f"\n3. Log file info:")
    print(f"   Location: {url_log_file}")
    if os.path.exists(url_log_file):
        file_size = os.path.getsize(url_log_file)
        with open(url_log_file, 'r') as f:
            line_count = len(f.readlines())
        print(f"   File size: {file_size} bytes")
        print(f"   Total entries: {line_count}")
        print("   ✅ Log file exists and contains data")
    else:
        print("   ❌ Log file does not exist")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Starting Simple URL Logging Test")
    print("=" * 50)
    
    success = test_simple_logging()
    
    print("\n" + "=" * 50)
    if success:
        print("🏁 URL logging functionality is working!")
    else:
        print("❌ URL logging test failed!")