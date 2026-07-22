#!/usr/bin/env bash
set -e

ACCESS_TOKEN="YOUR_ACCESS_TOKEN"
PERSON_URN="urn:li:person:JzD7IhuMn6"
IMAGE_FILE="photo.jpg"

echo ">>> Step 1: Register upload"
REG=$(curl -s -X POST "https://api.linkedin.com/v2/assets?action=registerUpload" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "registerUploadRequest": {
      "owner": "'"${PERSON_URN}"'",
      "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
      "serviceRelationships": [
        { "relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent" }
      ],
      "supportedUploadMechanism": ["SYNCHRONOUS_UPLOAD"]
    }
  }')

UPLOAD_URL=$(echo "$REG" | jq -r '.value.uploadMechanism."com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest".uploadUrl')
ASSET_URN=$(echo "$REG" | jq -r '.value.asset')
MEDIA_TYPE_FAMILY=$(echo "$REG" | jq -r '.value.uploadMechanism."com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest".headers["media-type-family"]')

echo "Upload URL: $UPLOAD_URL"
echo "Asset URN: $ASSET_URN"
echo "Media type family: $MEDIA_TYPE_FAMILY"

echo ">>> Step 2: Upload image"
curl -i -X PUT "$UPLOAD_URL" \
  -H "Content-Type: image/jpeg" \
  -H "media-type-family: ${MEDIA_TYPE_FAMILY}" \
  --data-binary @"$IMAGE_FILE"

echo ">>> Step 3: Create UGC post"
POST_RESP=$(curl -s -X POST "https://api.linkedin.com/v2/ugcPosts" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "X-Restli-Protocol-Version: 2.0.0" \
  -H "Content-Type: application/json" \
  -d '{
    "author": "'"${PERSON_URN}"'",
    "lifecycleState": "PUBLISHED",
    "specificContent": {
      "com.linkedin.ugc.ShareContent": {
        "shareCommentary": { "text": "Here is my uploaded image 🎉" },
        "shareMediaCategory": "IMAGE",
        "media": [
          {
            "status": "READY",
            "media": "'"${ASSET_URN}"'",
            "title": { "text": "Optional title" },
            "description": { "text": "Optional description" }
          }
        ]
      }
    },
    "visibility": { "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC" }
  }')

echo ">>> Post created:"
echo "$POST_RESP"
