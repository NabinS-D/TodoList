
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection from .env file
MONGODB_URL = os.getenv("MONGODB_URL")

# Create async client and database
client = AsyncIOMotorClient(MONGODB_URL)
database = client.fastapi_db
employees = database.employees
todos = database.todos
chat_messages = database.chat_messages

# Simple connection test
async def connect_to_mongo():
    try:
        await client.admin.command('ping')
        print("Connected to MongoDB Atlas!")
    except Exception as e:
        print(f"MongoDB connection error: {e}")