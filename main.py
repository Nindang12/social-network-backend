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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Log environment variables (excluding sensitive data)
logger.info(f"CORS_ORIGINS: {os.getenv('CORS_ORIGINS')}")
logger.info(f"MongoDB URL configured: {'Yes' if os.getenv('MONGODB_URL') else 'No'}")
logger.info(f"Secret key configured: {'Yes' if os.getenv('SECRET_KEY') else 'No'}")

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
logger.info(f"Configured CORS origins: {CORS_ORIGINS}")

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

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    logger.info("Root endpoint called")
    return {"message": "API is running"}

@app.post("/signup")
def signup(user: User):
    print(user)
    if (Manager.check_user_exists(phone_number=user.phone_number, email=user.email, username=user.username)):
        raise HTTPException(status_code=400, detail="User already exists")
    Manager.create_user(user)
    return {"message": "User signed up", "user": user}

# ... rest of your API endpoints ... 