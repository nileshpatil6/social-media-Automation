# 🤖 AI-Powered Advertisement Generation System

An advanced system that converts your n8n workflow into a fully functional AI-powered advertisement generator with intelligent image creation, quality analysis, and automated Instagram posting.

## 🎯 Features

### 🔄 Enhanced n8n Workflow
The original n8n workflow has been transformed into a comprehensive system:

**Original Flow:**
1. Manual Trigger → Set Image & Caption → Create Container → Publish

**Enhanced AI Flow:**
1. **Topic Input** → AI prompt generation (Gemini)
2. **Image Generation** → High-quality ads (Ideogram)  
3. **Quality Analysis** → Automated review (Gemini Vision)
4. **Smart Decisions** → Edit vs Regenerate logic
5. **Instagram Posting** → Automated publishing

### 🎨 AI-Powered Image Generation
- **Gemini Pro**: Converts topics into optimized image prompts
- **Ideogram v2**: Generates professional advertisement images
- **Minimal Text**: Optimized for AI models (no text artifacts)
- **Brand-Focused**: Creates visually striking ads that convert

### 👁️ Intelligent Quality Control
- **Gemini Vision**: Analyzes generated images for:
  - Semantic match to original prompt
  - Visual quality and composition
  - Text readability (if present)
  - Brand suitability for advertisements
  - Technical quality and artifacts
  - Safety and content appropriateness

### 🧠 Smart Decision Logic
- **APPROVE**: Score ≥7.5 → Ready for posting
- **EDIT**: Score 6.0-7.4 → Apply targeted improvements
- **REGENERATE**: Score <6.0 → Create new image with improved prompt

### 📊 Batch Processing
- **Excel Upload**: Process multiple topics at once
- **Scheduling**: Plan content for future dates
- **User Management**: Multi-user support with authentication

## 🛠️ Setup & Installation

### Prerequisites
1. **API Keys Required:**
   - `GEMINI_API_KEY` - Google AI Studio
   - `IDEOGRAM_API_KEY` - Ideogram API  
   - `FACEBOOK_ACCESS_TOKEN` - Facebook Graph API
   - `INSTAGRAM_BUSINESS_ACCOUNT_ID` - Instagram Business Account

2. **System Requirements:**
   - Python 3.8+
   - PostgreSQL (or SQLite for development)
   - Redis (for scheduling)

### Quick Start

1. **Clone and Install:**
```bash
cd n8ntocode
pip install -r requirements.txt
```

2. **Configure Environment:**
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. **Run the Application:**
```bash
python app.py
# or use the quick start script
chmod +x run.sh
./run.sh
```

4. **Access the Interface:**
```
http://localhost:8000
```

## 📋 API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - User login
- `GET /auth/me` - Get user info

### Advertisement Generation
- `GET /` - Main dashboard
- `GET /simple` - Single ad generation interface
- `POST /generate-ad` - Generate single advertisement
- `POST /upload-excel` - Batch upload topics
- `POST /post-to-instagram` - Post to Instagram

### Data Management
- `GET /topics` - Get user's topics
- `GET /download-sample-excel` - Download Excel template

## 📊 Excel Format

Expected columns in your Excel file:

| Column | Description | Required |
|--------|-------------|----------|
| `date` | Posting date/time | No |
| `topic_title` | Advertisement topic | **Yes** |
| `textual_description` | Detailed description | **Yes** |
| `target_accounts` | Target audience | No |
| `image_constraints` | Image requirements | No |

### Example Excel Content:
```
date                | topic_title        | textual_description                                    | target_accounts      | image_constraints
2024-01-15 10:00   | Summer Sale        | Promote 50% off summer collection with bright visuals | @fashion_lovers      | Bright colors, show products
2024-01-16 14:00   | New Product Launch | Launch our latest smartwatch with modern imagery      | @tech_enthusiasts    | Clean background, product focus
```

## 🎨 How It Works

### 1. Topic Analysis (Gemini)
```python
# Input: "Summer Sale - 50% off fashion items"
# Output: Optimized prompt for image generation
{
  "prompt": "Professional minimalist advertisement for summer sale, vibrant fashion items, 50% discount highlight, modern commercial style",
  "negative_prompt": "text artifacts, extra fingers, watermarks, cluttered composition",
  "style": "modern-commercial",
  "aspect_ratio": "1:1"
}
```

### 2. Image Generation (Ideogram)
- Uses Ideogram v2 model
- Square format (1:1) optimized for Instagram
- Professional advertisement style
- High resolution output

### 3. Quality Analysis (Gemini Vision)
```python
# Analyzes generated image and returns:
{
  "scores": {
    "semantic_match": 8.5,
    "visual_quality": 9.0,
    "brand_suitability": 8.8,
    "technical_quality": 9.2
  },
  "overall_score": 8.9,
  "decision": "APPROVE",
  "is_postable": true
}
```

### 4. Decision Logic
- **High Score (≥7.5)**: Auto-approve for posting
- **Medium Score (6.0-7.4)**: Apply targeted edits
- **Low Score (<6.0)**: Regenerate with improved prompt

## 🔐 Security Features

- **JWT Authentication**: Secure user sessions
- **API Key Encryption**: Secure credential storage
- **User Isolation**: Each user's data is separated
- **Input Validation**: Prevent malicious uploads
- **Rate Limiting**: Prevent API abuse

## 🚀 Advanced Usage

### Custom Brand Prompts
```python
# Brand Context Example
brand_context = """
Modern sustainable fashion brand
Target: Eco-conscious millennials
Style: Clean, minimalist, earth tones
Values: Sustainability, quality, transparency
"""

# Image Constraints Example
constraints = """
- Use earth tones (green, brown, beige)
- Show sustainable materials
- Include recycling symbols
- Minimal text overlay
- Professional product photography style
"""
```

### Batch Processing
1. Prepare Excel file with multiple topics
2. Upload via dashboard
3. System processes each topic automatically
4. Review and approve generated ads
5. Schedule for Instagram posting

## 📈 Monitoring & Analytics

### Quality Metrics Tracked
- **Generation Success Rate**: % of successful generations
- **Average Quality Score**: Mean score across all images
- **Decision Distribution**: APPROVE/EDIT/REGENERATE ratios
- **Processing Time**: Average time per generation

### User Analytics
- **Topics Created**: Total and per-user counts
- **Images Generated**: Success/failure rates
- **Instagram Posts**: Posted vs generated ratios

## 🐛 Troubleshooting

### Common Issues

1. **"Missing API Keys"**
   - Ensure all required keys are in `.env`
   - Check API key validity and permissions

2. **"Image Generation Failed"**
   - Verify Ideogram API key and credits
   - Check prompt complexity and constraints

3. **"Quality Analysis Error"**
   - Confirm Gemini API access
   - Verify image file exists and is readable

4. **"Instagram Posting Failed"**
   - Check Facebook access token permissions
   - Verify Instagram Business Account connection

### Debug Mode
```bash
# Run with debug logging
DEBUG=true python app.py
```

## 🔄 Migration from Original n8n

Your original n8n workflow data can be preserved:

1. **Image URLs**: System now generates instead of using provided URLs
2. **Captions**: Enhanced with AI-optimized content
3. **Posting Logic**: Same Instagram Graph API integration
4. **Scheduling**: Enhanced with database-backed scheduling

## 🚀 Future Enhancements

- **Video Generation**: Support for video advertisements
- **Multi-Platform**: Post to Facebook, Twitter, TikTok
- **A/B Testing**: Generate multiple variants for testing
- **Analytics Integration**: Track engagement metrics
- **Custom Models**: Train brand-specific AI models

## 📞 Support

For issues and feature requests:
1. Check the troubleshooting section
2. Review API documentation
3. Open GitHub issue with details

---

**🎉 Congratulations!** You've successfully converted your n8n workflow into a powerful AI-driven advertisement generation system!