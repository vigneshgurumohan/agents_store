"""
S3 utility functions for file uploads
"""
import boto3
import os
import uuid
from datetime import datetime
from typing import Optional, Tuple
from botocore.exceptions import ClientError
import logging
from config import S3_CONFIG, FILE_UPLOAD_CONFIG

logger = logging.getLogger(__name__)

class S3FileManager:
    def __init__(self):
        """Initialize S3 client"""
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=S3_CONFIG['access_key_id'],
                aws_secret_access_key=S3_CONFIG['secret_access_key'],
                region_name=S3_CONFIG['region']
            )
            self.bucket_name = S3_CONFIG['bucket_name']
            logger.info("S3 client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {str(e)}")
            self.s3_client = None

    def generate_file_path(self, folder_type: str, original_filename: str, user_id: str = None) -> str:
        """Generate a structured file path for S3 upload"""
        # Get file extension
        file_ext = os.path.splitext(original_filename)[1].lower()
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{timestamp}_{unique_id}{file_ext}"
        
        # Get folder path
        folder_path = FILE_UPLOAD_CONFIG['upload_folders'].get(folder_type, 'uploads/')
        
        # Add user ID if provided for organization
        if user_id:
            file_path = f"{folder_path}{user_id}/{filename}"
        else:
            file_path = f"{folder_path}{filename}"
        
        return file_path

    def validate_file(self, file_content: bytes, filename: str) -> Tuple[bool, str]:
        """Validate file size and extension"""
        # Check file size
        if len(file_content) > FILE_UPLOAD_CONFIG['max_file_size']:
            return False, f"File size exceeds maximum allowed size of {FILE_UPLOAD_CONFIG['max_file_size']} bytes"
        
        # Check file extension
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in FILE_UPLOAD_CONFIG['allowed_extensions']:
            return False, f"File type {file_ext} is not allowed. Allowed types: {FILE_UPLOAD_CONFIG['allowed_extensions']}"
        
        return True, "Valid"

    def upload_file(self, file_content: bytes, filename: str, folder_type: str, user_id: str = None) -> Tuple[bool, str, str]:
        """
        Upload file to S3
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            folder_type: Type of folder (mou, profile_images, etc.)
            user_id: User ID for organizing files
        
        Returns:
            Tuple of (success, message, s3_url)
        """
        if not self.s3_client:
            return False, "S3 client not initialized", ""
        
        try:
            # Validate file
            is_valid, validation_msg = self.validate_file(file_content, filename)
            if not is_valid:
                return False, validation_msg, ""
            
            # Generate S3 file path
            s3_key = self.generate_file_path(folder_type, filename, user_id)
            
            # Upload to S3 (without ACL since bucket doesn't support it)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=self.get_content_type(filename)
            )
            
            # Generate S3 URL
            s3_url = f"https://{self.bucket_name}.s3.{S3_CONFIG['region']}.amazonaws.com/{s3_key}"
            
            logger.info(f"File uploaded successfully: {s3_url}")
            return True, "File uploaded successfully", s3_url
            
        except ClientError as e:
            error_msg = f"S3 upload error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, ""
        except Exception as e:
            error_msg = f"Upload error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, ""

    def delete_file(self, s3_url: str) -> Tuple[bool, str]:
        """Delete file from S3"""
        if not self.s3_client:
            return False, "S3 client not initialized"
        
        try:
            # Extract S3 key from URL
            s3_key = s3_url.split(f"{self.bucket_name}.s3.{S3_CONFIG['region']}.amazonaws.com/")[-1]
            
            # Delete from S3
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            
            logger.info(f"File deleted successfully: {s3_key}")
            return True, "File deleted successfully"
            
        except ClientError as e:
            error_msg = f"S3 delete error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Delete error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def get_content_type(self, filename: str) -> str:
        """Get content type based on file extension"""
        content_types = {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.txt': 'text/plain',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg'
        }
        
        file_ext = os.path.splitext(filename)[1].lower()
        return content_types.get(file_ext, 'application/octet-stream')

    def generate_signed_url(self, s3_url: str, expiration: int = 3600) -> str:
        """
        Generate a signed URL for accessing a private S3 object
        
        Args:
            s3_url: The S3 URL of the file
            expiration: Time in seconds for the URL to remain valid (default: 1 hour)
        
        Returns:
            Signed URL that allows temporary access to the file
        """
        if not self.s3_client:
            return s3_url  # Return original URL if S3 client not available
        
        try:
            # Extract S3 key from URL
            s3_key = s3_url.split(f"{self.bucket_name}.s3.{S3_CONFIG['region']}.amazonaws.com/")[-1]
            
            # Generate signed URL
            signed_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            
            logger.info(f"Generated signed URL for {s3_key}")
            return signed_url
            
        except Exception as e:
            logger.error(f"Error generating signed URL: {str(e)}")
            return s3_url  # Return original URL if signing fails

# Global S3 file manager instance
s3_manager = S3FileManager()
