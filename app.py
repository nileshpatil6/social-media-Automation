from fastapi import FastAPI, Request, Form, HTTPException, Depends, UploadFile, File, Response
from typing import Optional, Dict, Any
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import uvicorn
import os
import tempfile
from datetime import datetime, timedelta, timezone

# Import our services and models
from instagram_agent import InstagramAgent
from twitter_agent import TwitterAgent
from linkedin_agent import LinkedInAgent
from youtube_agent import YouTubeAgent
from facebook_agent import FacebookAgent
from models.database import get_db, create_tables, User, Topic, ScheduledPost
from auth.auth import (
    AuthService, get_current_active_user, UserCreate, UserLogin, 
    Token, UserResponse
)
from services.ad_generation_service import AdGenerationService
from services.excel_service import ExcelService
from services.image_upload_service import ImageUploadService
from services.scheduling_service import SchedulingService, ScheduledPostRunner

# Create tables on startup
create_tables()

app = FastAPI(
    title="AI-Powered Advertisement Generation System", 
    description="Generate high-quality brand advertisements using AI and post to Instagram"
)

templates = Jinja2Templates(directory="templates")

# Mount static files for serving generated images
images_dir = os.path.abspath("generated_images")
static_dir = os.path.abspath("static")

# Create required directories
os.makedirs(images_dir, exist_ok=True)
os.makedirs(static_dir, exist_ok=True)

print(f"[startup] Images directory: {images_dir}")
print(f"[startup] Static directory: {static_dir}")
print(f"[startup] Images directory exists: {os.path.exists(images_dir)}")
print(f"[startup] Static directory exists: {os.path.exists(static_dir)}")

app.mount("/images", StaticFiles(directory=images_dir), name="images")
app.mount("/generated_images", StaticFiles(directory=images_dir), name="generated_images")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Scheduling setup
scheduler_runner = ScheduledPostRunner()
scheduling_service = scheduler_runner.service

def serialize_scheduled_post(post: ScheduledPost) -> Dict[str, Any]:
    return {
        "id": post.id,
        "topic_id": post.topic_id,
        "image_filename": post.image_filename,
        "image_url": post.image_url,
        "caption": post.caption,
        "schedule_time": post.schedule_time.replace(tzinfo=timezone.utc).isoformat() if post.schedule_time else None,
        "timezone": post.timezone,
        "status": post.status,
        "platform": post.platform,
        "attempts": post.attempts,
        "max_attempts": post.max_attempts,
        "next_attempt_after": post.next_attempt_after.replace(tzinfo=timezone.utc).isoformat() if post.next_attempt_after else None,
        "last_error": post.last_error,
        "last_error_details": post.last_error_details,
        "posted_at": post.posted_at.replace(tzinfo=timezone.utc).isoformat() if post.posted_at else None,
        "result": post.result_payload,
        "created_at": post.created_at.replace(tzinfo=timezone.utc).isoformat() if post.created_at else None,
        "updated_at": post.updated_at.replace(tzinfo=timezone.utc).isoformat() if getattr(post, "updated_at", None) else None,
        "metadata": post.job_metadata,
    }

@app.on_event("startup")
async def start_scheduler():
    await scheduler_runner.start()


@app.on_event("shutdown")
async def stop_scheduler():
    await scheduler_runner.stop()

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
    scheduled_time: Optional[str] = Form(None),
    schedule_timezone: Optional[str] = Form("UTC"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Post generated image immediately or schedule it for later."""

    try:
        topic = db.query(Topic).filter(
            Topic.id == topic_id,
            Topic.user_id == current_user.id
        ).first()

        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        image_path = os.path.join(os.path.abspath("generated_images"), image_filename)
        if not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail=f"Image file not found: {image_filename}")

        scheduled_time_value = (scheduled_time or "").strip() or None
        timezone_value = (schedule_timezone or "").strip() or None

        print(
            f"[post-to-instagram] user={current_user.email} image={image_filename} "
            f"caption_preview={caption[:50]}... topic_id={topic_id} "
            f"scheduled_time={scheduled_time_value} timezone={timezone_value}"
        )

        if scheduled_time_value:
            try:
                schedule_dt, tz_name = scheduling_service.parse_scheduled_datetime(scheduled_time_value, timezone_value)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))

            preview_url = ImageUploadService.get_public_url(image_path)
            metadata = {
                "source": "generated_image",
                "topic_id": topic_id,
                "preview_url": preview_url,
                "requested_by": current_user.email,
                "requested_at": datetime.now(timezone.utc).isoformat(),
            }

            scheduled = scheduling_service.schedule_post(
                db=db,
                user_id=current_user.id,
                caption=caption,
                schedule_time=schedule_dt,
                timezone_name=tz_name,
                image_url=preview_url,
                image_filename=image_filename,
                topic_id=topic_id,
                platform="instagram",
                metadata=metadata,
            )

            return JSONResponse(
                status_code=201,
                content={
                    "success": True,
                    "scheduled": True,
                    "scheduled_post": serialize_scheduled_post(scheduled)
                }
            )

        print(f"[post-to-instagram] Uploading image to public host: {image_filename}")
        image_url = ImageUploadService.get_public_url(image_path)

        if not image_url:
            raise HTTPException(
                status_code=500,
                detail="Failed to upload image to public service. Please check your IMGBB_API_KEY."
            )

        print("[post-to-instagram] Publishing immediately via Graph API")
        print(f"   Image file: {image_filename}")
        print(f"   Image path: {image_path}")
        print(f"   Public image URL: {image_url}")
        print(f"   Caption: {caption[:50]}...")

        agent = InstagramAgent()
        result = agent.post_to_instagram(image_url, caption)

        print(f"[post-to-instagram] Instagram response: {result}")
        if isinstance(result, dict):
            result.setdefault("requested_image_filename", image_filename)
            result.setdefault("public_image_url", image_url)
            result.setdefault("local_image_path", image_path)
            result.setdefault("scheduled", False)
        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        print(f"[error] Instagram posting error: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/post-to-twitter")
async def post_to_twitter(
    request: Request,
    image_filename: str = Form(...),
    caption: str = Form(...),
    topic_id: int = Form(...),
    scheduled_time: Optional[str] = Form(None),
    schedule_timezone: Optional[str] = Form("UTC"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        topic = db.query(Topic).filter(
            Topic.id == topic_id,
            Topic.user_id == current_user.id
        ).first()

        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        image_path = os.path.join(os.path.abspath("generated_images"), image_filename)
        if not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail=f"Image file not found: {image_filename}")

        scheduled_time_value = (scheduled_time or "").strip() or None
        timezone_value = (schedule_timezone or "").strip() or None

        print(
            f"[post-to-twitter] user={current_user.email} image={image_filename} "
            f"caption_preview={caption[:50]}... topic_id={topic_id} "
            f"scheduled_time={scheduled_time_value} timezone={timezone_value}"
        )

        if scheduled_time_value:
            try:
                schedule_dt, tz_name = scheduling_service.parse_scheduled_datetime(scheduled_time_value, timezone_value)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))

            preview_url = ImageUploadService.get_public_url(image_path)
            metadata = {
                "source": "generated_image",
                "topic_id": topic_id,
                "preview_url": preview_url,
                "requested_by": current_user.email,
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "platform": "twitter",
            }

            scheduled = scheduling_service.schedule_post(
                db=db,
                user_id=current_user.id,
                caption=caption,
                schedule_time=schedule_dt,
                timezone_name=tz_name,
                image_url=preview_url,
                image_filename=image_filename,
                topic_id=topic_id,
                platform="twitter",
                metadata=metadata,
            )

            return JSONResponse(
                status_code=201,
                content={
                    "success": True,
                    "scheduled": True,
                    "scheduled_post": serialize_scheduled_post(scheduled)
                }
            )

        agent = TwitterAgent()
        result = agent.post_to_twitter(caption, image_path=image_path)

        print(f"[post-to-twitter] Twitter response: {result}")
        if isinstance(result, dict):
            result.setdefault("requested_image_filename", image_filename)
            result.setdefault("platform", "twitter")
            result.setdefault("scheduled", False)
        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        print(f"[error] Twitter posting error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/post-direct-twitter")
async def post_direct_twitter(
    image_url: str = Form(...),
    caption: str = Form(...),
    scheduled_time: Optional[str] = Form(None),
    schedule_timezone: Optional[str] = Form("UTC"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        scheduled_time_value = (scheduled_time or "").strip() or None
        timezone_value = (schedule_timezone or "").strip() or None

        print(
            f"[post-direct-twitter] user={current_user.email} image_url={image_url} "
            f"caption_preview={caption[:50]}... scheduled_time={scheduled_time_value} "
            f"timezone={timezone_value}"
        )

        from urllib.parse import urlparse

        parsed = urlparse(image_url)
        if not parsed.scheme or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid image URL format")

        if scheduled_time_value:
            try:
                schedule_dt, tz_name = scheduling_service.parse_scheduled_datetime(scheduled_time_value, timezone_value)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))

            metadata = {
                "source": "direct_url",
                "requested_by": current_user.email,
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "platform": "twitter",
            }

            scheduled = scheduling_service.schedule_post(
                db=db,
                user_id=current_user.id,
                caption=caption,
                schedule_time=schedule_dt,
                timezone_name=tz_name,
                image_url=image_url,
                image_filename=None,
                topic_id=None,
                platform="twitter",
                metadata=metadata,
            )

            return JSONResponse(
                status_code=201,
                content={
                    "success": True,
                    "scheduled": True,
                    "scheduled_post": serialize_scheduled_post(scheduled)
                }
            )

        agent = TwitterAgent()
        result = agent.post_to_twitter(caption, image_url=image_url)

        print(f"[post-direct-twitter] Twitter response: {result}")
        if isinstance(result, dict):
            result.setdefault("platform", "twitter")
            result.setdefault("image_url", image_url)
            result.setdefault("scheduled", False)
        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        print(f"[error] Direct Twitter posting error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/post-direct-image")
async def post_direct_image(
    image_url: str = Form(...),
    caption: str = Form(...),
    scheduled_time: Optional[str] = Form(None),
    schedule_timezone: Optional[str] = Form("UTC"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Post image directly to Instagram using URL or schedule it."""
    try:

        scheduled_time_value = (scheduled_time or "").strip() or None
        timezone_value = (schedule_timezone or "").strip() or None

        print(
            f"[post-direct-image] user={current_user.email} image_url={image_url} "
            f"caption_preview={caption[:50]}... scheduled_time={scheduled_time_value} "
            f"timezone={timezone_value}"
        )

        # Validate URL format
        try:
            from urllib.parse import urlparse
            parsed = urlparse(image_url)
            if not parsed.scheme or not parsed.netloc:
                raise HTTPException(status_code=400, detail="Invalid image URL format")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid image URL format")

        if scheduled_time_value:
            try:
                schedule_dt, tz_name = scheduling_service.parse_scheduled_datetime(scheduled_time_value, timezone_value)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))

            metadata = {
                "source": "direct_url",
                "requested_by": current_user.email,
                "requested_at": datetime.now(timezone.utc).isoformat(),
            }

            scheduled = scheduling_service.schedule_post(
                db=db,
                user_id=current_user.id,
                caption=caption,
                schedule_time=schedule_dt,
                timezone_name=tz_name,
                image_url=image_url,
                image_filename=None,
                topic_id=None,
                metadata=metadata,
            )

            return JSONResponse(
                status_code=201,
                content={
                    "success": True,
                    "scheduled": True,
                    "scheduled_post": serialize_scheduled_post(scheduled)
                }
            )

        if not ImageUploadService._is_public_image_url(image_url):
            raise HTTPException(status_code=400, detail="Image URL must be publicly accessible")

        agent = InstagramAgent()
        result = agent.post_to_instagram(image_url, caption)

        print(f"[post-direct-image] Instagram response: {result}")

        if isinstance(result, dict):
            result.setdefault("scheduled", False)
            result.setdefault("public_image_url", image_url)
        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        print(f"[error] Direct Instagram posting error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/post-to-linkedin")
async def post_to_linkedin(
    request: Request,
    image_filename: str = Form(...),
    text: str = Form(...),
    topic_id: int = Form(...),
    scheduled_time: Optional[str] = Form(None),
    schedule_timezone: Optional[str] = Form("UTC"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        topic = db.query(Topic).filter(
            Topic.id == topic_id,
            Topic.user_id == current_user.id
        ).first()

        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        image_path = os.path.join(os.path.abspath("generated_images"), image_filename)
        if not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail=f"Image file not found: {image_filename}")

        scheduled_time_value = (scheduled_time or "").strip() or None
        timezone_value = (schedule_timezone or "").strip() or None

        print(
            f"[post-to-linkedin] user={current_user.email} image={image_filename} "
            f"text_preview={text[:50]}... topic_id={topic_id} "
            f"scheduled_time={scheduled_time_value} timezone={timezone_value}"
        )

        if scheduled_time_value:
            try:
                schedule_dt, tz_name = scheduling_service.parse_scheduled_datetime(scheduled_time_value, timezone_value)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))

            preview_url = ImageUploadService.get_public_url(image_path)
            metadata = {
                "source": "generated_image",
                "topic_id": topic_id,
                "preview_url": preview_url,
                "requested_by": current_user.email,
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "platform": "linkedin",
            }

            scheduled = scheduling_service.schedule_post(
                db=db,
                user_id=current_user.id,
                caption=text,  # Using 'caption' field for text in the database
                schedule_time=schedule_dt,
                timezone_name=tz_name,
                image_url=preview_url,
                image_filename=image_filename,
                topic_id=topic_id,
                platform="linkedin",
                metadata=metadata,
            )

            return JSONResponse(
                status_code=201,
                content={
                    "success": True,
                    "scheduled": True,
                    "scheduled_post": serialize_scheduled_post(scheduled)
                }
            )

        agent = LinkedInAgent()
        result = agent.post_to_linkedin(text, image_path=image_path)

        print(f"[post-to-linkedin] LinkedIn response: {result}")
        if isinstance(result, dict):
            result.setdefault("requested_image_filename", image_filename)
            result.setdefault("platform", "linkedin")
            result.setdefault("scheduled", False)
        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        print(f"[error] LinkedIn posting error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/post-direct-linkedin")
async def post_direct_linkedin(
    image_url: str = Form(...),
    text: str = Form(...),
    scheduled_time: Optional[str] = Form(None),
    schedule_timezone: Optional[str] = Form("UTC"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        scheduled_time_value = (scheduled_time or "").strip() or None
        timezone_value = (schedule_timezone or "").strip() or None

        print(
            f"[post-direct-linkedin] user={current_user.email} image_url={image_url} "
            f"text_preview={text[:50]}... scheduled_time={scheduled_time_value} "
            f"timezone={timezone_value}"
        )

        from urllib.parse import urlparse

        parsed = urlparse(image_url)
        if not parsed.scheme or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid image URL format")

        if scheduled_time_value:
            try:
                schedule_dt, tz_name = scheduling_service.parse_scheduled_datetime(scheduled_time_value, timezone_value)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))

            metadata = {
                "source": "direct_url",
                "requested_by": current_user.email,
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "platform": "linkedin",
            }

            scheduled = scheduling_service.schedule_post(
                db=db,
                user_id=current_user.id,
                caption=text,  # Using 'caption' field for text in the database
                schedule_time=schedule_dt,
                timezone_name=tz_name,
                image_url=image_url,
                image_filename=None,
                topic_id=None,
                platform="linkedin",
                metadata=metadata,
            )

            return JSONResponse(
                status_code=201,
                content={
                    "success": True,
                    "scheduled": True,
                    "scheduled_post": serialize_scheduled_post(scheduled)
                }
            )

        agent = LinkedInAgent()
        result = agent.post_to_linkedin(text, image_url=image_url)

        print(f"[post-direct-linkedin] LinkedIn response: {result}")
        if isinstance(result, dict):
            result.setdefault("platform", "linkedin")
            result.setdefault("image_url", image_url)
            result.setdefault("scheduled", False)
        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        print(f"[error] Direct LinkedIn posting error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/post-to-youtube")
async def post_to_youtube(
    request: Request,
    video_filename: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    topic_id: int = Form(...),
    scheduled_time: Optional[str] = Form(None),
    schedule_timezone: Optional[str] = Form("UTC"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        topic = db.query(Topic).filter(
            Topic.id == topic_id,
            Topic.user_id == current_user.id
        ).first()

        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        video_path = os.path.join(os.path.abspath("generated_images"), video_filename)  # Using same directory for now
        if not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail=f"Video file not found: {video_filename}")

        # Validate it's a video file
        import mimetypes
        mime_type, _ = mimetypes.guess_type(video_path)
        if not mime_type or not mime_type.startswith('video'):
            raise HTTPException(status_code=400, detail="File must be a video")

        scheduled_time_value = (scheduled_time or "").strip() or None
        timezone_value = (schedule_timezone or "").strip() or None

        print(
            f"[post-to-youtube] user={current_user.email} video={video_filename} "
            f"title_preview={title[:50]}... topic_id={topic_id} "
            f"scheduled_time={scheduled_time_value} timezone={timezone_value}"
        )

        if scheduled_time_value:
            try:
                schedule_dt, tz_name = scheduling_service.parse_scheduled_datetime(scheduled_time_value, timezone_value)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))

            # For YouTube, we can't schedule directly via API, so we'll schedule it in our system
            # and upload when the time comes
            preview_url = f"/serve-image/{video_filename}"  # This is a placeholder
            metadata = {
                "source": "generated_video",
                "topic_id": topic_id,
                "preview_url": preview_url,
                "requested_by": current_user.email,
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "platform": "youtube",
            }

            scheduled = scheduling_service.schedule_post(
                db=db,
                user_id=current_user.id,
                caption=title,  # Using 'caption' field for title in the database
                schedule_time=schedule_dt,
                timezone_name=tz_name,
                image_url=preview_url,  # Using image_url for video URL in DB
                image_filename=video_filename,  # Using image_filename for video filename
                topic_id=topic_id,
                platform="youtube",
                metadata=metadata,
            )

            return JSONResponse(
                status_code=201,
                content={
                    "success": True,
                    "scheduled": True,
                    "scheduled_post": serialize_scheduled_post(scheduled)
                }
            )

        agent = YouTubeAgent()
        result = agent.post_to_youtube(
            title=title,
            description=description,
            file_path=video_path
        )

        print(f"[post-to-youtube] YouTube response: {result}")
        if isinstance(result, dict):
            result.setdefault("requested_video_filename", video_filename)
            result.setdefault("platform", "youtube")
            result.setdefault("scheduled", False)
        return JSONResponse(content=result)

    except HTTPException:
        raise
    except ImportError as e:
        print(f"[error] YouTube import error: {e}")
        raise HTTPException(status_code=500, detail=f"YouTube library not properly installed: {str(e)}")
    except Exception as e:
        print(f"[error] YouTube posting error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/post-direct-youtube")
async def post_direct_youtube(
    video_url: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    scheduled_time: Optional[str] = Form(None),
    schedule_timezone: Optional[str] = Form("UTC"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        scheduled_time_value = (scheduled_time or "").strip() or None
        timezone_value = (schedule_timezone or "").strip() or None

        print(
            f"[post-direct-youtube] user={current_user.email} video_url={video_url} "
            f"title_preview={title[:50]}... scheduled_time={scheduled_time_value} "
            f"timezone={timezone_value}"
        )

        from urllib.parse import urlparse

        parsed = urlparse(video_url)
        if not parsed.scheme or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid video URL format")

        if scheduled_time_value:
            try:
                schedule_dt, tz_name = scheduling_service.parse_scheduled_datetime(scheduled_time_value, timezone_value)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))

            metadata = {
                "source": "direct_url",
                "requested_by": current_user.email,
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "platform": "youtube",
            }

            scheduled = scheduling_service.schedule_post(
                db=db,
                user_id=current_user.id,
                caption=title,  # Using 'caption' field for title in the database
                schedule_time=schedule_dt,
                timezone_name=tz_name,
                image_url=video_url,  # Using image_url for video URL in DB
                image_filename=None,
                topic_id=None,
                platform="youtube",
                metadata=metadata,
            )

            return JSONResponse(
                status_code=201,
                content={
                    "success": True,
                    "scheduled": True,
                    "scheduled_post": serialize_scheduled_post(scheduled)
                }
            )

        agent = YouTubeAgent()
        result = agent.post_to_youtube(
            title=title,
            description=description,
            file_url=video_url
        )

        print(f"[post-direct-youtube] YouTube response: {result}")
        if isinstance(result, dict):
            result.setdefault("platform", "youtube")
            result.setdefault("video_url", video_url)
            result.setdefault("scheduled", False)
        return JSONResponse(content=result)

    except HTTPException:
        raise
    except ImportError as e:
        print(f"[error] YouTube import error: {e}")
        raise HTTPException(status_code=500, detail=f"YouTube library not properly installed: {str(e)}")
    except Exception as e:
        print(f"[error] Direct YouTube posting error: {e}")
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


@app.get("/scheduled-posts")
async def list_scheduled_posts(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List scheduled Instagram posts for the current user."""
    query = db.query(ScheduledPost).filter(ScheduledPost.user_id == current_user.id)

    if status:
        status_value = status.lower()
        if status_value == "upcoming":
            query = query.filter(ScheduledPost.status.in_(["pending", "retry"]))
        else:
            query = query.filter(ScheduledPost.status == status_value)

    posts = query.order_by(ScheduledPost.schedule_time.asc(), ScheduledPost.id.asc()).limit(100).all()
    return {
        "count": len(posts),
        "scheduled_posts": [serialize_scheduled_post(post) for post in posts]
    }


@app.delete("/scheduled-posts/{post_id}")
async def cancel_scheduled_post(
    post_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cancel a scheduled Instagram post."""
    post = db.query(ScheduledPost).filter(
        ScheduledPost.id == post_id,
        ScheduledPost.user_id == current_user.id
    ).first()

    if not post:
        raise HTTPException(status_code=404, detail="Scheduled post not found")

    if post.status == "completed":
        raise HTTPException(status_code=400, detail="Post already completed")

    post.status = "cancelled"
    post.next_attempt_after = None
    db.commit()
    db.refresh(post)
    return {"success": True, "scheduled_post": serialize_scheduled_post(post)}


@app.post("/scheduled-posts/{post_id}/retry")
async def retry_scheduled_post(
    post_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Retry a failed or cancelled scheduled post."""
    post = db.query(ScheduledPost).filter(
        ScheduledPost.id == post_id,
        ScheduledPost.user_id == current_user.id
    ).first()

    if not post:
        raise HTTPException(status_code=404, detail="Scheduled post not found")

    now_utc = datetime.now(timezone.utc)
    if post.schedule_time and post.schedule_time < now_utc:
        post.schedule_time = now_utc + timedelta(seconds=5)

    post.status = "pending"
    post.next_attempt_after = None
    post.last_error = None
    post.last_error_details = None
    post.attempts = 0
    db.commit()
    db.refresh(post)
    return {"success": True, "scheduled_post": serialize_scheduled_post(post)}

@app.get("/serve-image/{filename}")
async def serve_image(filename: str):
    """Serve generated images directly"""
    image_path = os.path.join(os.path.abspath("generated_images"), filename)
    
    print(f"[serve-image] Lookup: {image_path}")
    print(f"[serve-image] Exists: {os.path.exists(image_path)}")
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

@app.post("/post-to-facebook")
async def post_to_facebook(
    request: Request,
    image_filename: str = Form(...),
    text: str = Form(...),
    topic_id: int = Form(...),
    scheduled_time: Optional[str] = Form(None),
    schedule_timezone: Optional[str] = Form("UTC"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        topic = db.query(Topic).filter(
            Topic.id == topic_id,
            Topic.user_id == current_user.id
        ).first()

        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        image_path = os.path.join(os.path.abspath("generated_images"), image_filename)
        if not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail=f"Image file not found: {image_filename}")

        scheduled_time_value = (scheduled_time or "").strip() or None
        timezone_value = (schedule_timezone or "").strip() or None

        print(
            f"[post-to-facebook] user={current_user.email} image={image_filename} "
            f"text_preview={text[:50]}... topic_id={topic_id} "
            f"scheduled_time={scheduled_time_value} timezone={timezone_value}"
        )

        if scheduled_time_value:
            try:
                schedule_dt, tz_name = scheduling_service.parse_scheduled_datetime(scheduled_time_value, timezone_value)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))

            preview_url = ImageUploadService.get_public_url(image_path)
            metadata = {
                "source": "generated_image",
                "topic_id": topic_id,
                "preview_url": preview_url,
                "requested_by": current_user.email,
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "platform": "facebook",
            }

            scheduled = scheduling_service.schedule_post(
                db=db,
                user_id=current_user.id,
                caption=text,  # Using 'caption' field for text in the database
                schedule_time=schedule_dt,
                timezone_name=tz_name,
                image_url=preview_url,
                image_filename=image_filename,
                topic_id=topic_id,
                platform="facebook",
                metadata=metadata,
            )

            return JSONResponse(
                status_code=201,
                content={
                    "success": True,
                    "scheduled": True,
                    "scheduled_post": serialize_scheduled_post(scheduled)
                }
            )

        agent = FacebookAgent()
        result = agent.post_to_facebook(text, image_path=image_path)

        print(f"[post-to-facebook] Facebook response: {result}")
        if isinstance(result, dict):
            result.setdefault("requested_image_filename", image_filename)
            result.setdefault("platform", "facebook")
            result.setdefault("scheduled", False)
        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        print(f"[error] Facebook posting error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/post-direct-facebook")
async def post_direct_facebook(
    image_url: str = Form(...),
    text: str = Form(...),
    scheduled_time: Optional[str] = Form(None),
    schedule_timezone: Optional[str] = Form("UTC"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        scheduled_time_value = (scheduled_time or "").strip() or None
        timezone_value = (schedule_timezone or "").strip() or None

        print(
            f"[post-direct-facebook] user={current_user.email} image_url={image_url} "
            f"text_preview={text[:50]}... scheduled_time={scheduled_time_value} "
            f"timezone={timezone_value}"
        )

        from urllib.parse import urlparse

        parsed = urlparse(image_url)
        if not parsed.scheme or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid image URL format")

        if scheduled_time_value:
            try:
                schedule_dt, tz_name = scheduling_service.parse_scheduled_datetime(scheduled_time_value, timezone_value)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))

            metadata = {
                "source": "direct_url",
                "requested_by": current_user.email,
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "platform": "facebook",
            }

            scheduled = scheduling_service.schedule_post(
                db=db,
                user_id=current_user.id,
                caption=text,
                schedule_time=schedule_dt,
                timezone_name=tz_name,
                image_url=image_url,
                image_filename=None,
                topic_id=None,
                platform="facebook",
                metadata=metadata,
            )

            return JSONResponse(
                status_code=201,
                content={
                    "success": True,
                    "scheduled": True,
                    "scheduled_post": serialize_scheduled_post(scheduled)
                }
            )

        agent = FacebookAgent()
        result = agent.post_to_facebook(text, image_url=image_url)

        print(f"[post-direct-facebook] Facebook response: {result}")
        if isinstance(result, dict):
            result.setdefault("platform", "facebook")
            result.setdefault("image_url", image_url)
            result.setdefault("scheduled", False)
        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        print(f"[error] Direct Facebook posting error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/post-to-multiple-channels")
async def post_to_multiple_channels(
    request: Request,
    image_filename: str = Form(...),
    topic_id: int = Form(...),
    caption: Optional[str] = Form(None),  # For Instagram/Twitter
    text: Optional[str] = Form(None),     # For Facebook/LinkedIn
    platforms: str = Form(...),           # Comma-separated list of platforms
    scheduled_time: Optional[str] = Form(None),
    schedule_timezone: Optional[str] = Form("UTC"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Post to multiple channels simultaneously
    Platforms should be sent as comma-separated values in the request
    """
    try:
        topic = db.query(Topic).filter(
            Topic.id == topic_id,
            Topic.user_id == current_user.id
        ).first()

        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        image_path = os.path.join(os.path.abspath("generated_images"), image_filename)
        if not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail=f"Image file not found: {image_filename}")

        # Parse platforms from comma-separated string
        platform_list = [p.strip().lower() for p in platforms.split(",") if p.strip()]
        
        # Validate platforms
        valid_platforms = {"instagram", "facebook", "linkedin", "twitter"}
        invalid_platforms = [p for p in platform_list if p not in valid_platforms]
        if invalid_platforms:
            raise HTTPException(status_code=400, detail=f"Invalid platforms: {invalid_platforms}")
        
        # Use either caption or text depending on what's provided
        post_content = caption or text or ""
        if not post_content:
            raise HTTPException(status_code=400, detail="Either caption or text must be provided")

        scheduled_time_value = (scheduled_time or "").strip() or None
        timezone_value = (schedule_timezone or "").strip() or None

        print(
            f"[post-to-multiple-channels] user={current_user.email} image={image_filename} "
            f"platforms={platform_list} topic_id={topic_id} "
            f"scheduled_time={scheduled_time_value} timezone={timezone_value}"
        )

        results = {}
        scheduled_any = False
        
        # If scheduling, schedule for each selected platform
        if scheduled_time_value:
            try:
                schedule_dt, tz_name = scheduling_service.parse_scheduled_datetime(scheduled_time_value, timezone_value)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))

            preview_url = ImageUploadService.get_public_url(image_path)
            metadata = {
                "source": "generated_image",
                "topic_id": topic_id,
                "preview_url": preview_url,
                "requested_by": current_user.email,
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "selected_platforms": platform_list,
            }

            for platform in platform_list:
                platform_metadata = metadata.copy()
                platform_metadata["target_platform"] = platform
                
                scheduled = scheduling_service.schedule_post(
                    db=db,
                    user_id=current_user.id,
                    caption=post_content,
                    schedule_time=schedule_dt,
                    timezone_name=tz_name,
                    image_url=preview_url,
                    image_filename=image_filename,
                    topic_id=topic_id,
                    platform=platform,
                    metadata=platform_metadata,
                )
                
                results[platform] = {
                    "success": True,
                    "scheduled": True,
                    "scheduled_post": serialize_scheduled_post(scheduled)
                }
                
                scheduled_any = True
        else:
            # Post immediately to each selected platform
            for platform in platform_list:
                try:
                    if platform == "instagram":
                        # Upload image for Instagram posting
                        image_url = ImageUploadService.get_public_url(image_path)
                        if not image_url:
                            raise Exception("Failed to upload image to public service")
                        agent = InstagramAgent()
                        result = agent.post_to_instagram(image_url, post_content)
                    elif platform == "facebook":
                        agent = FacebookAgent()
                        result = agent.post_to_facebook(post_content, image_path=image_path)
                    elif platform == "linkedin":
                        agent = LinkedInAgent()
                        result = agent.post_to_linkedin(post_content, image_path=image_path)
                    elif platform == "twitter":
                        agent = TwitterAgent()
                        result = agent.post_to_twitter(post_content, image_path=image_path)
                    else:
                        result = {"success": False, "error": f"Unsupported platform: {platform}"}
                    
                    results[platform] = result
                except Exception as e:
                    print(f"[error] Error posting to {platform}: {e}")
                    results[platform] = {"success": False, "error": str(e)}

        # Return results for each platform
        return JSONResponse(content={
            "success": True,
            "results": results,
            "scheduled_any": scheduled_any,
            "platforms_attempted": platform_list
        })

    except HTTPException:
        raise
    except Exception as e:
        print(f"[error] Multi-channel posting error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-and-schedule")
async def generate_and_schedule(
    request: Request,
    topic: str = Form(...),
    schedule_time: str = Form(...),
    timezone: str = Form("UTC"),
    platforms: str = Form(...),  # Comma-separated platforms
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Generate an image based on the topic and schedule it to be posted to selected platforms
    """
    try:
        # Parse platforms from comma-separated string
        platform_list = [p.strip().lower() for p in platforms.split(",") if p.strip()]
        
        # Validate platforms
        valid_platforms = {"instagram", "facebook", "linkedin", "twitter", "youtube"}
        invalid_platforms = [p for p in platform_list if p not in valid_platforms]
        if invalid_platforms:
            raise HTTPException(status_code=400, detail=f"Invalid platforms: {invalid_platforms}")
        
        # Parse the schedule time
        schedule_dt, tz_name = scheduling_service.parse_scheduled_datetime(schedule_time, timezone)
        
        # Create a new topic in the database
        new_topic = Topic(
            user_id=current_user.id,
            topic_title=topic,
            textual_description=topic,
            status="scheduled",
            scheduled_date=schedule_dt
        )
        db.add(new_topic)
        db.commit()
        db.refresh(new_topic)
        
        # For this route, we want to schedule image generation to happen at the scheduled time
        # So we don't generate the image now, but set up the system to generate it when the time comes
        # We'll create scheduled posts without image_filename, and the scheduling service will handle
        # image generation when the time comes
        
        # Create caption based on the topic
        caption = f"Check out this post about: {topic}"
        
        # Schedule the post for each selected platform - without image_filename
        scheduled_posts = []
        for platform in platform_list:
            # Schedule the post using the scheduling service
            metadata = {
                "platform": platform,
                "original_topic": topic,
                "automation": True,
                "source": "generate_at_schedule_time"
            }
            
            scheduled_post = scheduling_service.schedule_post(
                db=db,
                user_id=current_user.id,
                caption=caption,
                schedule_time=schedule_dt,
                timezone_name=tz_name,
                image_filename=None,  # No image filename yet - will be generated at schedule time
                topic_id=new_topic.id,
                platform=platform,
                metadata=metadata
            )
            
            scheduled_posts.append(scheduled_post)
        
        return JSONResponse(content={
            "success": True,
            "message": f"Image generation and posting scheduled successfully for {', '.join(platform_list)}",
            "scheduled_posts": [serialize_scheduled_post(post) for post in scheduled_posts],
            "topic_id": new_topic.id
        })
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[error] Generate and schedule error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/schedule-automation")
async def schedule_automation(
    request: Request,
    topic: str = Form(...),
    schedule_time: str = Form(...),
    timezone: str = Form("UTC"),
    platforms: str = Form(...),  # Comma-separated platforms
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Schedule automated image generation and posting to multiple platforms
    """
    try:
        # Parse platforms from comma-separated string
        platform_list = [p.strip().lower() for p in platforms.split(",") if p.strip()]
        
        # Validate platforms
        valid_platforms = {"instagram", "facebook", "linkedin", "twitter", "youtube"}
        invalid_platforms = [p for p in platform_list if p not in valid_platforms]
        if invalid_platforms:
            raise HTTPException(status_code=400, detail=f"Invalid platforms: {invalid_platforms}")
        
        # Parse the schedule time
        schedule_dt, tz_name = scheduling_service.parse_scheduled_datetime(schedule_time, timezone)
        
        # Create a new topic in the database
        new_topic = Topic(
            user_id=current_user.id,
            topic_title=topic,
            textual_description=topic,
            status="scheduled",
            scheduled_date=schedule_dt
        )
        db.add(new_topic)
        db.commit()
        db.refresh(new_topic)
        
        # Generate the image based on the topic using the AdGenerationService
        ad_service = AdGenerationService()
        
        # Check if AdGenerationService has generate_ad_image method, otherwise use generate_advertisement
        if hasattr(ad_service, 'generate_ad_image'):
            generated_image_path = ad_service.generate_ad_image(
                topic=topic,
                user_email=current_user.email
            )
        else:
            # Use generate_advertisement method instead
            result = ad_service.generate_advertisement(topic, "", "")
            if result.get('success') and result.get('final_image_path'):
                generated_image_path = result['final_image_path']
            else:
                raise HTTPException(status_code=500, detail=f"Failed to generate image: {result.get('error', 'Unknown error')}")
        
        # Check if image generation was successful
        if not generated_image_path or not os.path.exists(generated_image_path):
            raise HTTPException(status_code=500, detail="Failed to generate image for the topic")
        
        # Extract just the filename from the full path
        image_filename = os.path.basename(generated_image_path)
        
        # Create caption based on the topic
        caption = f"New post about: {topic}"
        
        # Schedule the post for each selected platform
        scheduled_posts = []
        for platform in platform_list:
            # For the first platform, use the generated image
            # Schedule the post using the scheduling service
            metadata = {
                "platform": platform,
                "original_topic": topic,
                "automation": True
            }
            
            scheduled_post = scheduling_service.schedule_post(
                db=db,
                user_id=current_user.id,
                caption=caption,
                schedule_time=schedule_dt,
                timezone_name=tz_name,
                image_filename=image_filename,
                topic_id=new_topic.id,
                platform=platform,
                metadata=metadata
            )
            
            scheduled_posts.append(scheduled_post)
        
        return JSONResponse(content={
            "success": True,
            "message": f"Automation scheduled successfully for {', '.join(platform_list)}",
            "scheduled_posts": [serialize_scheduled_post(post) for post in scheduled_posts],
            "topic_id": new_topic.id
        })
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[error] Automation scheduling error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/auto-generate-and-post")
async def auto_generate_and_post(
    request: Request,
    topic: str = Form(...),
    schedule_time: str = Form(...),
    timezone: str = Form("UTC"),
    platforms: str = Form(...),  # Comma-separated platforms
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Generate an image based on the topic and schedule it to be posted to selected platforms
    """
    try:
        # Parse platforms from comma-separated string
        platform_list = [p.strip().lower() for p in platforms.split(",") if p.strip()]
        
        # Validate platforms
        valid_platforms = {"instagram", "facebook", "linkedin", "twitter", "youtube"}
        invalid_platforms = [p for p in platform_list if p not in valid_platforms]
        if invalid_platforms:
            raise HTTPException(status_code=400, detail=f"Invalid platforms: {invalid_platforms}")
        
        # Parse the schedule time
        schedule_dt, tz_name = scheduling_service.parse_scheduled_datetime(schedule_time, timezone)
        
        # Generate the image based on the topic using the AdGenerationService
        ad_service = AdGenerationService()
        
        # Use generate_advertisement method to generate the image
        result = ad_service.generate_advertisement(topic, "", "")
        if not result.get('success') or not result.get('final_image_path'):
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to generate image: {result.get('error', 'Unknown error during image generation')}"
            )
        
        # Extract image path and filename
        generated_image_path = result['final_image_path']
        if not os.path.exists(generated_image_path):
            raise HTTPException(status_code=500, detail="Generated image file does not exist")
        
        image_filename = os.path.basename(generated_image_path)
        
        # Create a new topic in the database
        new_topic = Topic(
            user_id=current_user.id,
            topic_title=topic,
            textual_description=topic,
            status="scheduled",
            scheduled_date=schedule_dt
        )
        db.add(new_topic)
        db.commit()
        db.refresh(new_topic)
        
        # Create caption based on the topic
        caption = f"Check out this post about: {topic}"
        
        # Schedule the post for each selected platform
        scheduled_posts = []
        for platform in platform_list:
            metadata = {
                "platform": platform,
                "original_topic": topic,
                "automation": True,
                "source": "auto_generate_and_post"
            }
            
            scheduled_post = scheduling_service.schedule_post(
                db=db,
                user_id=current_user.id,
                caption=caption,
                schedule_time=schedule_dt,
                timezone_name=tz_name,
                image_filename=image_filename,
                topic_id=new_topic.id,
                platform=platform,
                metadata=metadata
            )
            
            scheduled_posts.append(scheduled_post)
        
        return JSONResponse(content={
            "success": True,
            "message": f"Image generated and scheduled successfully for {', '.join(platform_list)}",
            "scheduled_posts": [serialize_scheduled_post(post) for post in scheduled_posts],
            "topic_id": new_topic.id,
            "image_filename": image_filename
        })
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[error] Auto-generate and post error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "2.0.0"}

if __name__ == "__main__":
    # Get port from environment variable for Render compatibility
    port = int(os.environ.get("PORT", 8000))
    print(f"[startup] Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)

