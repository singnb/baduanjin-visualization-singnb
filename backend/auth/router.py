# type: ignore
# auth/router.py
# FastAPI Backend Authentication Endpoints

from datetime import datetime, timedelta
from typing import Optional, List
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, Body 
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Import from parent directory
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
import models  
from models import UserRole
from config import settings

# JWT Configuration
SECRET_KEY = "your-secret-key-for-jwt-tokens-make-it-long-and-random"  # Store in environment variables in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token schemes
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

router = APIRouter(prefix="/api/auth", tags=["authentication"])

# Pydantic models for request/response validation
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: dict

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None

class UserRole(str, Enum):
    MASTER = "master"
    LEARNER = "learner"

class UserCreate(BaseModel):
    email: str  
    username: str
    password: str
    name: str
    role: UserRole = UserRole.LEARNER  

class UserLogin(BaseModel):
    email: str
    password: str

class RefreshToken(BaseModel):
    refresh_token: str

class UserAgreement(BaseModel):
    agreement_accepted: bool

# Helper functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Get user by email from database
def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

# Get user by username
def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

# Authenticate user
def authenticate_user(db: Session, email: str, password: str):
    # Try to find user by email first
    user = get_user_by_email(db, email)
    
    # If not found by email, check if email is actually a username
    if not user:
        user = get_user_by_username(db, email)
        
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

# Get current user from token
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        user_id = payload.get("user_id")
        
        if email is None or user_id is None:
            raise credentials_exception
        
        token_data = TokenData(email=email, user_id=user_id)
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.id == token_data.user_id).first()
    if user is None:
        raise credentials_exception
    
    return user

# Routes
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    try:
        # Check if email already exists
        db_user = get_user_by_email(db, user_data.email)
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check if username already exists
        db_user = get_user_by_username(db, user_data.username)
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        # Validate role
        if user_data.role not in ["master", "learner"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role must be either 'master' or 'learner'"
            )
        
        # Create new user
        hashed_password = get_password_hash(user_data.password)
        new_user = models.User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password,
            name=user_data.name,
            role=UserRole.MASTER if user_data.role == "master" else UserRole.LEARNER
        )
                
        # Create empty profile for the user
        new_profile = models.UserProfile(user=new_user)
        
        db.add(new_user)
        db.add(new_profile)
        db.commit()
        db.refresh(new_user)
        
        return {
            "message": "User created successfully", 
            "user_id": new_user.id,
            "username": new_user.username,
            "role": new_user.role.value
        }
    except Exception as e:
        # Log the exception for debugging
        print(f"Register error: {str(e)}")
        raise

@router.post("/login", response_model=Token)
async def login_for_access_token(user_data: UserLogin, db: Session = Depends(get_db)):
    try:
        user = authenticate_user(db, user_data.email, user_data.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if user has accepted agreement
        if not getattr(user, 'agreement_accepted', True):  # Default to True for backward compatibility
            # Return a special status that frontend can recognize
            return {
                "access_token": "",
                "refresh_token": "",
                "token_type": "bearer",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "username": user.username,
                    "role": user.role.value,
                    "agreement_required": True
                }
            }
        
        # Create access and refresh tokens
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email, "user_id": user.id},
            expires_delta=access_token_expires
        )
        
        refresh_token = create_refresh_token(
            data={"sub": user.email, "user_id": user.id}
        )
        
        # Return tokens and user info
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "username": getattr(user, 'username', user.email.split('@')[0]),  # Fallback for backward compatibility
                "role": getattr(user, 'role', 'learner')  # Default to learner for backward compatibility
            }
        }
    except Exception as e:
        # Log the exception for debugging
        print(f"Login error: {str(e)}")
        raise

@router.post("/agreement")
async def accept_agreement(
    agreement: UserAgreement,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not agreement.agreement_accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agreement must be accepted to continue"
        )
    
    # Update user agreement status
    current_user.agreement_accepted = True
    current_user.agreement_timestamp = datetime.utcnow()
    db.commit()
    
    return {"message": "User agreement accepted successfully"}

@router.post("/agreement/accept-initial")
async def accept_initial_agreement(
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    # Extract data from request
    user_id = data.get("user_id")
    email = data.get("email")
    password = data.get("password")
    agreement_accepted = data.get("agreement_accepted", False)
    
    if not agreement_accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agreement must be accepted to continue"
        )
    
    # Find the user
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify credentials
    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password"
        )
    
    # Update user agreement status
    user.agreement_accepted = True
    user.agreement_timestamp = datetime.utcnow()
    db.commit()
    
    # Create tokens
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={"sub": user.email, "user_id": user.id}
    )
    
    # Return tokens and user info
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "username": getattr(user, 'username', user.email.split('@')[0]),
            "role": getattr(user, 'role', 'learner')
        }
    }

@router.get("/me")
async def get_current_user_info(current_user: models.User = Depends(get_current_user)):
    # Get profile if it exists
    profile = None
    if hasattr(current_user, 'profile') and current_user.profile:
        profile = {
            "bio": current_user.profile.bio,
            "experience_level": current_user.profile.experience_level
        }
    
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "username": getattr(current_user, 'username', current_user.email.split('@')[0]),
        "role": getattr(current_user, 'role', 'learner'),
        "agreement_accepted": getattr(current_user, 'agreement_accepted', True),
        "profile": profile
    }

@router.post("/refresh-token")
async def refresh_access_token(refresh_token_data: RefreshToken, db: Session = Depends(get_db)):
    try:
        # Decode refresh token
        payload = jwt.decode(refresh_token_data.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        user_id = payload.get("user_id")
        
        if email is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
        
        # Find user
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        
        # Create new access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email, "user_id": user.id},
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
