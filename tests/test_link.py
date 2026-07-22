import requests
import json

# Replace these with your details
ACCESS_TOKEN = "AQXO7JNqaZlhmaO_CvVy9Lr7i0gWEFLQD6yWgcNwgpUKEw_XoGcVJz65RZqF8Ur7gM6BzmJZs-LLxV05mQozciuw5yechfrmu1YcDW5W1GqA1frQHou3muvcpB6RUYbIGw-cS_lqpes8vGE6nBHB9ZbwIV1BrMV_2esf3O5zxqlsKH1kaKnDA6lyicAeh4JOualTnUQARK517uYSdg35WzROvUNh7wKUFvBadrLhdyFxoxELVcI1TNUcH84apAqlZJ1wqYNEhGtc7OrM8MGiiaDhhdXDhXnINfNGdHHurgSHgWRz3UTSU3gGxdH-igmB9QJ1EAM-keemgU6xYlQB5R495u70Pw"
PERSON_URN = "urn:li:person:JzD7IhuMn6"
IMAGE_PATH = "photo.jpg"
CAPTION = "Here is my uploaded image 🎉"

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

# Step 1: Register the upload
register_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
register_body = {
    "registerUploadRequest": {
        "owner": PERSON_URN,
        "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
        "serviceRelationships": [
            {"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}
        ],
        "supportedUploadMechanism": ["SYNCHRONOUS_UPLOAD"]
    }
}

print(">>> Registering upload")
r = requests.post(register_url, headers=headers, json=register_body)
r.raise_for_status()
upload_info = r.json()
upload_url = upload_info["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
asset = upload_info["value"]["asset"]

print("Upload URL:", upload_url)
print("Asset:", asset)

# Step 2: Upload the image binary
print(">>> Uploading image")
with open(IMAGE_PATH, "rb") as f:
    upload_headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "image/jpeg",
        "media-type-family": "STILLIMAGE"
    }
    r = requests.put(upload_url, headers=upload_headers, data=f)
    r.raise_for_status()

print("Image uploaded successfully")

# Step 3: Create the post
print(">>> Creating post")
post_url = "https://api.linkedin.com/v2/ugcPosts"
post_body = {
    "author": PERSON_URN,
    "lifecycleState": "PUBLISHED",
    "specificContent": {
        "com.linkedin.ugc.ShareContent": {
            "shareCommentary": {"text": CAPTION},
            "shareMediaCategory": "IMAGE",
            "media": [
                {
                    "status": "READY",
                    "media": asset,
                    "title": {"text": "Optional title"},
                    "description": {"text": "Optional description"}
                }
            ]
        }
    },
    "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
}

r = requests.post(post_url, headers=headers, json=post_body)
r.raise_for_status()

print("Post created:", r.json())
