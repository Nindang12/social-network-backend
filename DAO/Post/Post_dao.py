from DAO.connection import DatabaseConnection
import uuid
from datetime import datetime
from fastapi import UploadFile, Form, File, HTTPException
from DAO.GridFSConfig import gridfs_client
from DAO.Post.Post import Post
from typing import Optional
import os
from fastapi.responses import StreamingResponse
from io import BytesIO
from DAO.User.User_dao import User_dao
class Post_dao:
    def __init__(self):
        self.db = DatabaseConnection.get_db()
        self.collection = self.db["post"]
        self.MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        self.ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif'}
        self.ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi'}

    def _validate_file(self, file: UploadFile, is_image: bool = True):
        # Check file extension
        file_ext = os.path.splitext(file.filename)[1].lower()
        allowed_extensions = self.ALLOWED_IMAGE_EXTENSIONS if is_image else self.ALLOWED_VIDEO_EXTENSIONS
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
            )

        # Read file content
        file_content = file.file.read()
        file_size = len(file_content)
        
        # Check file size
        if file_size > self.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum allowed size of {self.MAX_FILE_SIZE/1024/1024}MB"
            )
        
        # Reset file pointer
        file.file.seek(0)
        return file_size, file_content

    def create_post(self, user_id: str, content: str, image: Optional[UploadFile] = None, video: Optional[UploadFile] = None):
        # Create post dictionary from Post object
        user = User_dao().get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        post_dict = {
            "post_id": str(uuid.uuid4()),
            "user_id": user_id,
            "content": content,
            "image_id": None,
            "video_id": None,
            "likes": 0,
            "liked_by": [],
            "reposts": 0,
            "reposted_by": [], # List to track users who reposted
            "comments": 0,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        try:
            # Handle image upload
            if image:
                try:
                    file_size, image_content = self._validate_file(image, is_image=True)
                    image_filename = f"images/{post_dict['post_id']}_{image.filename}"
                    image_id = gridfs_client.upload_file(
                        file_data=image_content,
                        file_name=image_filename,
                        content_type=image.content_type,
                        is_image=True
                    )
                    if image_id:
                        post_dict["image_id"] = image_id
                    else:
                        raise HTTPException(status_code=400, detail="Failed to upload image to GridFS")
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Image upload failed: {str(e)}")

            # Handle video upload
            if video:
                try:
                    file_size, video_content = self._validate_file(video, is_image=False)
                    video_filename = f"videos/{post_dict['post_id']}_{video.filename}"
                    video_id = gridfs_client.upload_file(
                        file_data=video_content,
                        file_name=video_filename,
                        content_type=video.content_type,
                        is_image=False
                    )
                    if video_id:
                        post_dict["video_id"] = video_id
                    else:
                        raise HTTPException(status_code=400, detail="Failed to upload video to GridFS")
                except Exception as e:
                    # If video upload fails and we have an image, we should clean up the image
                    if post_dict["image_id"]:
                        try:
                            gridfs_client.delete_file(post_dict["image_id"], is_image=True)
                        except:
                            pass
                    raise HTTPException(status_code=400, detail=f"Video upload failed: {str(e)}")

            # Insert post into database
            self.collection.insert_one(post_dict)
            return post_dict

        except Exception as e:
            # Clean up uploaded files if database insertion fails
            if post_dict["image_id"]:
                try:
                    gridfs_client.delete_file(post_dict["image_id"], is_image=True)
                except:
                    pass
            if post_dict["video_id"]:
                try:
                    gridfs_client.delete_file(post_dict["video_id"], is_image=False)
                except:
                    pass
            raise HTTPException(status_code=500, detail=f"Failed to create post: {str(e)}")

   
    def get_post(self, post_id: str):
        try:
            post = self.collection.find_one({"post_id": post_id})
            if post:
                if "_id" in post:
                    post["_id"] = str(post["_id"])
                if "liked_by" not in post or post["liked_by"] is None:
                    post["liked_by"] = []
                return post
            return None
        except Exception as e:
            print(f"Error getting post: {str(e)}")
            return None
    
    def get_post_by_id(self, post_id: str):
        try:
            post = self.collection.find_one({"post_id": post_id})
            if post:
                if "_id" in post:
                    post["_id"] = str(post["_id"])
                return post  # Không dùng Post.from_dict()
            return None
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get post by id: {str(e)}")
    
    def get_user_posts(self, user_id: str):
        try:
            posts = self.collection.find({"user_id": user_id})
            result = []
            for post in posts:
                if "_id" in post:
                    post["_id"] = str(post["_id"])
                result.append(post)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get user posts: {str(e)}")
    def get_posts(self):
        try:
            posts = self.collection.find()
            result = []
            for post in posts:
                if "_id" in post:
                    post["_id"] = str(post["_id"])

                if "liked_by" not in post or post["liked_by"] is None:
                    post["liked_by"] = []

                result.append(post)
            return result

        except Exception as e:
            print(f"Error getting posts: {str(e)}")
            return []

    def edit_post(self, post_id: str, content: str, user_id: str):
        try:
            # Check if post exists
            post = self.collection.find_one({"post_id": post_id})
            if not post:
                raise HTTPException(status_code=404, detail="Post not found")

            # Check if user is the post creator
            if post["user_id"] != user_id:
                raise HTTPException(status_code=403, detail="You are not authorized to edit this post")

            self.collection.update_one(
                {"post_id": post_id}, 
                {
                    "$set": {
                        "content": content,
                        "updated_at": datetime.now()
                    }
                }
            )
            return {"message": "Post updated successfully"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to update post: {str(e)}")

    def delete_post(self, post_id: str, user_id: str):
        try:
            post = self.collection.find_one({"post_id": post_id})
            if not post:
                raise HTTPException(status_code=404, detail="Post not found")

            if str(post["user_id"]) != str(user_id):
                raise HTTPException(status_code=403, detail="You are not authorized to delete this post")


            self.collection.delete_one({"post_id": post_id})
            return {"message": "Post deleted successfully"}

        except HTTPException as http_exc:
            raise http_exc  # Để FastAPI trả về đúng lỗi 403 hoặc 404

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete post: {str(e)}")
    def like_post(self, post_id: str, user_id: str):
        try:
            # Get the post first
            post = self.collection.find_one({"post_id": post_id})
            if not post:
                return None

            # Check if user has already liked the post
            if "liked_by" not in post:
                # Initialize liked_by array if it doesn't exist
                self.collection.update_one(
                    {"post_id": post_id},
                    {"$set": {"liked_by": []}}
                )
                post["liked_by"] = []

            if user_id in post["liked_by"]:
                # User already liked the post, so unlike it
                self.collection.update_one(
                    {"post_id": post_id},
                    {
                        "$inc": {"likes": -1},
                        "$pull": {"liked_by": user_id}
                    }
                )
            else:
                # User hasn't liked the post, so like it
                self.collection.update_one(
                    {"post_id": post_id},
                    {
                        "$inc": {"likes": 1},
                        "$push": {"liked_by": user_id}
                    }
                )

            # Get updated post
            updated_post = self.collection.find_one({"post_id": post_id})
            if "_id" in updated_post:
                updated_post["_id"] = str(updated_post["_id"])
            return updated_post

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to toggle like post: {str(e)}")

    def get_posts_with_comments(self, commenter_id: str):
        try:
            # Get all posts
            posts = self.collection.find()
            result = []
            for post in posts: 
                if "_id" in post:
                    post["_id"] = str(post["_id"])
                result.append(post)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get posts with comments: {str(e)}")

    def repost(self, post_id: str, user_id: str):
        try:
            # Get the post first
            post = self.collection.find_one({"post_id": post_id})
            if not post:
                return None

            # Check if user has already reposted the post
            if "reposted_by" not in post:
                # Initialize reposted_by array if it doesn't exist
                self.collection.update_one(
                    {"post_id": post_id},
                    {"$set": {"reposted_by": []}}
                )
                post["reposted_by"] = []

            if user_id in post["reposted_by"]:
                # User already reposted, so un-repost it
                self.collection.update_one(
                    {"post_id": post_id},
                    {
                        "$inc": {"reposts": -1},
                        "$pull": {"reposted_by": user_id}
                    }
                )
            else:
                # User hasn't reposted, so repost it
                self.collection.update_one(
                    {"post_id": post_id},
                    {
                        "$inc": {"reposts": 1},
                        "$push": {"reposted_by": user_id}
                    }
                )

            # Get updated post
            updated_post = self.collection.find_one({"post_id": post_id})
            if "_id" in updated_post:
                updated_post["_id"] = str(updated_post["_id"])
            return updated_post

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to toggle repost: {str(e)}")

    def search_posts(self, query: str):
        try:
            # Search for posts containing the query in content or user_id
            posts = self.collection.find({
                "$or": [
                    {"content": {"$regex": query, "$options": "i"}},
                    {"user_id": {"$regex": query, "$options": "i"}},
                    {"post_id": {"$regex": query, "$options": "i"}},
                    {"full_name": {"$regex": query, "$options": "i"}}
                ]
            })

            results = []
            for post in posts:
                if "_id" in post:
                    post["_id"] = str(post["_id"])
                results.append(post)

            if not results:
                raise HTTPException(status_code=404, detail="No posts found")

            return results

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to search posts: {str(e)}")

