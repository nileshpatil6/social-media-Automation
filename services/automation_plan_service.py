import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import google.generativeai as genai

class AutomationPlanService:
    def __init__(self):
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    def generate_content_plan(
        self,
        brand_name: str,
        brand_description: str,
        target_audience: str,
        color_palette: str,
        brand_style: str,
        content_type: str,
        content_description: str,
        start_date: datetime,
        end_date: datetime,
        posts_per_day: int,
        posting_times: List[str],
        timezone: str,
        platforms: List[str]
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive content plan using AI based on brand information and scheduling preferences.
        Returns short, concise image descriptions as requested.
        """

        # Calculate total number of posts needed
        total_days = (end_date - start_date).days + 1
        total_posts = total_days * posts_per_day

        # Prepare the prompt for Gemini
        prompt = f"""You are an expert social media content strategist. Generate a comprehensive content plan for a brand with the following details:

BRAND INFORMATION:
- Brand Name: {brand_name}
- Description: {brand_description}
- Target Audience: {target_audience}
- Color Palette: {color_palette}
- Brand Style: {brand_style}

CONTENT STRATEGY:
- Content Type: {content_type}
- Content Description: {content_description}

SCHEDULING:
- Start Date: {start_date.strftime('%Y-%m-%d')}
- End Date: {end_date.strftime('%Y-%m-%d')}
- Posts per Day: {posts_per_day}
- Posting Times: {', '.join(posting_times)} ({timezone})
- Total Posts to Generate: {total_posts}
- Platforms: {', '.join(platforms)}

IMPORTANT INSTRUCTIONS:
1. Generate exactly {total_posts} unique posts distributed evenly across the date range
2. For each post, provide:
   - A short, concise image description (KEEP IT MINIMAL - just essential elements like "water bottle, silver color, {brand_name} branding")
   - An engaging caption suitable for social media (include relevant hashtags)
3. Ensure variety in content while maintaining brand consistency
4. Image descriptions should be SHORT - only 5-10 words maximum
5. Distribute content themes evenly across the schedule

Return your response in this EXACT JSON format:
{{
    "plan_summary": "Brief overview of the content strategy",
    "posts": [
        {{
            "day": 1,
            "time": "09:00",
            "image_description": "water bottle, silver, {brand_name} logo",
            "caption": "Engaging caption with hashtags"
        }}
    ]
}}

Ensure the JSON is valid and parseable."""

        try:
            # Generate the plan using Gemini
            response = self.model.generate_content(prompt)
            response_text = response.text

            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            # Parse the JSON response
            plan_data = json.loads(response_text)

            # Create scheduled items with actual datetimes
            from dateutil import tz
            from datetime import timezone as dt_timezone

            scheduled_items = []

            # Convert start_date to user's timezone
            user_tz = tz.gettz(timezone)
            if start_date.tzinfo is None:
                # If naive, assume UTC
                start_date = start_date.replace(tzinfo=dt_timezone.utc)

            # Convert to user timezone
            start_date_local = start_date.astimezone(user_tz)
            current_date = start_date_local.replace(hour=0, minute=0, second=0, microsecond=0)

            post_index = 0

            for day in range(total_days):
                for time_slot in posting_times[:posts_per_day]:
                    if post_index >= len(plan_data.get('posts', [])):
                        break

                    post_data = plan_data['posts'][post_index]

                    # Parse time
                    hour, minute = map(int, time_slot.split(':'))
                    scheduled_datetime = current_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

                    scheduled_items.append({
                        'scheduled_datetime': scheduled_datetime.isoformat(),
                        'image_description': post_data['image_description'],
                        'caption': post_data['caption'],
                        'platforms': platforms
                    })

                    post_index += 1

                current_date += timedelta(days=1)

            return {
                'success': True,
                'plan_summary': plan_data.get('plan_summary', 'Content plan generated successfully'),
                'total_posts': len(scheduled_items),
                'items': scheduled_items
            }

        except json.JSONDecodeError as e:
            return {
                'success': False,
                'error': f"Failed to parse AI response: {str(e)}",
                'raw_response': response_text if 'response_text' in locals() else None
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to generate content plan: {str(e)}"
            }

    def validate_plan_data(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that the plan data contains all required fields
        """
        required_fields = [
            'brand_name', 'start_date', 'end_date',
            'posts_per_day', 'posting_times', 'platforms'
        ]

        missing_fields = [field for field in required_fields if field not in plan_data or not plan_data[field]]

        if missing_fields:
            return {
                'valid': False,
                'error': f"Missing required fields: {', '.join(missing_fields)}"
            }

        # Validate date range
        try:
            from dateutil import tz
            from datetime import timezone as dt_timezone

            # Parse dates (they come as ISO strings, possibly with 'Z' for UTC)
            start_str = plan_data['start_date'].replace('Z', '+00:00')
            end_str = plan_data['end_date'].replace('Z', '+00:00')

            start = datetime.fromisoformat(start_str)
            end = datetime.fromisoformat(end_str)

            # Make sure both have timezone info
            if start.tzinfo is None:
                start = start.replace(tzinfo=dt_timezone.utc)
            if end.tzinfo is None:
                end = end.replace(tzinfo=dt_timezone.utc)

            if end < start:
                return {
                    'valid': False,
                    'error': "End date must be after start date"
                }

            # Get current time in UTC for comparison
            now_utc = datetime.now(dt_timezone.utc)

            # Compare with current time (allow scheduling for today or future)
            if start < now_utc - timedelta(hours=24):
                return {
                    'valid': False,
                    'error': "Start date cannot be more than 1 day in the past"
                }
        except (ValueError, AttributeError) as e:
            return {
                'valid': False,
                'error': f"Invalid date format: {str(e)}"
            }

        # Validate platforms
        valid_platforms = {'instagram', 'twitter', 'facebook', 'linkedin', 'youtube'}
        invalid_platforms = [p for p in plan_data['platforms'] if p not in valid_platforms]

        if invalid_platforms:
            return {
                'valid': False,
                'error': f"Invalid platforms: {', '.join(invalid_platforms)}"
            }

        return {'valid': True}
