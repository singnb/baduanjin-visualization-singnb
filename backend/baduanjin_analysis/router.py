from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any
import json
import os
from datetime import datetime

# Import from parent directory
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from auth.router import get_current_user
import models

router = APIRouter(prefix="/api/baduanjin", tags=["baduanjin_analysis"])

# Base directory for storing analysis data
BASE_ANALYSIS_DIR = "baduanjin_analysis"

# Ensure the base directory exists
os.makedirs(BASE_ANALYSIS_DIR, exist_ok=True)

def get_user_analysis_dir(user_id: int) -> str:
    """Get the directory path for a user's analysis data"""
    user_dir = os.path.join(BASE_ANALYSIS_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

@router.get("/analysis/{analysis_type}")
async def get_analysis_data(
    analysis_type: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get analysis data for a specific type (jointAngles, smoothness, symmetry, balance)"""
    try:
        user_dir = get_user_analysis_dir(current_user.id)
        file_path = os.path.join(user_dir, f"{analysis_type}.json")
        
        if not os.path.exists(file_path):
            # Return empty data structure if file doesn't exist
            return get_empty_analysis_data(analysis_type)
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving analysis data: {str(e)}"
        )

@router.post("/analysis/{analysis_type}")
async def save_analysis_data(
    analysis_type: str,
    data: Dict[str, Any],
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save analysis data for a specific type"""
    try:
        user_dir = get_user_analysis_dir(current_user.id)
        file_path = os.path.join(user_dir, f"{analysis_type}.json")
        
        # Add timestamp to the data
        data['timestamp'] = datetime.utcnow().isoformat()
        
        with open(file_path, 'w') as f:
            json.dump(data, f)
        
        return {"message": f"{analysis_type} data saved successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving analysis data: {str(e)}"
        )

@router.get("/recommendations")
async def get_recommendations(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recommendations for the current user"""
    try:
        user_dir = get_user_analysis_dir(current_user.id)
        file_path = os.path.join(user_dir, "recommendations.json")
        
        if not os.path.exists(file_path):
            return {
                "overall": "No recommendations available yet. Complete your first exercise session to receive personalized feedback.",
                "jointAngles": "No data available",
                "smoothness": "No data available",
                "symmetry": "No data available",
                "balance": "No data available"
            }
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving recommendations: {str(e)}"
        )

def get_empty_analysis_data(analysis_type: str) -> Dict[str, Any]:
    """Return empty data structure for a specific analysis type"""
    empty_data = {
        'jointAngles': {
            'time': [],
            'kneeAngle': [],
            'elbowAngle': [],
            'shoulderAngle': []
        },
        'smoothness': {
            'time': [],
            'jerk': [],
            'acceleration': []
        },
        'symmetry': {
            'poses': [],
            'leftSide': [],
            'rightSide': []
        },
        'balance': {
            'time': [],
            'centerOfMassX': [],
            'centerOfMassY': []
        }
    }
    return empty_data.get(analysis_type, {}) 