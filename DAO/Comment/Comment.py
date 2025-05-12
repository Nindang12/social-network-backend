from datetime import datetime
import uuid
from typing import Optional

class Comment:
    def __init__(self, user_id: str, post_id: str, content: str, parent_comment_id: str = None, 
                 image_id: str = None, video_id: str = None):
        self.comment_id = str(uuid.uuid4())
        self.user_id = user_id
        self.post_id = post_id
        self.content = content
        self.parent_comment_id = parent_comment_id
        self.image_id = image_id
        self.video_id = video_id
        self.likes = 0
        self.liked_by = []
        self.replies = 0
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def to_dict(self):
        return {
            "comment_id": self.comment_id,
            "user_id": self.user_id,
            "post_id": self.post_id,
            "content": self.content,
            "parent_comment_id": self.parent_comment_id,
            "image_id": self.image_id,
            "video_id": self.video_id,
            "likes": self.likes,
            "liked_by": self.liked_by,
            "replies": self.replies,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @staticmethod
    def from_dict(data: dict):
        comment = Comment(
            user_id=data["user_id"],
            post_id=data["post_id"], 
            content=data["content"],
            parent_comment_id=data.get("parent_comment_id"),
            image_id=data.get("image_id"),
            video_id=data.get("video_id")
        )
        comment.comment_id = data["comment_id"]
        comment.likes = data["likes"]
        comment.liked_by = data["liked_by"]
        comment.replies = data["replies"]
        comment.created_at = data["created_at"]
        comment.updated_at = data["updated_at"]
        return comment
