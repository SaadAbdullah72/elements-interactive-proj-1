# profile.py
# User profile management endpoints (view/update/delete).
#
# This module depends on authentication helpers from `auth.py` and
# exposes endpoints to manage profile data, change passwords, and
# store/retrieve AI analysis history. Sensitive operations (password
# change, account deletion) require the authenticated `get_current_user`.
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, validator
from pymongo import MongoClient
from datetime import datetime
from typing import Optional, List, Dict, Any
import hashlib
import re
import os
from dotenv import load_dotenv

from auth import get_current_user, hash_password, verify_password

load_dotenv()

router = APIRouter(prefix="/api/profile", tags=["Profile"])

# -------------------------
# MongoDB Setup
# -------------------------
mongodburl = os.getenv('MONGODB_URL', os.getenv('LOCAL_MONGODB_URL', 'mongodb://localhost:27017/'))
auth_db_name = os.getenv('MONGODB_AUTH_DB', 'authentication')
client = MongoClient(mongodburl)
db = client[auth_db_name]
users_collection = db["users"]

# -------------------------
# Pydantic Models
# -------------------------
class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    age: Optional[int] = Field(None, ge=1, le=120)
    gender: Optional[str] = None
    medical_history: Optional[str] = None

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        return v

class AnalysisRecord(BaseModel):
    id: str
    date: str
    disease: str
    medication: str
    final_decision: str
    risk_level: str

class MessageResponse(BaseModel):
    message: str

# -------------------------
# API Endpoints
# -------------------------
@router.get("/me", response_model=Dict[str, Any])
async def get_full_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get complete user profile including analysis history.
    """
    user = users_collection.find_one({"email": current_user["email"]})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prepare profile response
    profile = {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "age": user.get("age"),
        "gender": user.get("gender"),
        "medical_history": user.get("medical_history", ""),
        "email_verified": user.get("email_verified", False),
        "created_at": user.get("created_at", ""),
        "analyses": user.get("analyses", [])
    }
    
    return profile

@router.put("/update", response_model=MessageResponse)
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update user profile information.
    
    - **name**: Full name (optional)
    - **age**: Age (optional)
    - **gender**: Gender (optional)
    - **medical_history**: Medical history (optional)
    """
    update_fields = {}
    
    if profile_data.name is not None:
        update_fields["name"] = profile_data.name
    if profile_data.age is not None:
        update_fields["age"] = profile_data.age
    if profile_data.gender is not None:
        update_fields["gender"] = profile_data.gender
    if profile_data.medical_history is not None:
        update_fields["medical_history"] = profile_data.medical_history
    
    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    # Update user in database
    users_collection.update_one(
        {"email": current_user["email"]},
        {"$set": update_fields}
    )
    
    return {"message": "Profile updated successfully"}

@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Change user password.
    
    - **current_password**: Current password for verification
    - **new_password**: New password (must meet security requirements)
    """
    # Get user from database
    user = users_collection.find_one({"email": current_user["email"]})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify current password
    if not verify_password(password_data.current_password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    users_collection.update_one(
        {"email": current_user["email"]},
        {"$set": {"password_hash": hash_password(password_data.new_password)}}
    )
    
    return {"message": "Password changed successfully"}

@router.get("/analyses", response_model=List[Dict[str, Any]])
async def get_user_analyses(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get all past AI medical analyses for the user.
    """
    user = users_collection.find_one({"email": current_user["email"]})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    analyses = user.get("analyses", [])
    
    # Sort by date (newest first)
    analyses.sort(key=lambda x: x.get("date", ""), reverse=True)
    
    return analyses

@router.post("/analyses", response_model=MessageResponse)
async def save_analysis(
    analysis_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Save an AI medical analysis to user's history.
    
    This endpoint is called internally by the prescription checker.
    """
    # Validate required fields
    required_fields = ["date", "disease", "medication", "final_decision", "risk_level"]
    for field in required_fields:
        if field not in analysis_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required field: {field}"
            )
    
    # Add analysis to user's history
    users_collection.update_one(
        {"email": current_user["email"]},
        {
            "$push": {
                "analyses": {
                    "id": analysis_data.get("id", str(datetime.utcnow().timestamp())),
                    "date": analysis_data["date"],
                    "disease": analysis_data["disease"],
                    "medication": analysis_data["medication"],
                    "final_decision": analysis_data["final_decision"],
                    "risk_level": analysis_data["risk_level"],
                    "verification_status": analysis_data.get("verification_status"),
                    "reactions": analysis_data.get("reactions", []),
                    "explanation": analysis_data.get("explanation", "")
                }
            }
        }
    )
    
    return {"message": "Analysis saved successfully"}

@router.delete("/analyses/{analysis_id}", response_model=MessageResponse)
async def delete_analysis(
    analysis_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Delete a specific analysis from user's history.
    """
    # Remove analysis from user's history
    result = users_collection.update_one(
        {"email": current_user["email"]},
        {"$pull": {"analyses": {"id": analysis_id}}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )
    
    return {"message": "Analysis deleted successfully"}

@router.delete("/account", response_model=MessageResponse)
async def delete_account(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Delete user account permanently.
    
    WARNING: This action cannot be undone.
    """
    # Delete user from database
    result = users_collection.delete_one({"email": current_user["email"]})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "Account deleted successfully"}