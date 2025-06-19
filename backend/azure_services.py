from azure.storage.blob import BlobServiceClient
from config import settings
import json
import uuid
from datetime import datetime

class AzureBlobService:
    def __init__(self):
        if settings.azure_storage_connection_string:
            self.blob_service_client = BlobServiceClient.from_connection_string(
                settings.azure_storage_connection_string
            )
        else:
            self.blob_service_client = None
            print("Warning: Azure Storage connection string not found")
    
    async def upload_video(self, file_content: bytes, filename: str) -> str:
        """Upload video file to Azure Blob Storage"""
        if not self.blob_service_client:
            raise Exception("Azure Blob Storage not configured")
        
        # Generate unique filename to avoid conflicts
        unique_filename = f"{uuid.uuid4()}_{filename}"
        
        blob_client = self.blob_service_client.get_blob_client(
            container=settings.azure_storage_container_videos,
            blob=unique_filename
        )
        
        blob_client.upload_blob(file_content, overwrite=True)
        return unique_filename
    
    async def upload_result(self, result_data: dict, original_filename: str) -> str:
        """Upload analysis result to Azure Blob Storage"""
        if not self.blob_service_client:
            raise Exception("Azure Blob Storage not configured")
        
        result_filename = f"{original_filename}_result_{uuid.uuid4()}.json"
        
        blob_client = self.blob_service_client.get_blob_client(
            container=settings.azure_storage_container_results,
            blob=result_filename
        )
        
        blob_client.upload_blob(
            json.dumps(result_data, indent=2), 
            overwrite=True
        )
        return result_filename
    
    async def get_video_url(self, filename: str) -> str:
        """Get video URL (for downloading/streaming)"""
        if not self.blob_service_client:
            raise Exception("Azure Blob Storage not configured")
        
        blob_client = self.blob_service_client.get_blob_client(
            container=settings.azure_storage_container_videos,
            blob=filename
        )
        
        return blob_client.url

# Create global instance
azure_blob_service = AzureBlobService()