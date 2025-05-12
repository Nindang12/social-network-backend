from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# CORS configuration
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "FastAPI is running",
        "environment": {
            "CORS_ORIGINS": origins,
            "PORT": os.getenv("PORT", "Not set"),
            "MONGODB_URL": "Configured" if os.getenv("MONGODB_URL") else "Not configured"
        }
    } 