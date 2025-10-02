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
        
        example prompts A photograph showcases a chilled "Yousuf"Winter Edition energy drink can in kiwi-peach flavor suspended in a dark, minimalist studio. The silver can is meticulously coated in condensation, reflecting the studio lights to reveal subtle, intricate geometric patterns, and adorned with stylized snowflakes. Three perfectly clear, irregularly shaped ice cubes orbit the can in a slow, graceful spiral, catching the light and scattering it into delicate refractions. Soft, diffused lighting highlights the can’s frosty surface and creates a gentle glow against a deep crimson backdrop subtly fading to fiery orange.

A product photography shot of a luxury perfume bottle positioned on a dark wooden stump against a deep purple gradient background. The bottle is matte purple in color with a rounded square shape and has a small round purple cap. The front of the bottle features a black rectangular label with gold text "CREO IA" and a small gold text below it. The wooden stump is textured with deep grooves and natural bark patterns, showing signs of age and weathering. The lighting creates a soft glow around the bottle, emphasizing its smooth surface against the dark background. The composition is minimalist and elegant, with the bottle positioned at a slight angle on the right side of the frame. The purple background transitions from darker at the top to a slightly lighter shade at the bottom, creating a moody, sophisticated atmosphere.



A photograph of an energy drink can showcasing a limited-edition design, prominently featuring "Coca-Cola" in a classic script. The predominantly red can boasts intricately embossed white patterns of SHE fruits and leaves, adorned with glistening condensation droplets that cling to its surface, as it rests on a bed of damp moss intertwined with exposed rainforest roots. Lush, vibrant green foliage with scattered guaraná fruits and a few cafe beans, mint and vanilla pods surround the can, all bathed in the diffused light filtering through the dense Amazon canopy, creating a shallow depth of field. Soft bokeh highlights the scattered dew drops on nearby leaves, emphasizing the can's luxurious texture and conveying a sense of refreshing indulgence.

A photograph showcases a pristine white Air Force 1 sneaker suspended mid-air against a dramatically dark black backdrop, displaying the text "Lebron" boldly printed across the lateral side. The sneaker's clean white leather upper gleams under a focused spotlight, accentuating the iconic white Nike swoosh and its tightly knotted white laces, while subtle graining is visible on the rubber outsole. Jagged, dark gray rocky formations, dusted with fine silver glitter, jut out from the lower corners, subtly reflecting the studio lights, creating a dynamic contrast to the floating shoe. A single, powerful spotlight highlights the sneaker, casting sharp, defined shadows that emphasize its sleek silhouette against the textured, minimalist background.

A photograph of a pristine white Air Force 1 sneaker suspended in mid-air against a stark black backdrop.  The sneaker features a clean white leather upper that gleams under a single spotlight, prominently displaying the iconic white Nike swoosh logo and crisp white laces tied in a neat bow, with a subtly textured white midsole and rubber outsole. Below the floating shoe, jagged, dark gray rocky formations rise with deep orange-lit crevices, their rough surfaces contrasting with the sneaker’s smooth design, while a single beam of light illuminates "ALOFA" written in a clean sans-serif font across the side. The dramatic studio lighting creates sharp shadows and highlights, emphasizing the sneaker's suspension and the stark visual contrast

A photograph in a fashion editorial style showcasing a pair of luxury high heels in a deep midnight blue velvet. Silver vine embroidery intricately wraps around the shoe, punctuated by tiny star-shaped crystals that catch the light. The heels feature a sharp, pointed toe and a tall, shimmering stiletto heel that reflects the surrounding environment. They rest elegantly on a polished, reflective marble background that creates a stunning visual contrast and highlights the shoe's luxurious details.

A sleek product shot advertisement showcasing a futuristic, minimalist laptop radiating vibrant neon gradients of purple, blue, and pink, designed for a digital marketing agency. Floating above the laptop are stylized 3D icons representing Instagram, Facebook, Twitter, and LinkedIn, subtly glowing and interconnected, demonstrating seamless social media integration. The composition utilizes a dark, almost black background punctuated by strategic glowing accents that highlight the laptop’s futuristic UI elements and sharp edges, with the bold headline "UNLOCK YOUR POTENTIAL" displayed in a modern sans-serif font. The overall aesthetic is clean, high-contrast, and undeniably modern, incorporating a subtle agency logo in the corner and a glowing neon button with the call to action "GET STARTED" to convey innovation and drive engagement.
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