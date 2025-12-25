from pydantic import BaseModel, Field
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

# MongoDB model - just Pydantic
class Employee(BaseModel):
    name: str
    surname: str
    age: int
    gender: Gender
    id: Optional[int] = None  # MongoDB will auto-generate _id
    
    class Config:
        json_encoders = {
            Gender: lambda v: v.value
        }

class Todo(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    priority: Priority = Priority.MEDIUM
    status: Status = Status.PENDING
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            Priority: lambda v: v.value,
            Status: lambda v: v.value,
            datetime: lambda v: v.isoformat() if v else None
        }
