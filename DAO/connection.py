from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

class DatabaseConnection:
    _instance = None
    _db = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
            client = MongoClient(os.getenv("MONGO_URI"))
            cls._db = client[os.getenv("MONGO_DB")]
        return cls._instance

    @staticmethod
    def get_db():
        if DatabaseConnection._instance is None:
            DatabaseConnection._instance = DatabaseConnection()
        return DatabaseConnection._db
    @staticmethod
    def get_jwt_secret_key():
        return os.getenv("JWT_SECRET_KEY")

