from fastapi import UploadFile

class User:
    
    def __init__(self, user_id: str, full_name: str, phone_number: str, username: str, email: str, password: str, bio: str):
        self.user_id = user_id
        self.full_name = full_name
        self.phone_number = phone_number
        self.username = username
        self.email = email
        self.password = password
        self.bio = bio
    def to_json(self):
        return {
            "user_id": self.user_id,
            "full_name": self.full_name, 
            "phone_number": self.phone_number,
            "username": self.username,
            "email": self.email,
            "password": self.password,
            "bio": self.bio
        }
    def get_email(self):
        return self.email
    def get_full_name(self):
        return self.full_name
    def get_phone_number(self):
        return self.phone_number
    def get_username(self):
        return self.username
