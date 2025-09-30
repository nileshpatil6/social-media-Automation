# Facebook API Permissions Fix Guide

## Issue
Error: `(#200) This app is not allowed to publish to other users' timelines.`

## Root Cause
Your Facebook app is not properly configured to post to Facebook Pages. This error occurs when:
1. The access token doesn't have the required permissions
2. The app is not configured for Facebook Page posting
3. The access token is a user token instead of a page token
4. Your app hasn't been approved by Facebook for the required permissions

## Solution Steps

### 1. Get Proper Page Access Token
1. Go to [Facebook Developers - Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Select your app from the dropdown
3. In "Get Token" dropdown, select "Get User Access Token"
4. Select the following permissions:
   - `pages_manage_posts`
   - `pages_read_engagement`
   - `pages_manage_engagement` (optional)
5. Then select "Get Page Access Token" 
6. Select your Facebook Page from the list
7. This will give you a Page Access Token with all necessary permissions

### 2. Verify Permissions in Access Token
Use Facebook's Access Token Debugger to verify your token has the right permissions:
- Go to [Access Token Debugger](https://developers.facebook.com/tools/debug/accesstoken/)
- Paste your access token
- Check that it includes `pages_manage_posts`

### 3. Update Environment Variables
Make sure your `.env` file contains:
```
FACEBOOK_ACCESS_TOKEN=your_new_page_access_token
FACEBOOK_PAGE_ID=your_facebook_page_id
```

### 4. App Review Requirements
If your app is still in development mode, you need to submit it for review to access these permissions:
1. Go to your Facebook App Dashboard
2. Navigate to "App Review" section
3. Submit for review with the `pages_manage_posts` permission
4. Explain that your app needs to post to Facebook Pages

### 5. Alternative Method: Long-lived Token
If the above doesn't work, you may need to create a long-lived token:

1. First get a short-lived user access token
2. Exchange it for a long-lived token:
   ```
   GET https://graph.facebook.com/oauth/access_token?  
     grant_type=fb_exchange_token&           
     client_id={app-id}&
     client_secret={app-secret}&
     fb_exchange_token={short-lived-token}
   ```
3. Then get a page access token using:
   ```
   GET https://graph.facebook.com/{user-id}/accounts?access_token={long-lived-token}
   ```

### 6. Testing Your Setup
After updating your access token, test by making a simple API call:
```
GET https://graph.facebook.com/v22.0/me?access_token=YOUR_TOKEN
```

For page info:
```
GET https://graph.facebook.com/v22.0/YOUR_PAGE_ID?access_token=YOUR_TOKEN
```

### 7. Common Troubleshooting Points
- Make sure your Facebook Page is not in "unpublished" state
- Ensure your app is not in development mode if other users need to use it
- Check that your Facebook Page ID is numeric, not a name
- Verify that your access token has not expired

### 8. App Configuration
Your Facebook App needs to be configured properly:
- Go to [Facebook Developers](https://developers.facebook.com/)
- Select your app
- In Settings → Basic, ensure "App mode" is "Live" (if needed)
- In Products, ensure "Facebook Login" is added and configured
- Under Facebook Login → Settings, ensure your domain is added if required

### 9. Using Graph API Explorer for Testing
The Graph API Explorer is helpful for testing:
- Use it to test your API calls before implementing in code
- It can help you get the right permissions for your token
- It shows the exact error messages which can be more detailed

### 10. Verify Page ID
Ensure your `FACEBOOK_PAGE_ID` is correct by calling:
```
GET https://graph.facebook.com/search?q=PAGE_NAME&type=page&access_token=YOUR_TOKEN
```
