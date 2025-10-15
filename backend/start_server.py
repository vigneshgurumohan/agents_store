"""
Simple server startup script
"""
import uvicorn
from main import app

if __name__ == "__main__":
    print("🚀 Starting Agents Marketplace API Server...")
    print("📍 Server will be available at: http://localhost:8000")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🌐 Agents Listing: http://localhost:8000/agents")
    print("🔄 Health Check: http://localhost:8000/api/health")
    print("-" * 50)
    
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
