from fastapi import FastAPI, Request, Form, HTTPException, Depends, UploadFile, File, Response
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import uvicorn
import os
import tempfile
from datetime import timedelta

# Import our services and models
from instagram_agent import InstagramAgent
from models.database import get_db, create_tables, User, Topic
from auth.auth import (
    AuthService, get_current_active_user, UserCreate, UserLogin, 
    Token, UserResponse
)
from services.ad_generation_service import AdGenerationService
from services.excel_service import ExcelService
from services.image_upload_service import ImageUploadService

# Create tables on startup
create_tables()

app = FastAPI(
    title="AI-Powered Advertisement Generation System", 
    description="Generate high-quality brand advertisements using AI and post to Instagram"
)

templates = Jinja2Templates(directory="templates")

# Mount static files for serving generated images
images_dir = os.path.abspath("generated_images")
os.makedirs(images_dir, exist_ok=True)

print(f"📁 Images directory: {images_dir}")
print(f"📋 Directory exists: {os.path.exists(images_dir)}")

app.mount("/images", StaticFiles(directory=images_dir), name="images")
app.mount("/generated_images", StaticFiles(directory=images_dir), name="generated_images")

# Authentication endpoints
@app.post("/auth/register", response_model=Token)
async def register(user_data: UserCreate, response: Response, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        user = AuthService.create_user(db, user_data.email, user_data.password)
        access_token = AuthService.create_access_token(data={"sub": user.email})
        # Set auth token cookie for form submissions without JS headers
        response.set_cookie(
            key="authToken",
            value=access_token,
            max_age=60*60*24*7,  # 7 days
            httponly=False,
            samesite="lax",
            path="/"
        )
        # Also set sb-access-token for compatibility with other clients
        response.set_cookie(
            key="sb-access-token",
            value=access_token,
            max_age=60*60*24*7,
            httponly=False,
            samesite="lax",
            path="/"
        )
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin, response: Response, db: Session = Depends(get_db)):
    """Login user"""
    user = AuthService.authenticate_user(db, user_data.email, user_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = AuthService.create_access_token(data={"sub": user.email})
    # Set auth token cookie for form submissions without JS headers
    response.set_cookie(
        key="authToken",
        value=access_token,
        max_age=60*60*24*7,  # 7 days
        httponly=False,
        samesite="lax",
        path="/"
    )
    response.set_cookie(
        key="sb-access-token",
        value=access_token,
        max_age=60*60*24*7,
        httponly=False,
        samesite="lax",
        path="/"
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user

# Main application endpoints
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with the new AI-powered interface"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/simple", response_class=HTMLResponse)
async def simple_interface(request: Request):
    """Simple single-topic generation interface"""
    return templates.TemplateResponse("simple.html", {"request": request})

@app.post("/generate-ad")
async def generate_advertisement(
    request: Request,
    topic: str = Form(...),
    brand_context: str = Form(""),
    constraints: str = Form(""),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Generate a single advertisement using AI"""
    try:
        # Create topic in database
        db_topic = Topic(
            user_id=current_user.id,
            topic_title=topic,
            textual_description=topic,
            brand_context=brand_context,
            image_constraints=constraints,
            status='processing'
        )
        db.add(db_topic)
        db.commit()
        db.refresh(db_topic)
        
        # Generate advertisement
        ad_service = AdGenerationService()
        result = ad_service.generate_advertisement(topic, brand_context, constraints)
        
        # Update topic status
        db_topic.status = 'completed' if result['success'] else 'failed'
        db.commit()
        
        return templates.TemplateResponse("ad_result.html", {
            "request": request,
            "result": result,
            "topic": topic,
            "brand_context": brand_context,
            "constraints": constraints,
            "topic_id": db_topic.id
        })
        
    except Exception as e:
        if 'db_topic' in locals():
            db_topic.status = 'failed'
            db.commit()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-excel")
async def upload_excel(
    file: UploadFile = File(...),
    schedule_name: str = Form(""),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload Excel file with multiple topics"""
    try:
        # Validate file type
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="Please upload an Excel file (.xlsx or .xls)")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # Validate Excel format first
            validation = ExcelService.validate_excel_format(tmp_file_path)
            if not validation['valid']:
                raise HTTPException(status_code=400, detail=f"Invalid Excel format: {validation['error']}")
            
            # Create topics from Excel
            result = ExcelService.create_topics_from_excel(
                db, current_user, tmp_file_path, schedule_name or f"Upload_{file.filename}"
            )
            
            return JSONResponse(content=result)
            
        finally:
            # Clean up temporary file
            os.unlink(tmp_file_path)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download-sample-excel")
async def download_sample_excel():
    """Download sample Excel template"""
    try:
        sample_path = "sample_template.xlsx"
        if ExcelService.create_sample_excel(sample_path):
            return {"download_url": f"/static/{sample_path}"}
        else:
            raise HTTPException(status_code=500, detail="Failed to create sample file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/post-to-instagram")
async def post_to_instagram(
    request: Request,
    image_filename: str = Form(...),
    caption: str = Form(...),
    topic_id: int = Form(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Post generated image to Instagram"""
    print(f"🎯 Instagram posting request from user: {current_user.email}")
    print(f"📋 Request details: image={image_filename}, caption={caption[:50]}..., topic_id={topic_id}")
    try:
        # Verify topic belongs to user
        topic = db.query(Topic).filter(
            Topic.id == topic_id, 
            Topic.user_id == current_user.id
        ).first()
        
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        # Verify image file exists
        image_path = os.path.join(os.path.abspath("generated_images"), image_filename)
        if not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail=f"Image file not found: {image_filename}")
        
        # Upload image to IMGBB for public access
        print(f"🌐 Uploading image to IMGBB: {image_filename}")
        image_url = ImageUploadService.get_public_url(image_path)
        
        if not image_url:
            raise HTTPException(
                status_code=500, 
                detail="Failed to upload image to public service. Please check your IMGBB_API_KEY."
            )
        
        print(f"📤 Posting to Instagram:")
        print(f"   Image file: {image_filename}")
        print(f"   Image path: {image_path}")
        print(f"   Public image URL: {image_url}")
        print(f"   Caption: {caption[:50]}...")
        
        # Post to Instagram using public image URL
        agent = InstagramAgent()
        result = agent.post_to_instagram(image_url, caption)
        
        print(f"📊 Instagram result: {result}")
        # Augment result with helpful diagnostics
        if isinstance(result, dict):
            result.setdefault('requested_image_filename', image_filename)
            result.setdefault('public_image_url', image_url)
            result.setdefault('local_image_path', image_path)
        return JSONResponse(content=result)
        
    except Exception as e:
        print(f"❌ Instagram posting error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/post-direct-image")
async def post_direct_image(
    image_url: str = Form(...),
    caption: str = Form(...),
    current_user: User = Depends(get_current_active_user)
):
    """Post image directly to Instagram using URL"""
    try:        
        print(f"🎯 Direct Instagram posting request from user: {current_user.email}")
        print(f"📋 Request details: image_url={image_url}, caption={caption[:50]}...")
        
        # Validate URL format
        try:
            from urllib.parse import urlparse
            parsed = urlparse(image_url)
            if not parsed.scheme or not parsed.netloc:
                raise HTTPException(status_code=400, detail="Invalid image URL format")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid image URL format")
        
        # Post to Instagram directly with the provided URL - same logic as existing endpoint
        agent = InstagramAgent()
        result = agent.post_to_instagram(image_url, caption)
        
        print(f"📊 Direct Instagram result: {result}")
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Direct Instagram posting error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/topics")
async def get_user_topics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's topics"""
    topics = db.query(Topic).filter(Topic.user_id == current_user.id).all()
    return [
        {
            "id": topic.id,
            "title": topic.topic_title,
            "description": topic.textual_description,
            "status": topic.status,
            "scheduled_date": topic.scheduled_date,
            "created_at": topic.created_at
        }
        for topic in topics
    ]

@app.get("/serve-image/{filename}")
async def serve_image(filename: str):
    """Serve generated images directly"""
    image_path = os.path.join(os.path.abspath("generated_images"), filename)
    
    print(f"🔍 Looking for image: {image_path}")
    print(f"📋 File exists: {os.path.exists(image_path)}")
    
    if os.path.exists(image_path):
        return FileResponse(
            image_path,
            media_type="image/png",
            headers={"Content-Disposition": f"inline; filename={filename}"}
        )
    else:
        # List files in directory for debugging
        images_dir = os.path.abspath("generated_images")
        if os.path.exists(images_dir):
            files = os.listdir(images_dir)
            print(f"📁 Available files: {files}")
        
        raise HTTPException(
            status_code=404, 
            detail=f"Image not found: {filename}. Available files: {files if 'files' in locals() else 'Directory not found'}"
        )

@app.get("/ideogram-urls")
async def get_ideogram_urls(
    limit: int = 50,
    current_user: User = Depends(get_current_active_user)
):
    """Get logged Ideogram URLs"""
    try:
        ad_service = AdGenerationService()
        urls = ad_service.get_logged_urls(limit)
        return JSONResponse(content={"urls": urls, "count": len(urls)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get-unposted-images")
async def get_unposted_images(
    current_user: User = Depends(get_current_active_user)
):
    """Get unposted images from Ideogram logs"""
    try:
        ad_service = AdGenerationService()
        unposted = ad_service.get_unposted_images()
        return JSONResponse(content={"images": unposted, "count": len(unposted)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mark-as-posted")
async def mark_as_posted(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Mark an image as posted to Instagram"""
    try:
        body = await request.json()
        workflow_id = body.get('workflow_id')
        
        if not workflow_id:
            raise HTTPException(status_code=400, detail="workflow_id is required")
        
        ad_service = AdGenerationService()
        result = ad_service.mark_as_posted(workflow_id)
        
        return JSONResponse(content={"success": result})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "2.0.0"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)