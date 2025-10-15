"""
Production startup script for Render deployment
"""
import uvicorn
from main import app

if __name__ == "__main__":
    print("🚀 Starting Agents Marketplace API Server (Production Mode)...")
    print("📍 Server will be available at: https://your-app.onrender.com")
    print("📚 API Documentation: https://your-app.onrender.com/docs")
    print("🌐 Agents Listing: https://your-app.onrender.com/agents")
    print("🔄 Health Check: https://your-app.onrender.com/api/health")
    print("-" * 60)
    
    # Production configuration for Render
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        workers=1,  # Single worker for free tier
        log_level="info"
    )
