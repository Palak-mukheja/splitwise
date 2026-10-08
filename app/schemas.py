from datetime import datetime
from pydantic import BaseModel

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    
class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    created_at: datetime
    
class LoginRequest(BaseModel):
    email: str
    password: str
    
class GroupCreate(BaseModel):
    name: str
    
class AddMemberRequest(BaseModel):
    user_id: int