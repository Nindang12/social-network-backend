from pymongo import MongoClient
import os
from DAO.connection import DatabaseConnection
import uuid
import bcrypt
from DAO.User.User import User
from fastapi import HTTPException

class User_dao:
    def __init__(self):
        self.db = DatabaseConnection.get_db()
        self.collection = self.db["user"]
        self.token_blacklist = self.db["token_blacklist"]
    def create_user(self, user: User):
        # Validate required fields
        if not user.email or not user.username or not user.phone_number:
            raise HTTPException(status_code=400, detail="Email, username and phone number are required fields")
       
        # Hash password before storing
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), salt)
        
        user = {
            "user_id": str(uuid.uuid4()),   
            "full_name": user.full_name,
            "phone_number": user.phone_number,
            "username": user.username,
            "email": user.email,
            "password": hashed_password
        }
        return self.collection.insert_one(user)

    def get_user(self, user_id: str):
        user = self.collection.find_one({"user_id": user_id})
        if user:
            user["_id"] = str(user["_id"])
            return user
        return None                                                                                                                                                                                                                                                                                                                                             
    def update_user(self, user_id: str, user: dict):
        # Validate user exists
        existing_user = self.get_user(user_id)
        if not existing_user:
            raise HTTPException(status_code=404, detail="User not found")

        # Build update data, only including fields that were provided
        user_data = {}
        if user.get("full_name"):
            user_data["full_name"] = user.get("full_name")
        if user.get("phone_number"):
            # Check if phone number is already taken by another user
            existing = self.get_user_by_phone_number(user.get("phone_number"))
            if existing and existing["user_id"] != user_id:
                raise HTTPException(status_code=400, detail="Phone number already in use")
            user_data["phone_number"] = user.get("phone_number")
        if user.get("username"):
            # Check if username is already taken
            existing = self.get_user_by_username(user.get("username")) 
            if existing and existing["user_id"] != user_id:
                raise HTTPException(status_code=400, detail="Username already taken")
            user_data["username"] = user.get("username")
        if user.get("email"):
            # Check if email is already taken
            existing = self.get_user_by_email(user.get("email"))
            if existing and existing["user_id"] != user_id:
                raise HTTPException(status_code=400, detail="Email already in use")
            user_data["email"] = user.get("email")
        if user.get("avatar") is not None:
            user_data["avatar"] = user.get("avatar")
        if user.get("bio") is not None:
            user_data["bio"] = user.get("bio")

        # Only update if there are changes
        if user_data:
            return self.collection.update_one(
                {"user_id": user_id}, 
                {"$set": user_data}
            )
        return None
    def get_user_by_full_name(self, full_name: str):
        return self.collection.find_one({"full_name": full_name})
    def get_user_by_phone_number(self, phone_number: str):
        return self.collection.find_one({"phone_number": phone_number})
    def get_user_by_email(self, email: str):
        return self.collection.find_one({"email": email})
    def get_user_by_username(self, username: str):
        return self.collection.find_one({"username": username})
    def authenticate_user(self, phone_number: str, email: str, username: str, password: str):
        # Find user by phone/email/username first
        user = self.collection.find_one({"phone_number": phone_number})
        if user:
            if bcrypt.checkpw(password.encode('utf-8'), user["password"]):
                return user
        user = self.collection.find_one({"email": email})
        if user:
            if bcrypt.checkpw(password.encode('utf-8'), user["password"]):
                return user
        user = self.collection.find_one({"username": username})
        if user:
            if bcrypt.checkpw(password.encode('utf-8'), user["password"]):
                return user
        return None
    def logout(self, token: str):
        return self.token_blacklist.insert_one({"token": token})
    def is_token_blacklisted(self, token: str):
        return self.token_blacklist.find_one({"token": token}) is not None
    def get_users(self):
        users = self.collection.find()
        user_list = list(users)
        for user in user_list:
            user["_id"] = str(user["_id"])  
            users = self.collection.find({}, {"password": 0})
        return user_list
    def search_user(self, query: str = None):
        if not query:
            return []
        regex = {"$regex": query, "$options": "i"}
        or_conditions = [
            {"username": regex},
            {"full_name": regex},
            {"email": regex},
            {"phone_number": regex},
        ]
        mongo_query = {"$or": or_conditions}
        result = list(self.collection.find(mongo_query, {"password": 0}))
        for user in result:
            user["_id"] = str(user["_id"])
        return result
    def follow_user(self, current_user_id: str, target_user_id: str):
        if current_user_id == target_user_id:
            raise HTTPException(status_code=400, detail="You cannot follow yourself")
        user_collection = self.collection
        current_user = user_collection.find_one({"user_id": current_user_id})
        target_user = user_collection.find_one({"user_id": target_user_id})
        if not current_user or not target_user:
            raise HTTPException(status_code=404, detail="User not found")
        # Check if already following
        if "following" in current_user and target_user_id in current_user["following"]:
            raise HTTPException(status_code=400, detail="Already following this user")
        # Add to following and followers
        user_collection.update_one(
            {"user_id": current_user_id},
            {"$addToSet": {"following": target_user_id}}
        )
        user_collection.update_one(
            {"user_id": target_user_id},
            {"$addToSet": {"followers": current_user_id}}
        )
        return {"message": "Follow user successfully"}
    def unfollow_user(self, current_user_id: str, target_user_id: str):
        if current_user_id == target_user_id:
            raise HTTPException(status_code=400, detail="You cannot unfollow yourself")
        user_collection = self.collection
        current_user = user_collection.find_one({"user_id": current_user_id})
        target_user = user_collection.find_one({"user_id": target_user_id})
        if not current_user or not target_user:
            raise HTTPException(status_code=404, detail="User not found")
        # Remove from following and followers
        user_collection.update_one(
            {"user_id": current_user_id},
            {"$pull": {"following": target_user_id}}
        )
        user_collection.update_one(
            {"user_id": target_user_id},
            {"$pull": {"followers": current_user_id}}
        )
        return {"message": "Unfollowed user successfully"}
