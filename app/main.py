from fastapi import FastAPI
from fastapi import Depends
from fastapi import HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta, timezone

SECRET_KEY = "your-secret-key-change-this-later"
ALGORITHM = "HS256"

from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()

from app.schemas import LoginRequest, RegisterRequest, GroupCreate, AddMemberRequest
from sqlalchemy import select

from app.database import SessionLocal
from app.models import User, Group, GroupMember


def create_access_token(user_id: int):
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)

    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "access"
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(user_id: int):
    expire = datetime.now(timezone.utc) + timedelta(days=7)

    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "refresh"
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    user_id = int(payload["sub"])

    db = SessionLocal()

    stmt = select(User).where(User.id == user_id)
    result = db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    db.close()

    if existing_user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    return existing_user

app = FastAPI()


@app.get("/")
def home():
    return {"message": "Welcome to SplitEasy!"}

@app.get("/hello/{name}")
def say_hello(name: str):
    return {"message": f"Hello {name}!"}

@app.post("/groups")
def create_group(
    group: GroupCreate,
    current_user: User = Depends(get_current_user)
):
    db = SessionLocal()

    new_group = Group(
        name=group.name,
        created_by=current_user.id
    )

    db.add(new_group)
    db.flush()
    new_member = GroupMember(
        group_id=new_group.id,
        user_id=current_user.id
    )
    db.add(new_member)
    db.commit()
    db.refresh(new_group)

    response = {
        "id": new_group.id,
        "name": new_group.name,
        "created_by": new_group.created_by
    }

    db.close()

    return response

@app.get("/groups")
def get_groups(
    current_user: User = Depends(get_current_user)
):
    db = SessionLocal()

    stmt = (
        select(Group)
        .join(GroupMember, Group.id == GroupMember.group_id)
        .where(GroupMember.user_id == current_user.id)
    )

    result = db.execute(stmt)
    groups = result.scalars().all()

    db.close()

    return [
        {
            "id": group.id,
            "name": group.name,
            "created_by": group.created_by
        }
        for group in groups
    ]
    
@app.post("/groups/{group_id}/members")
def add_member(
    group_id: int,
    member: AddMemberRequest,
    current_user: User = Depends(get_current_user)
):
    db = SessionLocal()

    stmt = select(GroupMember).where(
        GroupMember.group_id == group_id,
        GroupMember.user_id == current_user.id
    )

    result = db.execute(stmt)
    existing_membership = result.scalar_one_or_none()

    if existing_membership is None:
        db.close()
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this group"
        )
    stmt = select(User).where(User.id == member.user_id)

    result = db.execute(stmt)
    user_to_add = result.scalar_one_or_none()
    if user_to_add is None:
        db.close()
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    stmt = select(GroupMember).where(
        GroupMember.group_id == group_id,
        GroupMember.user_id == member.user_id
    )

    result = db.execute(stmt)
    already_member = result.scalar_one_or_none()

    if already_member is not None:
        db.close()
        raise HTTPException(
            status_code=400,
            detail="User is already a member of this group"
        )

    new_member = GroupMember(
        group_id=group_id,
        user_id=member.user_id
    )

    db.add(new_member)
    db.commit()
    db.close()

    return {
        "message": "User added to group",
        "group_id": group_id,
        "user_id": member.user_id
    }

@app.post("/auth/register")
def register(user: RegisterRequest):
    db = SessionLocal()

    stmt = select(User).where(User.email == user.email)
    result = db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        db.close()
        return {"error": "Email already registered"}

    hashed_password = password_hash.hash(user.password)

    new_user = User(
        name=user.name,
        email=user.email,
        password_hash=hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    db.close()

    return {
        "id": new_user.id,
        "email": new_user.email,
        "name": new_user.name,
        "created_at": new_user.created_at
    }
  
@app.post("/auth/login")
def login(user: LoginRequest):
    db = SessionLocal()

    stmt = select(User).where(User.email == user.email)
    result = db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if not existing_user:
        db.close()
        return {"error": "Invalid email or password"}

    password_valid = password_hash.verify(
        user.password,
        existing_user.password_hash
    )

    if not password_valid:
        db.close()
        return {"error": "Invalid email or password"}
    
    access_token = create_access_token(existing_user.id)
    refresh_token = create_refresh_token(existing_user.id)
    
    db.close()
    return {
    "access_token": access_token,
    "refresh_token": refresh_token,
    "token_type": "bearer"
}
    
@app.post("/auth/refresh")
def refresh_access_token(refresh_token: str):
    try:
        payload = jwt.decode(
            refresh_token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=401,
                detail="Not a refresh token"
            )

        user_id = int(payload["sub"])

    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token"
        )

    new_access_token = create_access_token(user_id)

    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }
    
@app.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "created_at": current_user.created_at
    }