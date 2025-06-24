# SQLAlchemy models (models.py) for database interactions
# models.py 

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from sqlalchemy import Enum as SQLAlchemyEnum
import json
from sqlalchemy.dialects.postgresql import JSONB  # Add this import for JSONB support

from database import Base
from datetime import datetime

# Change the enum to inherit from str so it properly converts to strings
class UserRole(str, enum.Enum):
    MASTER = "master"
    LEARNER = "learner"

# Make BrocadeType inherit from str for proper serialization
class BrocadeType(str, enum.Enum):
    FIRST = "FIRST"
    SECOND = "SECOND"
    THIRD = "THIRD"
    FOURTH = "FOURTH"
    FIFTH = "FIFTH"
    SIXTH = "SIXTH"
    SEVENTH = "SEVENTH"
    EIGHTH = "EIGHTH"
    LIVE_SESSION = "LIVE_SESSION" 

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    name = Column(String)
    hashed_password = Column(String)
    role = Column(SQLAlchemyEnum(UserRole), default=UserRole.LEARNER)
    is_active = Column(Boolean, default=True)
    agreement_accepted = Column(Boolean, default=False)
    agreement_timestamp = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    videos = relationship("VideoUpload", back_populates="user")

class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    bio = Column(Text, nullable=True)
    experience_level = Column(String, nullable=True)
    preferences = Column(Text, nullable=True)  # JSON string for user preferences
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="profile")

class VideoUpload(Base):
    __tablename__ = "video_uploads"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    description = Column(String, nullable=True)
    brocade_type = Column(String)
    video_path = Column(String)
    upload_timestamp = Column(DateTime, default=datetime.utcnow)
    processing_status = Column(String, default="uploaded")
    analyzed_video_path = Column(String, nullable=True)
    keypoints_path = Column(String, nullable=True)
    english_audio_path = Column(String, nullable=True)
    analysis_report_path = Column(String, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="videos")
    analysis_results = relationship("AnalysisResult", back_populates="video", uselist=False)
    keypoints = relationship("KeypointData", back_populates="video", cascade="all, delete-orphan")

class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("video_uploads.id"), unique=True)
    joint_angle_data = Column(Text)  # JSON string
    balance_data = Column(Text)  # JSON string
    smoothness_data = Column(Text)  # JSON string
    symmetry_data = Column(Text)  # JSON string
    recommendations = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    video = relationship("VideoUpload", back_populates="analysis_results")
    
    # Helper methods for JSON serialization/deserialization
    def get_joint_angle_data(self):
        if self.joint_angle_data:
            return json.loads(self.joint_angle_data)
        return {}
        
    def get_balance_data(self):
        if self.balance_data:
            return json.loads(self.balance_data)
        return {}
        
    def get_smoothness_data(self):
        if self.smoothness_data:
            return json.loads(self.smoothness_data)
        return {}
        
    def get_symmetry_data(self):
        if self.symmetry_data:
            return json.loads(self.symmetry_data)
        return {}
        
    def get_recommendations(self):
        if self.recommendations:
            return json.loads(self.recommendations)
        return {}
    
    def set_joint_angle_data(self, data):
        self.joint_angle_data = json.dumps(data)
        
    def set_balance_data(self, data):
        self.balance_data = json.dumps(data)
        
    def set_smoothness_data(self, data):
        self.smoothness_data = json.dumps(data)
        
    def set_symmetry_data(self, data):
        self.symmetry_data = json.dumps(data)
        
    def set_recommendations(self, data):
        self.recommendations = json.dumps(data)

class MasterLearnerRelationship(Base):
    __tablename__ = "master_learner_relationships"
    
    id = Column(Integer, primary_key=True, index=True)
    master_id = Column(Integer, ForeignKey("users.id"))
    learner_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String, default="pending")  # pending, accepted, rejected
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    master = relationship("User", foreign_keys=[master_id])
    learner = relationship("User", foreign_keys=[learner_id])

# New class for storing frame-by-frame keypoint data
class KeypointData(Base):
    __tablename__ = "keypoint_data"
    
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("video_uploads.id", ondelete="CASCADE"))
    frame_number = Column(Integer)
    keypoints = Column(JSONB)  # PostgreSQL's binary JSON format for efficient storage
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    video = relationship("VideoUpload", back_populates="keypoints")