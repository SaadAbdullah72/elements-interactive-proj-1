# auth.py
# Authentication subsystem for users (patients and doctors).
#
# Contains Pydantic models for signup/login, helpers for password hashing
# and JWT token creation. This module is intentionally opinionated about
# validation rules (password complexity) — these can be made configurable.
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field, validator
from pymongo import MongoClient
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import os
import jwt
import secrets
import hashlib
import re

from email_service import send_verification_email, send_registration_email

load_dotenv()

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# -------------------------
# MongoDB Setup
# -------------------------
mongodburl = os.getenv('MONGODB_URL', os.getenv('LOCAL_MONGODB_URL', 'mongodb://localhost:27017/'))
db_name = os.getenv('MONGODB_LOCAL_DB', 'local_data')
client = MongoClient(mongodburl)
db = client[db_name]
users_collection = db["users"]

# -------------------------
# JWT Configuration
# -------------------------
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "1440"))

# -------------------------
# Security Dependencies
# -------------------------
security = HTTPBearer(auto_error=False)

# -------------------------
# Pydantic Models
# -------------------------
class UserSignup(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Full Name")
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    age: Optional[int] = Field(None, ge=1, le=120, description="Age")
    gender: Optional[str] = Field(None, description="Gender")
    medical_history: Optional[str] = Field("", description="Medical History")
    role: str = Field(default="patient", description="User role: patient or doctor")

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        return v

class DoctorSignup(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Full Name")
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    specialization: str = Field(..., min_length=2, max_length=100, description="Medical Specialization")
    license_number: str = Field(..., min_length=2, max_length=50, description="Medical License Number")
    hospital: Optional[str] = Field(None, description="Hospital/Clinic Name")

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    age: Optional[int]
    gender: Optional[str]
    medical_history: Optional[str]
    email_verified: bool
    created_at: str
    role: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class MessageResponse(BaseModel):
    message: str

# -------------------------
# Helper Functions
# -------------------------
# NOTE: `hash_password` currently uses SHA-256 for simplicity. For
# production deployments, migrate to `bcrypt` or `argon2` (use passlib
# or bcrypt library) to store salted hashes and resist brute-force.
#+ Keep the helper API stable so other modules can switch implementation
# with minimal changes.
def hash_password(password: str) -> str:
    """Hash password using SHA-256 (use bcrypt in production)"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return hash_password(password) == hashed_password

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def generate_verification_token() -> str:
    """Generate secure verification token"""
    return secrets.token_urlsafe(32)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current authenticated user from JWT token"""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = users_collection.find_one({"email": email})
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user["id"] = str(user["_id"])
        del user["_id"]
        del user["password_hash"]
        del user["verification_token"]
        
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

# -------------------------
# API Endpoints
# -------------------------
@router.post("/signup", response_model=MessageResponse)
async def signup(user_data: UserSignup):
    """
    Register a new user account.

    - **name**: Full name of the patient
    - **email**: Email address (will be used for verification)
    - **password**: Password (min 8 chars, must include uppercase, lowercase, and number)
    - **age**: Optional age
    - **gender**: Optional gender
    - **medical_history**: Optional medical history
    """
    # Check if user already exists with same email
    existing_user = users_collection.find_one({"email": user_data.email.lower()})
    if existing_user:
        # If email exists but name is different, tell them to use different email
        if existing_user.get("name", "").lower() != user_data.name.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email already exists under a different name. Please use a different email address."
            )
        # Same email and same name - already exists
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists"
        )
    
    # Check if another user with same name but different email exists (prevent name spoofing)
    existing_name = users_collection.find_one({
        "name": {"$regex": f"^{user_data.name}$", "$options": "i"},
        "email": {"$ne": user_data.email.lower()}
    })
    if existing_name and existing_name.get("role") == "patient":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this name already exists. Please sign in with your registered email or use a different name."
        )
    
    # Generate verification token
    verification_token = generate_verification_token()
    
    # Create user document
    user_document = {
        "name": user_data.name,
        "email": user_data.email.lower(),
        "password_hash": hash_password(user_data.password),
        "age": user_data.age,
        "gender": user_data.gender,
        "medical_history": user_data.medical_history or "",
        "email_verified": False,
        "verification_token": verification_token,
        "role": user_data.role,
        "created_at": datetime.utcnow().isoformat(),
        "analyses": []  # Store past AI medical analyses
    }
    
    # Insert user into database
    result = users_collection.insert_one(user_document)
    user_id = str(result.inserted_id)
    
    # Send verification email
    verification_url = f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/verify-email?token={verification_token}"
    
    try:
        await send_verification_email(
            email=user_data.email,
            name=user_data.name,
            verification_url=verification_url
        )
    except Exception as e:
        # Log error but don't fail signup
        print(f"Failed to send verification email: {str(e)}")
    
    # Send registration email
    try:
        send_registration_email(
            patient_email=user_data.email,
            patient_name=user_data.name,
            user_id=user_id,
            role=user_data.role
        )
    except Exception as e:
        # Log error but don't fail signup
        print(f"Failed to send registration email: {str(e)}")
    
    return {"message": "Verification email has been sent to your email address. Please check your inbox and verify your account."}

@router.post("/doctor-signup", response_model=MessageResponse)
async def doctor_signup(doctor_data: DoctorSignup):
    """
    Register a new doctor account.
    
    - **name**: Full name of the doctor
    - **email**: Email address (will be used for verification)
    - **password**: Password (min 8 chars, must include uppercase, lowercase, and number)
    - **specialization**: Medical specialization
    - **license_number**: Medical license number
    - **hospital**: Optional hospital/clinic name
    """
    # Check if user already exists
    existing_user = users_collection.find_one({"email": doctor_data.email.lower()})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists"
        )
    
    # Generate verification token
    verification_token = generate_verification_token()
    
    # Create doctor document
    doctor_document = {
        "name": doctor_data.name,
        "email": doctor_data.email.lower(),
        "password_hash": hash_password(doctor_data.password),
        "specialization": doctor_data.specialization,
        "license_number": doctor_data.license_number,
        "hospital": doctor_data.hospital or "",
        "email_verified": False,
        "verification_token": verification_token,
        "role": "doctor",
        "created_at": datetime.utcnow().isoformat(),
        "managed_patients": []  # List of patient IDs managed by this doctor
    }
    
    # Insert doctor into database
    result = users_collection.insert_one(doctor_document)
    doctor_id = str(result.inserted_id)
    
    # Send verification email
    verification_url = f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/verify-email?token={verification_token}"
    
    try:
        await send_verification_email(
            email=doctor_data.email,
            name=doctor_data.name,
            verification_url=verification_url
        )
    except Exception as e:
        # Log error but don't fail signup
        print(f"Failed to send verification email: {str(e)}")
    
    # Send doctor welcome email
    try:
        send_registration_email(
            patient_email=doctor_data.email,
            patient_name=doctor_data.name,
            user_id=doctor_id,
            role="doctor",
            specialization=doctor_data.specialization
        )
    except Exception as e:
        # Log error but don't fail signup
        print(f"Failed to send welcome email: {str(e)}")
    
    return {"message": "Verification email has been sent to your email address. Please check your inbox and verify your account."}

@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin):
    """
    Login with email and password.
    
    Returns JWT token for authenticated requests.
    """
    # Find user by email
    user = users_collection.find_one({"email": login_data.email.lower()})
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(login_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user["email"]})
    
    # Prepare user response
    user_response = UserResponse(
        id=str(user["_id"]),
        name=user["name"],
        email=user["email"],
        age=user.get("age"),
        gender=user.get("gender"),
        medical_history=user.get("medical_history"),
        email_verified=user.get("email_verified", False),
        created_at=user.get("created_at", ""),
        role=user.get("role", "patient")
    )
    
    response = TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )
    
    return response

@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(token: str):
    """
    Verify user email using the token from the verification email.
    """
    # Find user by verification token
    user = users_collection.find_one({"verification_token": token})
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    # Update user as verified
    users_collection.update_one(
        {"_id": user["_id"]},
        {
            "$set": {"email_verified": True},
            "$unset": {"verification_token": ""}
        }
    )
    
    return {"message": "Your account has been successfully verified. You can now access your medical dashboard."}

@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(email: EmailStr):
    """
    Resend verification email to unverified users.
    """
    user = users_collection.find_one({"email": email.lower()})
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email"
        )
    
    if user.get("email_verified", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already verified"
        )
    
    # Generate new verification token
    verification_token = generate_verification_token()
    users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"verification_token": verification_token}}
    )
    
    # Send verification email
    verification_url = f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/verify-email?token={verification_token}"
    
    try:
        await send_verification_email(
            email=user["email"],
            name=user["name"],
            verification_url=verification_url
        )
    except Exception as e:
        print(f"Failed to send verification email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email"
        )
    
    return {"message": "Verification email has been resent. Please check your inbox."}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get current authenticated user information.
    """
    return UserResponse(**current_user)

@router.post("/logout")
async def logout():
    """
    Logout (client should remove the token).
    """
    return {"message": "Successfully logged out"}