from DAO.connection import DatabaseConnection
from DAO.Comment.Comment import Comment
from fastapi import HTTPException, UploadFile
from DAO.GridFSConfig import gridfs_client
import uuid
from datetime import datetime
from typing import Optional, List
import os

class Comment_dao:
    def __init__(self):
        self.db = DatabaseConnection.get_db()
        self.collection = self.db["comment"]
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

        # Check file size
        file_size = 0
        for chunk in file.file:
            file_size += len(chunk)
            if file_size > self.MAX_FILE_SIZE:
                file.file.seek(0)  # Reset file pointer before raising exception
                raise HTTPException(
                    status_code=400,
                    detail=f"File size exceeds maximum allowed size of {self.MAX_FILE_SIZE/1024/1024}MB"
                )
        file.file.seek(0)  # Reset file pointer after validation
        return file_size

    def comment_post(self,post_id: str, user_id: str,  content: str, image: Optional[UploadFile] = None, video: Optional[UploadFile] = None):
        try:
            # Kiểm tra bài post có tồn tại không
            post_collection = self.db["post"]
            post = post_collection.find_one({"post_id": post_id})
            print(f"Checking post_id: {post_id}")  # log

            if not post:
                raise HTTPException(status_code=404, detail="Post not found")

            # Kiểm tra user có tồn tại không
            user_collection = self.db["user"]
            user = user_collection.find_one({"user_id": user_id})
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            # Tạo comment mới (chỉ cho comment gốc, không phải reply)
            comment_dict = {
                "comment_id": str(uuid.uuid4()),
                "post_id": post_id,
                "user_id": user_id,
                "content": content,
                "parent_comment_id": None,
                "image_id": None,
                "video_id": None,
                "likes": 0,
                "liked_by": [],
                "replies": 0,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }

            # Handle image upload
            if image:
                try:
                    self._validate_file(image, is_image=True)
                    image_filename = f"comment_images/{comment_dict['comment_id']}_{image.filename}"
                    image_content = image.file.read()
                    image_id = gridfs_client.upload_file(
                        file_data=image_content,
                        file_name=image_filename,
                        content_type=image.content_type,
                        is_image=True
                    )
                    comment_dict["image_id"] = image_id
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Image upload failed: {str(e)}")

            # Handle video upload
            if video:
                try:
                    self._validate_file(video, is_image=False)
                    video_filename = f"comment_videos/{comment_dict['comment_id']}_{video.filename}"
                    video_content = video.file.read()
                    video_id = gridfs_client.upload_file(
                        file_data=video_content,
                        file_name=video_filename,
                        content_type=video.content_type,
                        is_image=False
                    )
                    comment_dict["video_id"] = video_id
                except Exception as e:
                    # If video upload fails and we have an image, we should clean up the image
                    if comment_dict["image_id"]:
                        try:
                            gridfs_client.delete_file(comment_dict["image_id"], is_image=True)
                        except:
                            pass
                    raise HTTPException(status_code=400, detail=f"Video upload failed: {str(e)}")

            # Thêm comment vào database
            self.collection.insert_one(comment_dict)

            # Tăng comments count của post
            post_collection.update_one(
                {"post_id": post_id},
                {"$inc": {"comments": 1}}
            )

            return comment_dict

        except HTTPException:
            raise
        except Exception as e:
            # Clean up uploaded files if database insertion fails
            if "image_id" in locals() and comment_dict.get("image_id"):
                try:
                    gridfs_client.delete_file(comment_dict["image_id"], is_image=True)
                except:
                    pass
            if "video_id" in locals() and comment_dict.get("video_id"):
                try:
                    gridfs_client.delete_file(comment_dict["video_id"], is_image=False)
                except:
                    pass
            raise HTTPException(status_code=500, detail=f"Failed to create comment: {str(e)}")

    def reply_comment(self, comment_id: str, user_id: str, content: str, image: Optional[UploadFile] = None, video: Optional[UploadFile] = None):
        try:
            # 1. Kiểm tra comment cha
            parent = self.collection.find_one({"comment_id": comment_id})
            if not parent:
                raise HTTPException(status_code=404, detail="Parent comment not found")

            # 2. (Tuỳ chọn) kiểm tra user tồn tại
            user = self.db["user"].find_one({"user_id": user_id})
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            # 3. Tạo reply dict
            reply = {
                "comment_id": str(uuid.uuid4()),
                "post_id": parent["post_id"],
                "user_id": user_id,
                "content": content,
                "parent_comment_id": comment_id,
                "image_id": None,
                "video_id": None,
                "likes": 0,
                "liked_by": [],
                "replies": 0,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

            # 4. Xử lý image
            if image:
                self._validate_file(image, is_image=True)
                fn = f"comment_images/{reply['comment_id']}_{image.filename}"
                data = image.file.read()
                reply["image_id"] = gridfs_client.upload_file(
                    file_data=data,
                    file_name=fn,
                    content_type=image.content_type,
                    is_image=True
                )
                image.file.close()

            # 5. Xử lý video
            if video:
                self._validate_file(video, is_image=False)
                fn = f"comment_videos/{reply['comment_id']}_{video.filename}"
                data = video.file.read()
                reply["video_id"] = gridfs_client.upload_file(
                    file_data=data,
                    file_name=fn,
                    content_type=video.content_type,
                    is_image=False
                )
                video.file.close()
            
            # 6. Lưu reply và tăng count
            self.collection.insert_one(reply)

            # Cập nhật replies count của comment cha
            self.collection.update_one(
                {"comment_id": comment_id},
                {"$inc": {"replies": 1}}
            )

            # ✅ Cập nhật tổng comment count trong bài post
            self.db["post"].update_one(
                {"post_id": parent["post_id"]},
                {"$inc": {"comments": 1}}
            )

            return reply

        except HTTPException:
            raise
        except Exception as e:
            # Dọn rác nếu có image/video đã up lên
            if reply.get("image_id"):
                try: gridfs_client.delete_file(reply["image_id"], is_image=True)
                except: pass
            if reply.get("video_id"):
                try: gridfs_client.delete_file(reply["video_id"], is_image=False)
                except: pass
            raise HTTPException(status_code=500, detail=f"Failed to create reply: {e}")

    def edit_comment(self, comment_id: str, content: str, user_id: str):
        try:
            # Check if comment exists
            comment = self.collection.find_one({"comment_id": comment_id})
            if not comment:
                raise HTTPException(status_code=404, detail="Comment not found")

            # Check if user is the comment creator
            if comment["user_id"] != user_id:
                raise HTTPException(status_code=403, detail="You are not authorized to edit this comment")

            # Update comment content
            self.collection.update_one(
                {"comment_id": comment_id},
                {
                    "$set": {
                        "content": content,
                        "updated_at": datetime.now()
                    }
                }
            )

            # Get updated comment
            updated_comment = self.collection.find_one({"comment_id": comment_id})
            if "_id" in updated_comment:
                updated_comment["_id"] = str(updated_comment["_id"])
            return updated_comment

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to edit comment: {str(e)}")

    def get_comments_by_user_id(self, user_id: str):
        try:
            # Lấy tất cả comments của user
            comments = self.collection.find({"user_id": user_id})
            return list(comments)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get comments by user_id: {str(e)}")
    def delete_comment(self, comment_id: str, user_id: str):
        try:
            # Check if comment exists
            comment = self.collection.find_one({"comment_id": comment_id})
            if not comment:
                raise HTTPException(status_code=404, detail="Comment not found")

            # Check if user is the comment creator
            if comment["user_id"] != user_id:
                raise HTTPException(status_code=403, detail="You are not authorized to delete this comment")

            # Nếu là reply thì giảm replies count của comment cha
            if comment.get("parent_comment_id"):
                self.collection.update_one(
                    {"comment_id": comment["parent_comment_id"]},
                    {"$inc": {"replies": -1}}
                )

            # Xóa comment
            self.collection.delete_one({"comment_id": comment_id})

            # Luôn giảm comments count của post đúng 1 lần
            self.db["post"].update_one(
                {"post_id": comment["post_id"]},
                {"$inc": {"comments": -1}}
            )

            return {"message": "Comment deleted successfully"}

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete comment: {str(e)}")

    def like_comment(self, comment_id: str, user_id: str):
        try:
            # Get the comment first
            comment = self.collection.find_one({"comment_id": comment_id})
            if not comment:
                raise HTTPException(status_code=404, detail="Comment not found")

            # Check if user has already liked the comment
            if "liked_by" not in comment:
                # Initialize liked_by array if it doesn't exist
                self.collection.update_one(
                    {"comment_id": comment_id},
                    {"$set": {"liked_by": []}}
                )
                comment["liked_by"] = []

            if user_id in comment["liked_by"]:
                # User already liked the comment, so unlike it
                self.collection.update_one(
                    {"comment_id": comment_id},
                    {
                        "$inc": {"likes": -1},
                        "$pull": {"liked_by": user_id}
                    }
                )
            else:
                # User hasn't liked the comment, so like it
                self.collection.update_one(
                    {"comment_id": comment_id},
                    {
                        "$inc": {"likes": 1},
                        "$push": {"liked_by": user_id}
                    }
                )

            # Get updated comment
            updated_comment = self.collection.find_one({"comment_id": comment_id})
            if "_id" in updated_comment:
                updated_comment["_id"] = str(updated_comment["_id"])
            return updated_comment

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to toggle like comment: {str(e)}")

    def get_comments(self, post_id: str):
        try:
            # Get all comments for the post
            comments = self.collection.find({"post_id": post_id})
            
            results = []
            for comment in comments:
                if "_id" in comment:
                    comment["_id"] = str(comment["_id"])
                results.append(comment)

            if not results:
                raise HTTPException(status_code=404, detail="No comments found")

            return results

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get comments: {str(e)}")

    def get_replies(self, comment_id: str):
        try:
            # Get all replies for the comment
            replies = self.collection.find({"parent_comment_id": comment_id})
            
            results = []
            for reply in replies:
                if "_id" in reply:
                    reply["_id"] = str(reply["_id"])
                results.append(reply)

            return results

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get replies: {str(e)}")

