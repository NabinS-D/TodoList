from pydantic import BaseModel, Field, EmailStr
from enum import Enum
from typing import Optional
from datetime import datetime

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class Status(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class Employee(BaseModel):
    name: str
    position: str
    department: str
    email: EmailStr
    gender: Gender
    salary: float
    hire_date: datetime

class Todo(BaseModel):
    title: str
    description: str
    priority: Priority
    status: Status
    assigned_to: str
    due_date: datetime

# User models for authentication
class User(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str
    password: str = Field(..., min_length=6)
    display_name: Optional[str] = None
    is_active: bool = True

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    username: str
    email: str
    display_name: Optional[str]
    is_active: bool
    created_at: datetime

# Private message models
class PrivateMessage(BaseModel):
    sender: str
    receiver: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    is_read: bool = False

class PrivateChatRoom(BaseModel):
    user1: str
    user2: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_message: Optional[str] = None
    last_message_time: Optional[datetime] = None
