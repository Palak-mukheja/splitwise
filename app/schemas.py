from datetime import datetime
from pydantic import BaseModel
from pydantic import BaseModel, Field, ConfigDict

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
    
class ExpenseCreate(BaseModel):
    amount_paise: int
    description: str
    paid_by: int
class ExactSplitItem(BaseModel):
    user_id: int
    share_paise: int = Field(ge=0)


class ExactExpenseCreate(BaseModel):
    amount_paise: int = Field(gt=0)
    description: str
    paid_by: int
    splits: list[ExactSplitItem] = Field(min_length=1)


from decimal import Decimal
from pydantic import BaseModel, Field


class PercentageSplitItem(BaseModel):
    user_id: int
    percentage: Decimal = Field(ge=0, le=100)


class PercentageExpenseCreate(BaseModel):
    amount_paise: int = Field(gt=0)
    description: str
    paid_by: int
    splits: list[PercentageSplitItem] = Field(min_length=1)
