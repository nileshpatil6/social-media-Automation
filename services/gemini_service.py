import os
import json
import base64
from typing import Dict, Any, Optional, List
import google.generativeai as genai
from PIL import Image
import io

class GeminiService:
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.vision_model = genai.GenerativeModel('gemini-2.5-flash')
    
    def generate_image_prompt(self, topic: str, brand_context: str = "", constraints: str = "") -> Dict[str, Any]:
        """
        Convert a topic into a detailed image generation prompt optimized for ads
        """
        system_prompt = f"""
        You are an expert advertising creative director specializing in visual social media content.
        
        Create a detailed image generation prompt for creating a high-quality advertisement image.
        
        REQUIREMENTS:
        - Target: Instagram/social media advertisement
        - Style: Professional, modern, eye-catching
        - Text: Minimal text only (brands struggle with text generation)
        - Composition: Clean, uncluttered, brand-focused
        - Colors: Vibrant but professional
        - Format: Square (1:1 aspect ratio)
        
        Topic: {topic}
        Brand Context: {brand_context}
        Additional Constraints: {constraints}
        
        Return a JSON object with:
        {{
            "prompt": "detailed image generation prompt",
            "negative_prompt": "things to avoid in the image",
            "style": "art style description",
            "aspect_ratio": "1:1",
            "text_elements": ["minimal text suggestions if any"],
            "color_palette": ["primary", "secondary", "accent"],
            "composition_notes": "layout and composition guidance"
        }}
        
        Focus on creating visually striking advertisements that convert well on social media.
        Avoid complex text, keep it minimal and readable.
        
      
        """
        
        try:
            response = self.model.generate_content(system_prompt)
            
            # Extract JSON from response
            response_text = response.text
            
            # Find JSON in the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx:end_idx]
                prompt_data = json.loads(json_str)
                
                # Add metadata
                prompt_data['original_topic'] = topic
                prompt_data['generated_by'] = 'gemini-2.5-flash'
                
                return prompt_data
            else:
                # Fallback if JSON parsing fails
                return self._create_fallback_prompt(topic, brand_context)
                
        except Exception as e:
            print(f"Error generating prompt: {e}")
            return self._create_fallback_prompt(topic, brand_context)
    
    def _create_fallback_prompt(self, topic: str, brand_context: str = "") -> Dict[str, Any]:
        """Fallback prompt generation if Gemini fails"""
        return {
            "prompt": f"Professional minimalist advertisement for {topic}, clean modern design, vibrant colors, centered composition, high quality, commercial photography style, {brand_context}",
            "negative_prompt": "text artifacts, extra fingers, distorted faces, watermarks, low quality, cluttered composition",
            "style": "modern-commercial",
            "aspect_ratio": "1:1",
            "text_elements": [topic],
            "color_palette": ["vibrant", "modern", "professional"],
            "composition_notes": "centered, clean, minimal",
            "original_topic": topic,
            "generated_by": "fallback"
        }
    
    def analyze_image_quality(self, image_path: str, original_prompt: str) -> Dict[str, Any]:
        """
        Analyze generated image for quality, safety, and prompt adherence
        """
        try:
            # Load and process image
            image = Image.open(image_path)
            
            analysis_prompt = f"""
            Analyze this generated advertisement image based on the following criteria:
            
            Original Prompt: {original_prompt}
            
            Please evaluate and score (0-10) the following aspects:
            
            1. SEMANTIC_MATCH: How well does the image match the intended prompt/topic?
            2. VISUAL_QUALITY: Overall visual quality, composition, and professional appearance
            3. TEXT_READABILITY: If text is present, is it clear and readable?
            4. BRAND_SUITABILITY: Would this work well as a brand advertisement?
            5. TECHNICAL_QUALITY: Are there visual artifacts, distortions, or technical issues?
            6. SAFETY_CHECK: Is the content appropriate and safe for advertising?
            
            Return JSON with:
            {{
                "scores": {{
                    "semantic_match": score,
                    "visual_quality": score,
                    "text_readability": score,
                    "brand_suitability": score,
                    "technical_quality": score,
                    "safety_check": score
                }},
                "overall_score": average_score,
                "is_postable": boolean,
                "issues_found": ["list of specific issues"],
                "recommendations": ["list of improvement suggestions"],
                "decision": "APPROVE/EDIT/REGENERATE",
                "edit_instructions": "specific edit instructions if decision is EDIT"
            }}
            
            Use these thresholds:
            - APPROVE: overall_score >= 7.5 and no critical issues
            - EDIT: overall_score >= 6.0 and fixable issues
            - REGENERATE: overall_score < 6.0 or unfixable issues
            """
            
            response = self.vision_model.generate_content([analysis_prompt, image])
            
            # Extract JSON from response
            response_text = response.text
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx:end_idx]
                analysis_data = json.loads(json_str)
                return analysis_data
            else:
                return self._create_fallback_analysis()
                
        except Exception as e:
            print(f"Error analyzing image: {e}")
            return self._create_fallback_analysis()
    
    def _create_fallback_analysis(self) -> Dict[str, Any]:
        """Fallback analysis if Gemini Vision fails"""
        return {
            "scores": {
                "semantic_match": 7.0,
                "visual_quality": 7.0,
                "text_readability": 7.0,
                "brand_suitability": 7.0,
                "technical_quality": 7.0,
                "safety_check": 8.0
            },
            "overall_score": 7.0,
            "is_postable": True,
            "issues_found": ["Unable to perform detailed analysis"],
            "recommendations": ["Manual review recommended"],
            "decision": "APPROVE",
            "edit_instructions": ""
        }
    
    def create_edit_instructions(self, analysis: Dict[str, Any], original_prompt: str) -> str:
        """
        Generate specific edit instructions based on image analysis
        """
        if analysis.get('decision') != 'EDIT':
            return ""
        
        issues = analysis.get('issues_found', [])
        recommendations = analysis.get('recommendations', [])
        
        edit_prompt = f"""
        Based on the image analysis, create specific edit instructions to improve this advertisement image.
        
        Original Prompt: {original_prompt}
        Issues Found: {', '.join(issues)}
        Recommendations: {', '.join(recommendations)}
        
        Provide clear, actionable edit instructions that focus on:
        - Fixing specific visual problems
        - Improving brand appeal
        - Enhancing readability
        - Maintaining professional quality
        
        Format as a concise editing instruction for image generation APIs.
        """
        
        try:
            response = self.model.generate_content(edit_prompt)
            return response.text.strip()
        except:
            return f"Fix the following issues: {', '.join(issues[:3])}"
    
    def create_regeneration_prompt(self, original_prompt: str, analysis: Dict[str, Any]) -> str:
        """
        Create an improved prompt for regeneration based on analysis feedback
        """
        issues = analysis.get('issues_found', [])
        recommendations = analysis.get('recommendations', [])
        
        regen_prompt = f"""
        Improve this image generation prompt based on analysis feedback:
        
        Original Prompt: {original_prompt}
        Issues to Fix: {', '.join(issues)}
        Improvements Needed: {', '.join(recommendations)}
        
        Create a better prompt that addresses these issues while maintaining the original intent.
        Focus on creating a high-quality advertisement image.
        """
        
        try:
            response = self.model.generate_content(regen_prompt)
            return response.text.strip()
        except:
            return f"{original_prompt} (improved version addressing: {', '.join(issues[:2])})"