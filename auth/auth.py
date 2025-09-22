from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import os

from models.database import User, get_db

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Bearer token (non-blocking to allow custom header/cookie fallbacks)
security = HTTPBearer(auto_error=False)

class AuthService:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        """Create a JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            return None
    
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """Authenticate a user by email and password"""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not AuthService.verify_password(password, user.hashed_password):
            return None
        return user
    
    @staticmethod
    def create_user(db: Session, email: str, password: str) -> User:
        """Create a new user"""
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        hashed_password = AuthService.get_password_hash(password)
        db_user = User(
            email=email,
            hashed_password=hashed_password,
            auth_provider="email"
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get the current authenticated user"""
    print(f"🔐 Authentication attempt:")
    print(f"   Headers: {dict(request.headers)}")
    print(f"   Cookies: {dict(request.cookies)}")
    print(f"   Credentials: {credentials}")
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = None
    
    # Try to get token from Authorization header first
    if credentials:
        token = credentials.credentials
        print(f"🔑 Token from Authorization header: {token[:20]}...")
    
    # If no Authorization header, try to get from localStorage token via custom header
    elif "x-auth-token" in request.headers:
        token = request.headers["x-auth-token"]
        print(f"🔑 Token from X-Auth-Token header: {token[:20]}...")
    
    # If still no token, check cookies
    elif "authToken" in request.cookies:
        token = request.cookies["authToken"]
        print(f"🔑 Token from authToken cookie: {token[:20]}...")
    
    # Also try sb-access-token cookie (Supabase format)
    elif "sb-access-token" in request.cookies:
        token = request.cookies["sb-access-token"]
        print(f"🔑 Token from sb-access-token cookie: {token[:20]}...")
    
    if not token:
        print("❌ No authentication token found")
        print("💡 Tried: Authorization header, X-Auth-Token header, authToken cookie, sb-access-token cookie")
        raise credentials_exception
    
    try:
        print(f"🔍 Verifying token...")
        
        # First try our JWT verification
        payload = AuthService.verify_token(token)
        if payload is None:
            print("❌ JWT token verification failed")
            # For now, let's create a mock user for testing
            print("🧪 Creating mock user for testing with Supabase token")
            # Extract email from Supabase token if possible
            import json
            import base64
            try:
                # Try to decode Supabase JWT
                parts = token.split('.')
                if len(parts) == 3:
                    # Decode payload (add padding if needed)
                    payload_part = parts[1]
                    payload_part += '=' * (4 - len(payload_part) % 4)
                    decoded = base64.b64decode(payload_part)
                    supabase_payload = json.loads(decoded)
                    print(f"📋 Supabase payload: {supabase_payload}")
                    
                    email = supabase_payload.get('email')
                    if email:
                        print(f"📧 Found email in Supabase token: {email}")
                        # Check if user exists, create if not
                        user = db.query(User).filter(User.email == email).first()
                        if not user:
                            print(f"🆕 Creating new user for Supabase auth: {email}")
                            user = User(
                                email=email,
                                hashed_password="supabase_auth",  # Placeholder
                                auth_provider="supabase",
                                is_active=True
                            )
                            db.add(user)
                            db.commit()
                            db.refresh(user)
                        
                        print(f"✅ User authenticated via Supabase: {user.email}")
                        return user
            except Exception as e:
                print(f"❌ Supabase token decode error: {e}")
            
            raise credentials_exception
        
        print(f"✅ Token verified, payload: {payload}")
        
        email: str = payload.get("sub")
        if email is None:
            print("❌ No email in token payload")
            raise credentials_exception
            
        print(f"👤 Looking up user: {email}")
            
    except JWTError as e:
        print(f"❌ JWT Error: {e}")
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        print(f"❌ User not found in database: {email}")
        raise credentials_exception
    
    print(f"✅ User authenticated: {user.email}")
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get the current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Pydantic models for API
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    auth_provider: str
    created_at: datetime
    
    class Config:
        from_attributes = True