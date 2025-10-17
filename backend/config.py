"""
Configuration file for the Agents Marketplace backend
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY","")


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
    "agent_requirements": DATA_DIR / "agent_requirements.csv"
}

# Database configuration
DATABASE_CONFIG = {
    # PostgreSQL settings
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "agents_marketplace"),
    "username": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "password"),
    
    # Connection pool settings
    "min_connections": 1,
    "max_connections": 10,
    
    # Data source preference (csv or postgres)
    "data_source": os.getenv("DATA_SOURCE", "csv")  # "csv" or "postgres"
}

# API settings
API_CONFIG = {
    "title": "Agents Marketplace API",
    "version": "1.0.0",
    "description": "API for managing AI agents marketplace",
    "host": os.getenv("API_HOST", "0.0.0.0"),
    "port": int(os.getenv("API_PORT", "8000"))
}
