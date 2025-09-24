from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, Float, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
import os

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./adgen.db')

# Configure SQLite properly for concurrent access
if DATABASE_URL.startswith('sqlite'):
    engine = create_engine(
        DATABASE_URL, 
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    auth_provider = Column(String, default="email")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    schedules = relationship("Schedule", back_populates="user")
    topics = relationship("Topic", back_populates="user")
    scheduled_posts = relationship("ScheduledPost", back_populates="user")

class Schedule(Base):
    __tablename__ = "schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    cron_expression = Column(String)
    scheduled_datetime = Column(DateTime(timezone=True))
    timezone = Column(String, default="UTC")
    status = Column(String, default="active")  # active, paused, completed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="schedules")
    topics = relationship("Topic", back_populates="schedule")

class Topic(Base):
    __tablename__ = "topics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    schedule_id = Column(Integer, ForeignKey("schedules.id"), nullable=True)
    
    # Content
    topic_title = Column(String, nullable=False)
    textual_description = Column(Text)
    brand_context = Column(Text)
    target_accounts = Column(Text)
    image_constraints = Column(Text)
    
    # Scheduling
    scheduled_date = Column(DateTime(timezone=True))
    
    # Status tracking
    status = Column(String, default="pending")  # pending, processing, completed, failed
    retries = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="topics")
    schedule = relationship("Schedule", back_populates="topics")
    scheduled_posts = relationship("ScheduledPost", back_populates="topic")
    prompts = relationship("Prompt", back_populates="topic")
    images = relationship("Image", back_populates="topic")

class Prompt(Base):
    __tablename__ = "prompts"
    
    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    
    # Prompt details
    model = Column(String, default="gemini-2.5-flash")
    prompt_text = Column(Text, nullable=False)
    negative_prompt = Column(Text)
    style = Column(String)
    parameters = Column(JSON)  # Store additional parameters
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    topic = relationship("Topic", back_populates="prompts")
    images = relationship("Image", back_populates="prompt")

class Image(Base):
    __tablename__ = "images"
    
    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    prompt_id = Column(Integer, ForeignKey("prompts.id"), nullable=True)
    
    # Image details
    url = Column(String)
    local_path = Column(String)
    version = Column(Integer, default=1)
    status = Column(String, default="generated")  # generated, reviewed, approved, rejected
    
    # Generation metadata
    provider = Column(String)  # ideogram, dalle, etc.
    request_id = Column(String)
    generation_parameters = Column(JSON)
    
    # Quality metrics
    width = Column(Integer)
    height = Column(Integer)
    file_size = Column(Integer)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    topic = relationship("Topic", back_populates="images")
    prompt = relationship("Prompt", back_populates="images")
    reviews = relationship("ImageReview", back_populates="image")

class ImageReview(Base):
    __tablename__ = "image_reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(Integer, ForeignKey("images.id"), nullable=False)
    
    # Review details
    reviewer = Column(String, default="gemini-vision")
    
    # Scores (0-10)
    semantic_match_score = Column(Float)
    visual_quality_score = Column(Float)
    text_readability_score = Column(Float)
    brand_suitability_score = Column(Float)
    technical_quality_score = Column(Float)
    safety_score = Column(Float)
    overall_score = Column(Float)
    
    # Decision
    decision = Column(String)  # APPROVE, EDIT, REGENERATE
    is_postable = Column(Boolean, default=False)
    
    # Feedback
    issues_found = Column(JSON)
    recommendations = Column(JSON)
    edit_instructions = Column(Text)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    image = relationship("Image", back_populates="reviews")

class ScheduledPost(Base):
    __tablename__ = "scheduled_posts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    workflow_id = Column(String)
    image_url = Column(String)
    image_filename = Column(String)
    job_metadata = Column("metadata", JSON)  # Use column mapping to avoid reserved keyword
    caption = Column(Text, nullable=False)
    schedule_time = Column(DateTime(timezone=True), nullable=False)
    scheduled_for = Column(DateTime(timezone=True))  # Alternative column name from actual DB
    timezone = Column(String, default="UTC")
    status = Column(String, default="pending")  # pending, processing, completed, failed, retry, cancelled
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    last_error = Column(Text)
    error_message = Column(Text)  # Alternative column name from actual DB
    last_error_details = Column(JSON)
    last_attempt_at = Column(DateTime(timezone=True))
    next_attempt_after = Column(DateTime(timezone=True))
    posted_at = Column(DateTime(timezone=True))
    result_payload = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="scheduled_posts")
    topic = relationship("Topic", back_populates="scheduled_posts")


class PostRecord(Base):
    __tablename__ = "post_records"
    
    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    image_id = Column(Integer, ForeignKey("images.id"), nullable=False)
    
    # Instagram posting details
    instagram_media_id = Column(String)
    instagram_container_id = Column(String)
    caption_used = Column(Text)
    
    # Status
    posted_at = Column(DateTime(timezone=True))
    status = Column(String)  # posted, failed, pending
    error_message = Column(Text)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Create tables
def create_tables():
    Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
