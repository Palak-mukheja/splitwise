from fastapi import FastAPI
from app.schemas import PercentageExpenseCreate
from app.services.split import calculate_percentage_split
from fastapi import Depends
from app.services.split import (
    calculate_equal_split,
    calculate_exact_split,
)
from fastapi import HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta, timezone

SECRET_KEY = "your-secret-key-change-this-later"
ALGORITHM = "HS256"

from app.schemas import ExpenseCreate
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()

from app.schemas import LoginRequest, RegisterRequest, GroupCreate, AddMemberRequest
from sqlalchemy import select
from app.schemas import ExactExpenseCreate
from app.services.split import calculate_exact_split

from app.database import SessionLocal
from app.models import User, Group, GroupMember, Expense, ExpenseSplit


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
    

@app.post("/groups/{group_id}/expenses")
def create_expense(
    group_id: int,
    expense: ExpenseCreate,
    current_user: User = Depends(get_current_user)
):
    db = SessionLocal()

    try:
        # 1. Check whether the current user belongs to the group
        stmt = select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.id
        )

        result = db.execute(stmt)
        current_user_membership = result.scalar_one_or_none()

        if current_user_membership is None:
            raise HTTPException(
                status_code=403,
                detail="You are not a member of this group"
            )

        # 2. Check whether the payer belongs to the group
        stmt = select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == expense.paid_by
        )

        result = db.execute(stmt)
        paid_by_membership = result.scalar_one_or_none()

        if expense.amount_paise <= 0:
            raise HTTPException(
                status_code=400,
                detail="Expense amount must be positive"
            )

        if paid_by_membership is None:
            raise HTTPException(
                status_code=400,
                detail="Payer is not a member of this group"
            )

        new_expense = Expense(
            group_id=group_id,
            paid_by=expense.paid_by,
            amount_paise=expense.amount_paise,
            description=expense.description
        )

        db.add(new_expense)
        db.flush()

        stmt = select(GroupMember).where(
            GroupMember.group_id == group_id
        )

        result = db.execute(stmt)
        memberships = result.scalars().all()

        member_ids = [
            membership.user_id
            for membership in memberships
        ]

        splits = calculate_equal_split(
       new_expense.amount_paise,
       member_ids
)

        for user_id, share_paise in splits:
            split = ExpenseSplit(
                expense_id=new_expense.id,
                user_id=user_id,
                share_paise=share_paise
            )
            db.add(split)

        db.commit()
        db.refresh(new_expense)

        return {
            "id": new_expense.id,
            "group_id": new_expense.group_id,
            "paid_by": new_expense.paid_by,
            "amount_paise": new_expense.amount_paise,
            "description": new_expense.description,
            "splits": [
                {
                    "user_id": user_id,
                    "share_paise": share_paise
                }
                for user_id, share_paise in splits
            ]
        }
    except ValueError as error:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

@app.post("/groups/{group_id}/expenses/exact")
def create_exact_expense(
    group_id: int,
    expense: ExactExpenseCreate,
    current_user: User = Depends(get_current_user)
):
    db = SessionLocal()

    try:
        # 1. Check that the requester belongs to the group
        stmt = select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.id
        )
        current_membership = db.execute(
            stmt
        ).scalar_one_or_none()

        if current_membership is None:
            raise HTTPException(
                status_code=403,
                detail="You are not a member of this group"
            )

        # 2. Get all members of the group
        stmt = select(GroupMember.user_id).where(
            GroupMember.group_id == group_id
        )
        group_member_ids = set(
            db.execute(stmt).scalars().all()
        )

        # 3. Check that the payer belongs to the group
        if expense.paid_by not in group_member_ids:
            raise HTTPException(
                status_code=400,
                detail="Payer is not a member of this group"
            )

        # 4. Check that every split user belongs to the group
        for split_item in expense.splits:
            if split_item.user_id not in group_member_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"User {split_item.user_id} is not a member of this group"
                )

      
        splits = calculate_equal_split(
            new_expense.amount_paise,
            member_ids
            )


        # 6. Create the expense
        new_expense = Expense(
            group_id=group_id,
            paid_by=expense.paid_by,
            amount_paise=expense.amount_paise,
            description=expense.description
        )

        db.add(new_expense)
        db.flush()

        # 7. Create one database row per share
        for user_id, share_paise in splits:
            db.add(
                ExpenseSplit(
                    expense_id=new_expense.id,
                    user_id=user_id,
                    share_paise=share_paise
                )
            )

        # 8. Save everything together
        db.commit()
        db.refresh(new_expense)

        return {
            "id": new_expense.id,
            "group_id": new_expense.group_id,
            "paid_by": new_expense.paid_by,
            "amount_paise": new_expense.amount_paise,
            "description": new_expense.description,
            "split_type": "exact",
            "splits": [
                {
                    "user_id": user_id,
                    "share_paise": share_paise
                }
                for user_id, share_paise in splits
            ]
        }

    except ValueError as error:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


@app.post("/groups/{group_id}/expenses/percentage")
def create_percentage_expense(
    group_id: int,
    expense: PercentageExpenseCreate,
    current_user: User = Depends(get_current_user)
):
    db = SessionLocal()

    try:
        # 1. Check that the requester belongs to the group
        stmt = select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.id
        )
        membership = db.execute(stmt).scalar_one_or_none()

        if membership is None:
            raise HTTPException(
                status_code=403,
                detail="You are not a member of this group"
            )

        # 2. Get all group member IDs
        stmt = select(GroupMember.user_id).where(
            GroupMember.group_id == group_id
        )
        group_member_ids = set(db.execute(stmt).scalars().all())

        # 3. Validate the payer
        if expense.paid_by not in group_member_ids:
            raise HTTPException(
                status_code=400,
                detail="Payer is not a member of this group"
            )

        # 4. Validate every split user
        for split_item in expense.splits:
            if split_item.user_id not in group_member_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"User {split_item.user_id} is not a member of this group"
                )

        # 5. Calculate percentage shares
        splits = calculate_percentage_split(
            expense.amount_paise,
            expense.splits
        )

        # 6. Create the expense
        new_expense = Expense(
            group_id=group_id,
            paid_by=expense.paid_by,
            amount_paise=expense.amount_paise,
            description=expense.description
        )
        db.add(new_expense)
        db.flush()

        # 7. Create the split records
        for user_id, share_paise in splits:
            db.add(
                ExpenseSplit(
                    expense_id=new_expense.id,
                    user_id=user_id,
                    share_paise=share_paise
                )
            )

        # 8. Save everything in one transaction
        db.commit()
        db.refresh(new_expense)

        return {
            "id": new_expense.id,
            "group_id": new_expense.group_id,
            "paid_by": new_expense.paid_by,
            "amount_paise": new_expense.amount_paise,
            "description": new_expense.description,
            "split_type": "percentage",
            "splits": [
                {
                    "user_id": user_id,
                    "share_paise": share_paise
                }
                for user_id, share_paise in splits
            ]
        }

    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(error))

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()
