from datetime import datetime
from typing import Optional
import uuid

class Post:
    def __init__(self, user_id: str, content: str, 
                 post_id: Optional[str] = None,
                 image_id: Optional[str] = None, 
                 video_id: Optional[str] = None,
                 likes: int = 0, 
                 reposts: int = 0, 
                 comments: int = 0,
                 created_at: Optional[datetime] = None, 
                 updated_at: Optional[datetime] = None):
        self.post_id = post_id or str(uuid.uuid4())
        self.user_id = user_id
        self.content = content
        self.image_id = image_id
        self.video_id = video_id
        self.likes = likes
        self.reposts = reposts 
        self.comments = comments
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def to_dict(self):
        return {
            "post_id": self.post_id,
            "user_id": self.user_id,
            "content": self.content,
            "image_id": self.image_id,
            "video_id": self.video_id,
            "likes": self.likes,
            "reposts": self.reposts,
            "comments": self.comments,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @staticmethod
    def from_dict(data: dict):
        user_data = data.get("user", {})
        user_id = user_data.get("_id") or data.get("user_id")  # fallback nếu dùng kiểu cũ

        return Post(
            post_id=data.get("post_id"),
            user_id=user_id,
            content=data["content"],
            image_id=data.get("image_id"),
            video_id=data.get("video_id"),
            likes=data.get("likes", 0),
            reposts=data.get("reposts", 0),
            comments=data.get("comments", 0),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )

