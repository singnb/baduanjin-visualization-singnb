
# Pydantic models (schemas.py) for API request/response validation
# schemas.py

from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

# User schemas
class UserBase(BaseModel):
    email: str
    username: str
    name: str
    role: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(UserBase):
    id: int
    agreement_accepted: bool
    created_at: datetime
    
    class Config:
        orm_mode = True

# Video schemas
class VideoBase(BaseModel):
    title: str
    description: Optional[str] = None
    brocade_type: str

class VideoUploadResponse(VideoBase):
    id: int
    processing_status: str
    upload_timestamp: datetime
    
    class Config:
        orm_mode = True

# Analysis schemas
class AnalysisData(BaseModel):
    # This can hold any JSON data
    pass

class AnalysisResponse(BaseModel):
    joint_angle_data: Optional[Dict[str, Any]] = {}
    balance_data: Optional[Dict[str, Any]] = {}
    smoothness_data: Optional[Dict[str, Any]] = {}
    symmetry_data: Optional[Dict[str, Any]] = {}
    recommendations: Optional[Dict[str, str]] = {}
    
    class Config:
        orm_mode = True

# Token schema
class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class TokenData(BaseModel):
    id: Optional[int] = None
    email: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None