# config/storage.py
# Storage Configuration for Local and Azure Blob Storage

import os
from pathlib import Path
from typing import Optional
import aiofiles
from datetime import datetime

class StorageConfig:
    """Storage configuration for video files"""
    
    # Local storage paths
    LOCAL_UPLOAD_DIR = Path("uploads/recordings")
    LOCAL_TEMP_DIR = Path("uploads/temp")
    LOCAL_PROCESSED_DIR = Path("uploads/processed")
    
    # Azure Blob Storage (if using)
    AZURE_STORAGE_CONNECTION_STRING = os.getenv("DefaultEndpointsProtocol=https;AccountName=baduanjintesting;AccountKey=ubh2Ykb+hizqr4PCqm3bVMsNW2SRbTIwIvj6DfB+qPBTD6WUcwnB0qB9GbsKon/dxWLIW80kX+py+AStsHKHlg==;EndpointSuffix=core.windows.net")
    # AZURE_CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME", "baduanjin-videos")
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://dbadmin:NYPBedok1234!@baduanjin-db-testing.postgres.database.azure.com:5432/postgres")
    
    # Storage mode
    STORAGE_MODE = os.getenv("STORAGE_MODE", "local")  # "local" or "azure"
    
    # File size limits (in bytes)
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
    MAX_TOTAL_SIZE = 1024 * 1024 * 1024  # 1GB per upload
    
    @classmethod
    def init_directories(cls):
        """Initialize all required directories"""
        for directory in [cls.LOCAL_UPLOAD_DIR, cls.LOCAL_TEMP_DIR, cls.LOCAL_PROCESSED_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"📁 Directory ready: {directory}")

class LocalStorage:
    """Local file storage implementation"""
    
    def __init__(self):
        StorageConfig.init_directories()
    
    async def save_file(self, file_content: bytes, filename: str, subfolder: str = "") -> str:
        """Save file to local storage"""
        if subfolder:
            save_dir = StorageConfig.LOCAL_UPLOAD_DIR / subfolder
            save_dir.mkdir(parents=True, exist_ok=True)
        else:
            save_dir = StorageConfig.LOCAL_UPLOAD_DIR
        
        file_path = save_dir / filename
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content)
        
        return str(file_path)
    
    def get_file_path(self, filename: str, subfolder: str = "") -> Path:
        """Get full path to file"""
        if subfolder:
            return StorageConfig.LOCAL_UPLOAD_DIR / subfolder / filename
        return StorageConfig.LOCAL_UPLOAD_DIR / filename
    
    def file_exists(self, filename: str, subfolder: str = "") -> bool:
        """Check if file exists"""
        return self.get_file_path(filename, subfolder).exists()
    
    def get_file_size(self, filename: str, subfolder: str = "") -> int:
        """Get file size in bytes"""
        file_path = self.get_file_path(filename, subfolder)
        if file_path.exists():
            return file_path.stat().st_size
        return 0
    
    def delete_file(self, filename: str, subfolder: str = "") -> bool:
        """Delete file from storage"""
        try:
            file_path = self.get_file_path(filename, subfolder)
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            print(f"❌ Delete error: {e}")
            return False

class AzureBlobStorage:
    """Azure Blob Storage implementation (optional)"""
    
    def __init__(self):
        if not StorageConfig.AZURE_STORAGE_CONNECTION_STRING:
            raise ValueError("Azure Storage connection string not configured")
        
        try:
            from azure.storage.blob import BlobServiceClient
            self.blob_service = BlobServiceClient.from_connection_string(
                StorageConfig.AZURE_STORAGE_CONNECTION_STRING
            )
            self.container_name = StorageConfig.DATABASE_URL
            self._ensure_container()
        except ImportError:
            raise ImportError("azure-storage-blob package required for Azure storage")
    
    def _ensure_container(self):
        """Ensure container exists"""
        try:
            self.blob_service.create_container(self.container_name)
        except Exception:
            pass  # Container might already exist
    
    async def save_file(self, file_content: bytes, filename: str, subfolder: str = "") -> str:
        """Save file to Azure Blob Storage"""
        blob_name = f"{subfolder}/{filename}" if subfolder else filename
        
        blob_client = self.blob_service.get_blob_client(
            container=self.container_name,
            blob=blob_name
        )
        
        await blob_client.upload_blob(file_content, overwrite=True)
        return blob_name
    
    def get_file_url(self, filename: str, subfolder: str = "") -> str:
        """Get URL to file in Azure storage"""
        blob_name = f"{subfolder}/{filename}" if subfolder else filename
        blob_client = self.blob_service.get_blob_client(
            container=self.container_name,
            blob=blob_name
        )
        return blob_client.url

# Storage factory
def get_storage():
    """Get storage implementation based on configuration"""
    if StorageConfig.STORAGE_MODE == "azure":
        return AzureBlobStorage()
    else:
        return LocalStorage()

# Add to main.py imports and setup
def setup_storage():
    """Initialize storage system"""
    storage_mode = StorageConfig.STORAGE_MODE
    print(f"🗄️  Storage mode: {storage_mode}")
    
    if storage_mode == "local":
        StorageConfig.init_directories()
        print("✅ Local storage initialized")
    elif storage_mode == "azure":
        if not StorageConfig.AZURE_STORAGE_CONNECTION_STRING:
            print("⚠️  Azure storage configured but no connection string found")
            print("🔄 Falling back to local storage")
            StorageConfig.STORAGE_MODE = "local"
            StorageConfig.init_directories()
        else:
            print("✅ Azure storage configured")
    
    return get_storage()

# Updated schemas.py additions
from pydantic import BaseModel
from typing import Dict, Any

class VideoTransferRequest(BaseModel):
    timestamp: str
    title: str
    description: Optional[str] = None
    brocade_type: str = "LIVE_SESSION"

class VideoTransferResponse(BaseModel):
    success: bool
    message: str
    video_id: Optional[int] = None
    transfer_info: Optional[Dict[str, Any]] = None
    local_files: Optional[Dict[str, str]] = None

class DualVideoUploadResponse(BaseModel):
    success: bool
    message: str
    video_id: int
    upload_id: str
    files: Dict[str, Dict[str, Any]]
    timestamp: str

class RecordingListResponse(BaseModel):
    success: bool
    recordings: List[Dict[str, Any]]
    count: int