from pymongo import MongoClient
import gridfs
from bson import ObjectId
import os
from dotenv import load_dotenv

load_dotenv()

class GridFSConfig:
    def __init__(self):
        # Get MongoDB connection string from environment variable
        mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        
        # Create MongoDB client
        self.client = MongoClient(mongo_uri)
        
        # Get database
        self.db = self.client["social_network"]
        
        # Initialize GridFS
        self.fs = gridfs.GridFS(self.db)
        
        # Create collections for metadata
        self.images = self.db["images"]
        self.videos = self.db["videos"]
        self.avatars = self.db["avatars"]

    def upload_file(self, file_data, file_name, content_type, is_image=True):
        try:
            # Store file in GridFS
            file_id = self.fs.put(
                file_data,
                filename=file_name,
                content_type=content_type
            )
            
            # Store metadata
            metadata = {
                "file_id": str(file_id),
                "filename": file_name,
                "content_type": content_type,
                "upload_date": ObjectId(file_id).generation_time
            }
            
            if is_image:
                self.images.insert_one(metadata)
            else:
                self.videos.insert_one(metadata)
                
            return str(file_id)
            
        except Exception as e:
            print(f"Error uploading file to GridFS: {e}")
            return None

    def get_file(self, file_id, is_image=True):
        try:
            file_data = self.fs.get(ObjectId(file_id))
            if is_image:
                metadata = self.images.find_one({"file_id": file_id})
            else:
                metadata = self.videos.find_one({"file_id": file_id})
            return file_data, metadata["content_type"] if metadata else "application/octet-stream"
        except Exception as e:
            print(f"Error getting file from GridFS: {e}")
            return None, None

    def delete_file(self, file_id, is_image=True):
        try:
            # Delete from GridFS
            self.fs.delete(ObjectId(file_id))
            
            # Delete metadata
            if is_image:
                self.images.delete_one({"file_id": file_id})
            else:
                self.videos.delete_one({"file_id": file_id})
                
        except Exception as e:
            print(f"Error deleting file from GridFS: {e}")

# Create a global instance
gridfs_client = GridFSConfig() 