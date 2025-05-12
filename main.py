from fastapi import FastAPI, HTTPException, Depends, Query, Form, File, UploadFile
from typing import List, Optional, Any
from pydantic import BaseModel
from DAO.DAO_manager import DAO_Manager
from auth.jwt_handler import create_access_token
import json
from fastapi.responses import JSONResponse, StreamingResponse
from bson import ObjectId
from datetime import datetime
from auth.dependencies import get_current_user
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import logging
import uvicorn

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI()

# CORS configuration
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000")
# Clean up CORS URL and convert to list
origins = [origin.strip().rstrip("/").rstrip(";") for origin in CORS_ORIGINS.split(",")]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Log configuration
logger.info(f"Configured CORS origins: {origins}")
logger.info(f"MongoDB URL status: {'Configured' if os.getenv('MONGODB_URL') else 'Not configured'}")
logger.info(f"Secret key status: {'Configured' if os.getenv('SECRET_KEY') else 'Not configured'}")

@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "FastAPI is running",
        "config": {
            "cors_origins": origins,
            "mongodb_status": "Configured" if os.getenv("MONGODB_URL") else "Not configured",
            "secret_key_status": "Configured" if os.getenv("SECRET_KEY") else "Not configured"
        }
    }

# ------------------------
# Mock Models and Schemas
# ------------------------
Manager = DAO_Manager()
class User(BaseModel):
    full_name: str
    phone_number: str
    username: str
    email: str
    password: str

class PostCreate(BaseModel):
    user_id: str
    content: str

class Comment(BaseModel):
    post_id: str
    user_id: str
    content: str
    parent_comment_id: Optional[str] = None

class UserUpdate(BaseModel):
    full_name: str
    phone_number: str
    username: str
    email: str
    bio: str

@app.post("/signup")
def signup(user: User):
    print(user)
    if (Manager.check_user_exists(phone_number=user.phone_number, email=user.email, username=user.username)):
        raise HTTPException(status_code=400, detail="User already exists")
    Manager.create_user(user)
    return {"message": "User signed up", "user": user}

# ... rest of your API endpoints ...

# Khởi động server
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port) 