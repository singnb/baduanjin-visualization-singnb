# routers/relationships.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import or_, and_

import os
from pathlib import Path
from datetime import datetime
import models, database
from auth.router import get_current_user
from config import settings

router = APIRouter(prefix="/api/relationships", tags=["relationships"])

# NEW ENDPOINT: Get all masters in the system
@router.get("/masters")
async def get_available_masters(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """Get all available masters in the system"""
    # Verify current user is a learner
    if current_user.role != models.UserRole.LEARNER:
        raise HTTPException(status_code=403, detail="Only learners can view masters")
    
    # Query all users with master role
    masters = db.query(models.User).filter(
        models.User.role == models.UserRole.MASTER,
        models.User.is_active == True
    ).all()
    
    # Format response
    result = []
    for master in masters:
        # Count followers
        followers_count = db.query(models.MasterLearnerRelationship).filter(
            models.MasterLearnerRelationship.master_id == master.id,
            models.MasterLearnerRelationship.status == "accepted"
        ).count()
        
        # Count videos
        videos_count = db.query(models.VideoUpload).filter(
            models.VideoUpload.user_id == master.id
        ).count()
        
        # Get profile if it exists
        profile = None
        if hasattr(master, 'profile') and master.profile:
            profile = {
                "bio": master.profile.bio,
                "experience_level": master.profile.experience_level
            }
        
        result.append({
            "id": master.id,
            "name": master.name,
            "username": master.username,
            "email": master.email,
            "followers_count": followers_count,
            "videos_count": videos_count,
            "profile": profile
        })
    
    return result

# NEW ENDPOINT: Get details for a specific master
@router.get("/masters/{master_id}")
async def get_master_details(
    master_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """Get details for a specific master"""
    # Verify the master exists
    master = db.query(models.User).filter(
        models.User.id == master_id,
        models.User.role == models.UserRole.MASTER,
        models.User.is_active == True
    ).first()
    
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")
    
    # Count followers
    followers_count = db.query(models.MasterLearnerRelationship).filter(
        models.MasterLearnerRelationship.master_id == master.id,
        models.MasterLearnerRelationship.status == "accepted"
    ).count()
    
    # Count videos
    videos_count = db.query(models.VideoUpload).filter(
        models.VideoUpload.user_id == master.id
    ).count()
    
    # Get profile if it exists
    profile = None
    if hasattr(master, 'profile') and master.profile:
        profile = {
            "bio": master.profile.bio,
            "experience_level": master.profile.experience_level
        }
    
    # Get master's videos
    videos = db.query(models.VideoUpload).filter(
        models.VideoUpload.user_id == master.id
    ).order_by(models.VideoUpload.upload_timestamp.desc()).limit(5).all()
    
    video_list = [{
        "id": video.id,
        "title": video.title,
        "description": video.description,
        "brocade_type": video.brocade_type,
        "upload_timestamp": video.upload_timestamp
    } for video in videos]
    
    # Check if the current user follows this master
    is_following = db.query(models.MasterLearnerRelationship).filter(
        models.MasterLearnerRelationship.master_id == master.id,
        models.MasterLearnerRelationship.learner_id == current_user.id,
        models.MasterLearnerRelationship.status == "accepted"
    ).first() is not None
    
    return {
        "id": master.id,
        "name": master.name,
        "username": master.username,
        "email": master.email,
        "followers_count": followers_count,
        "videos_count": videos_count,
        "profile": profile,
        "recent_videos": video_list,
        "is_following": is_following,
        "expertise": profile.get("experience_level") if profile else "Baduanjin Master"
    }

# NEW ENDPOINT: Check relationship status with a master
@router.get("/status/{master_id}")
async def check_relationship_status(
    master_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """Check if the current user follows this master"""
    # Verify the master exists
    master = db.query(models.User).filter(
        models.User.id == master_id,
        models.User.role == models.UserRole.MASTER
    ).first()
    
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")
    
    # Check relationship status
    relationship = db.query(models.MasterLearnerRelationship).filter(
        models.MasterLearnerRelationship.master_id == master_id,
        models.MasterLearnerRelationship.learner_id == current_user.id
    ).first()
    
    if not relationship:
        return {
            "is_following": False,
            "status": None
        }
    
    return {
        "is_following": relationship.status == "accepted",
        "status": relationship.status
    }

# NEW ENDPOINT: Get the master that a learner is following
@router.get("/followed-master")
async def get_followed_master(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """Get the master that the current user follows"""
    # Verify current user is a learner
    if current_user.role != models.UserRole.MASTER:
        raise HTTPException(status_code=403, detail="Only learners can follow masters")
    
    # Get the master this learner follows
    relationship = db.query(models.MasterLearnerRelationship).filter(
        models.MasterLearnerRelationship.learner_id == current_user.id,
        models.MasterLearnerRelationship.status == "accepted"
    ).first()
    
    if not relationship:
        return {"master": None}
    
    # Get master details
    master = db.query(models.User).filter(
        models.User.id == relationship.master_id
    ).first()
    
    if not master:
        return {"master": None}
    
    # Get profile if it exists
    profile = None
    if hasattr(master, 'profile') and master.profile:
        profile = {
            "bio": master.profile.bio,
            "experience_level": master.profile.experience_level
        }
    
    return {
        "master": {
            "id": master.id,
            "name": master.name,
            "username": master.username,
            "email": master.email,
            "expertise": profile.get("experience_level") if profile else "Baduanjin Master"
        }
    }

# NEW ENDPOINT: Follow a master (direct)
@router.post("/follow/{master_id}")
async def follow_master(
    master_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """Follow a master (learner initiated)"""
    # Verify current user is a learner
    if current_user.role != models.UserRole.LEARNER:
        raise HTTPException(status_code=403, detail="Only learners can follow masters")
    
    # Verify the master exists
    master = db.query(models.User).filter(
        models.User.id == master_id,
        models.User.role == models.UserRole.MASTER
    ).first()
    
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")
    
    # Check if relationship already exists
    relationship = db.query(models.MasterLearnerRelationship).filter(
        models.MasterLearnerRelationship.master_id == master_id,
        models.MasterLearnerRelationship.learner_id == current_user.id
    ).first()
    
    if relationship:
        # Update existing relationship
        relationship.status = "accepted"
    else:
        # Create new relationship
        relationship = models.MasterLearnerRelationship(
            master_id=master_id,
            learner_id=current_user.id,
            status="accepted"
        )
        db.add(relationship)
    
    db.commit()
    db.refresh(relationship)
    
    return {
        "id": relationship.id,
        "master_id": relationship.master_id,
        "learner_id": relationship.learner_id,
        "status": relationship.status,
        "message": "You are now following this master"
    }

# NEW ENDPOINT: Unfollow a master
@router.post("/unfollow/{master_id}")
async def unfollow_master(
    master_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """Unfollow a master"""
    # Verify current user is a learner
    if current_user.role != models.UserRole.LEARNER:
        raise HTTPException(status_code=403, detail="Only learners can unfollow masters")
    
    # Find the relationship
    relationship = db.query(models.MasterLearnerRelationship).filter(
        models.MasterLearnerRelationship.master_id == master_id,
        models.MasterLearnerRelationship.learner_id == current_user.id
    ).first()
    
    if not relationship:
        raise HTTPException(status_code=404, detail="You are not following this master")
    
    # Delete the relationship
    db.delete(relationship)
    db.commit()
    
    return {
        "message": "You have unfollowed this master"
    }

# EXISTING ENDPOINTS BELOW

@router.post("/request/{learner_id}")
async def request_master_learner_relationship(
    learner_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    # Verify current user is a master
    if current_user.role != models.UserRole.MASTER:
        raise HTTPException(status_code=403, detail="Only masters can send relationship requests")
    
    # Check if learner exists
    learner = db.query(models.User).filter(
        models.User.id == learner_id,
        models.User.role == models.UserRole.LEARNER
    ).first()
    
    if not learner:
        raise HTTPException(status_code=404, detail="Learner not found")
    
    # Check if relationship already exists
    existing = db.query(models.MasterLearnerRelationship).filter(
        models.MasterLearnerRelationship.master_id == current_user.id,
        models.MasterLearnerRelationship.learner_id == learner_id
    ).first()
    
    if existing:
        return {
            "id": existing.id,
            "master_id": existing.master_id,
            "learner_id": existing.learner_id,
            "status": existing.status,
            "message": "Relationship request already exists"
        }
    
    # Create new relationship
    relationship = models.MasterLearnerRelationship(
        master_id=current_user.id,
        learner_id=learner_id,
        status="pending"
    )
    
    db.add(relationship)
    db.commit()
    db.refresh(relationship)
    
    return {
        "id": relationship.id,
        "master_id": relationship.master_id,
        "learner_id": relationship.learner_id,
        "status": relationship.status,
        "message": "Relationship request sent successfully"
    }

@router.post("/{relationship_id}/respond")
async def respond_to_relationship_request(
    relationship_id: int,
    status: str = Query(..., regex="^(accepted|rejected)$"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    # Verify current user is a learner
    if current_user.role != models.UserRole.LEARNER:
        raise HTTPException(status_code=403, detail="Only learners can respond to relationship requests")
    
    # Check if relationship exists and belongs to current user
    relationship = db.query(models.MasterLearnerRelationship).filter(
        models.MasterLearnerRelationship.id == relationship_id,
        models.MasterLearnerRelationship.learner_id == current_user.id,
        models.MasterLearnerRelationship.status == "pending"
    ).first()
    
    if not relationship:
        raise HTTPException(status_code=404, detail="Relationship request not found")
    
    # Update relationship status
    relationship.status = status
    db.commit()
    
    return {
        "id": relationship.id,
        "master_id": relationship.master_id,
        "learner_id": relationship.learner_id,
        "status": relationship.status,
        "message": f"Relationship request {status} successfully"
    }

@router.get("/my-requests")
async def get_my_relationship_requests(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    # Different queries based on user role
    if current_user.role == models.UserRole.MASTER:
        # Get relationships where user is the master
        relationships = db.query(models.MasterLearnerRelationship).filter(
            models.MasterLearnerRelationship.master_id == current_user.id
        ).all()
    else:
        # Get relationships where user is the learner
        relationships = db.query(models.MasterLearnerRelationship).filter(
            models.MasterLearnerRelationship.learner_id == current_user.id
        ).all()
    
    # Get related user information
    result = []
    for rel in relationships:
        if current_user.role == models.UserRole.MASTER:
            related_user = db.query(models.User).filter(models.User.id == rel.learner_id).first()
            related_role = "learner"
        else:
            related_user = db.query(models.User).filter(models.User.id == rel.master_id).first()
            related_role = "master"
        
        result.append({
            "id": rel.id,
            "status": rel.status,
            "created_at": rel.created_at,
            "related_user": {
                "id": related_user.id,
                "username": related_user.username,
                "name": related_user.name,
                "role": related_role
            }
        })
    
    return result

@router.get("/learners")
async def get_master_learners(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    # Verify current user is a master
    if current_user.role != models.UserRole.MASTER:
        raise HTTPException(status_code=403, detail="Only masters can view their learners")
    
    # Get accepted relationships
    relationships = db.query(models.MasterLearnerRelationship).filter(
        models.MasterLearnerRelationship.master_id == current_user.id,
        models.MasterLearnerRelationship.status == "accepted"
    ).all()
    
    # Get learner information
    result = []
    for rel in relationships:
        learner = db.query(models.User).filter(models.User.id == rel.learner_id).first()
        
        if learner:
            result.append({
                "relationship_id": rel.id,
                "learner_id": learner.id,
                "username": learner.username,
                "name": learner.name,
                "email": learner.email
            })
    
    return result

# Endpoints from Learner to Master's account
@router.get("/master-videos/{master_id}/analyzed")
async def get_master_analyzed_videos(
    master_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """Get only analyzed videos from a master that have extracted JSON files"""
    
    # Verify the master exists
    master = db.query(models.User).filter(
        models.User.id == master_id,
        models.User.role == models.UserRole.MASTER,
        models.User.is_active == True
    ).first()
    
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")
    
    # Get videos that are completed
    videos = db.query(models.VideoUpload).filter(
        models.VideoUpload.user_id == master_id,
        models.VideoUpload.processing_status == "completed"
    ).order_by(models.VideoUpload.upload_timestamp.desc()).all()
    
    analyzed_videos = []
    
    for video in videos:
        try:
            # Construct paths to check for analysis results
            video_uuid = getattr(video, 'video_uuid', None)
            
            # Create the base path for outputs
            base_path = Path("outputs_json") / str(master_id) / str(video.id)
            
            # Check for analysis directory
            analysis_dir = base_path / "baduanjin_analysis"
            
            # Check for JSON results file - handle different possible naming conventions
            json_exists = False
            if video_uuid:
                json_path = base_path / f"results_{video_uuid}.json"
                json_exists = json_path.exists()
            
            # Alternative: check for any results JSON file in the directory
            if not json_exists and base_path.exists():
                json_files = list(base_path.glob("results_*.json"))
                json_exists = len(json_files) > 0
            
            # Check if analysis report exists
            analysis_exists = False
            if analysis_dir.exists():
                report_path = analysis_dir / "analysis_report.txt"
                analysis_exists = report_path.exists()
            
            # Include video if it has either JSON results or analysis
            if json_exists or analysis_exists:
                video_data = {
                    "id": video.id,
                    "title": video.title,
                    "description": video.description or "",
                    "brocade_type": getattr(video, 'brocade_type', None),
                    "processing_status": video.processing_status,
                    "upload_timestamp": video.upload_timestamp.isoformat() if video.upload_timestamp else None,
                    "has_json": json_exists,
                    "has_analysis": analysis_exists
                }
                
                # Add uuid if available
                if video_uuid:
                    video_data["uuid"] = video_uuid
                
                analyzed_videos.append(video_data)
                
        except Exception as e:
            print(f"Error processing video {video.id}: {str(e)}")
            # Continue with next video instead of failing entirely
            continue
    
    return analyzed_videos

# Endpoints for the Master's to learner accounts
@router.get("/learner-details/{learner_id}")
async def get_learner_details(
    learner_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """Get detailed information about a specific learner"""
    
    # Verify current user is a master
    if current_user.role != models.UserRole.MASTER:
        raise HTTPException(status_code=403, detail="Only masters can view learner details")
    
    # Verify the learner follows this master
    relationship = db.query(models.MasterLearnerRelationship).filter(
        models.MasterLearnerRelationship.master_id == current_user.id,
        models.MasterLearnerRelationship.learner_id == learner_id,
        models.MasterLearnerRelationship.status == "accepted"
    ).first()
    
    if not relationship:
        raise HTTPException(status_code=404, detail="Learner not found or doesn't follow you")
    
    # Get learner information
    learner = db.query(models.User).filter(
        models.User.id == learner_id
    ).first()
    
    if not learner:
        raise HTTPException(status_code=404, detail="Learner not found")
    
    # Count videos
    videos_count = db.query(models.VideoUpload).filter(
        models.VideoUpload.user_id == learner_id,
        models.VideoUpload.processing_status == "completed"
    ).count()
    
    # Get last active timestamp (last video upload)
    last_video = db.query(models.VideoUpload).filter(
        models.VideoUpload.user_id == learner_id
    ).order_by(models.VideoUpload.upload_timestamp.desc()).first()
    
    return {
        "learner_id": learner.id,
        "name": learner.name,
        "username": learner.username,
        "email": learner.email,
        "videos_count": videos_count,
        "last_active": last_video.upload_timestamp if last_video else None,
        "created_at": relationship.created_at
    }

@router.get("/learner-videos/{learner_id}/analyzed")
async def get_learner_analyzed_videos(
    learner_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """Get analyzed videos from a learner that are ready for comparison"""
    
    # Verify current user is a master
    if current_user.role != models.UserRole.MASTER:
        raise HTTPException(status_code=403, detail="Only masters can view learner videos")
    
    # Verify the learner follows this master
    relationship = db.query(models.MasterLearnerRelationship).filter(
        models.MasterLearnerRelationship.master_id == current_user.id,
        models.MasterLearnerRelationship.learner_id == learner_id,
        models.MasterLearnerRelationship.status == "accepted"
    ).first()
    
    if not relationship:
        raise HTTPException(status_code=404, detail="Learner not found or doesn't follow you")
    
    # Get videos that are completed and have analysis results
    videos = db.query(models.VideoUpload).filter(
        models.VideoUpload.user_id == learner_id,
        models.VideoUpload.processing_status == "completed"
    ).order_by(models.VideoUpload.upload_timestamp.desc()).all()
    
    analyzed_videos = []
    
    for video in videos:
        try:
            # Check for analysis results
            video_uuid = getattr(video, 'video_uuid', None)
            base_path = Path("outputs_json") / str(learner_id) / str(video.id)
            
            # Check for analysis directory and JSON files
            analysis_dir = base_path / "baduanjin_analysis"
            json_exists = False
            
            if video_uuid:
                json_path = base_path / f"results_{video_uuid}.json"
                json_exists = json_path.exists()
            
            if not json_exists and base_path.exists():
                json_files = list(base_path.glob("results_*.json"))
                json_exists = len(json_files) > 0
            
            # Check if analysis report exists
            analysis_exists = False
            if analysis_dir.exists():
                report_path = analysis_dir / "analysis_report.txt"
                analysis_exists = report_path.exists()
            
            # Include video if it has either JSON results or analysis
            if json_exists or analysis_exists:
                video_data = {
                    "id": video.id,
                    "title": video.title,
                    "description": video.description or "",
                    "brocade_type": getattr(video, 'brocade_type', None),
                    "processing_status": video.processing_status,
                    "upload_timestamp": video.upload_timestamp.isoformat() if video.upload_timestamp else None,
                    "has_json": json_exists,
                    "has_analysis": analysis_exists
                }
                
                if video_uuid:
                    video_data["uuid"] = video_uuid
                
                analyzed_videos.append(video_data)
                
        except Exception as e:
            print(f"Error processing video {video.id}: {str(e)}")
            continue
    
    return analyzed_videos

@router.get("/master-followers/{master_id}")
async def get_master_followers(
    master_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """Get followers of a specific master"""
    
    # Only the master themselves can see their followers
    if current_user.id != master_id or current_user.role != models.UserRole.MASTER:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get all accepted relationships
    relationships = db.query(models.MasterLearnerRelationship).filter(
        models.MasterLearnerRelationship.master_id == master_id,
        models.MasterLearnerRelationship.status == "accepted"
    ).order_by(models.MasterLearnerRelationship.created_at.desc()).all()
    
    followers = []
    for rel in relationships:
        learner = db.query(models.User).filter(
            models.User.id == rel.learner_id
        ).first()
        
        if learner:
            # Get additional stats
            videos_count = db.query(models.VideoUpload).filter(
                models.VideoUpload.user_id == learner.id
            ).count()
            
            last_video = db.query(models.VideoUpload).filter(
                models.VideoUpload.user_id == learner.id
            ).order_by(models.VideoUpload.upload_timestamp.desc()).first()
            
            followers.append({
                "learner_id": learner.id,
                "name": learner.name,
                "username": learner.username,
                "email": learner.email,
                "videos_count": videos_count,
                "last_active": last_video.upload_timestamp if last_video else None,
                "following_since": rel.created_at
            })
    
    return followers

@router.get("/debug/relationship/{master_id}/{learner_id}")
async def debug_relationship(
    master_id: int,
    learner_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """Debug endpoint to check relationship status"""
    
    relationship = db.query(models.MasterLearnerRelationship).filter(
        models.MasterLearnerRelationship.master_id == master_id,
        models.MasterLearnerRelationship.learner_id == learner_id
    ).first()
    
    if relationship:
        return {
            "relationship_exists": True,
            "status": relationship.status,
            "master_id": relationship.master_id,
            "learner_id": relationship.learner_id,
            "created_at": relationship.created_at
        }
    else:
        return {
            "relationship_exists": False,
            "master_id": master_id,
            "learner_id": learner_id
        }

@router.get("/debug/video/{video_id}")
async def debug_video_ownership(
    video_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """Debug endpoint to check video ownership"""
    
    video = db.query(models.VideoUpload).filter(
        models.VideoUpload.id == video_id
    ).first()
    
    if video:
        video_owner = db.query(models.User).filter(
            models.User.id == video.user_id
        ).first()
        
        return {
            "video_exists": True,
            "video_id": video.id,
            "owner_id": video.user_id,
            "owner_name": video_owner.name if video_owner else "Unknown",
            "owner_role": video_owner.role if video_owner else "Unknown",
            "current_user_id": current_user.id,
            "current_user_role": current_user.role
        }
    else:
        return {
            "video_exists": False,
            "video_id": video_id
        }