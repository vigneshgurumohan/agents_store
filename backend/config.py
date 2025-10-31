"""
Configuration file for the Agents Marketplace backend
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Log API key status for debugging
import logging
logger = logging.getLogger(__name__)
logger.info(f"Config: OpenAI API Key loaded: {'Yes' if OPENAI_API_KEY else 'No'}")
if OPENAI_API_KEY:
    logger.info(f"Config: API Key length: {len(OPENAI_API_KEY)} characters")
    logger.info(f"Config: API Key prefix: {OPENAI_API_KEY[:10]}..." if len(OPENAI_API_KEY) > 10 else "Config: API Key too short")


# Base directory paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

# CSV file paths
CSV_PATHS = {
    "agents": DATA_DIR / "agents.csv",
    "auth": DATA_DIR / "auth.csv",
    "capabilities_mapping": DATA_DIR / "capabilities_mapping.csv",
    "demo_assets": DATA_DIR / "demo_assets.csv", 
    "deployments": DATA_DIR / "deployments.csv",
    "docs": DATA_DIR / "docs.csv",
    "isv": DATA_DIR / "isv.csv",
    "reseller": DATA_DIR / "reseller.csv",
    "client": DATA_DIR / "client.csv",
    "agent_requirements": DATA_DIR / "agent_requirements.csv",
    "chat_history": DATA_DIR / "chat_history.csv",
    "enquiries": DATA_DIR / "enquiries.csv"
}

# Database configuration
DATABASE_CONFIG = {
    # PostgreSQL connection URL (preferred - takes precedence over individual parameters)
    "DATABASE_URL": os.getenv("DATABASE_URL"),  # Format: postgresql://user:pass@host:port/dbname
    # PostgreSQL settings (used if DATABASE_URL is not provided)
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "database": os.getenv("DB_NAME"),
    "username": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    
    # Connection pool settings
    "min_connections": 1,
    "max_connections": 10,
    
    # Data source preference (csv or postgres)
    "data_source": os.getenv("DATA_SOURCE", "postgres")  # "csv" or "postgres"
}

# API settings
API_CONFIG = {
    "title": "Agents Marketplace API",
    "version": "1.0.0",
    "description": "API for managing AI agents marketplace",
    "host": os.getenv("API_HOST", "0.0.0.0"),
    "port": int(os.getenv("API_PORT", "8000"))
}


# S3 Configuration
S3_CONFIG = {
    "bucket_name": os.getenv("S3_BUCKET_NAME", ""),
    "region": os.getenv("S3_REGION", ""),
    "access_key_id": os.getenv("AWS_ACCESS_KEY_ID", ""),
    "secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY", "")
}


# File upload settings
FILE_UPLOAD_CONFIG = {
    "max_file_size": 50 * 1024 * 1024,  # 50MB (increased for demo assets)
    "allowed_extensions": [".pdf", ".doc", ".docx", ".txt", ".md", ".png", ".jpg", ".jpeg", ".gif", ".mp4", ".avi", ".mov"],
    "upload_folders": {
        "mou": "documents/mou/",
        "profile_images": "images/profile/",
        "agent_docs": "documents/agents/",
        "demo_assets": "assets/demo/",
        "deployments": "assets/deployments/"
    }
}