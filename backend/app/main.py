from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

# Basic FastAPI app for foundation testing
app = FastAPI(
    title="Bubble Platform API",
    version="1.0.0",
    description="AI-Native Investment Strategy Automation Platform - Foundation Test"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "Bubble Platform API - Foundation Test",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            "api": "running",
            "environment": os.getenv("ENVIRONMENT", "development")
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)