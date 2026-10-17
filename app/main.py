from dataclasses import Field
from fastapi import HTTPException
from redis.exceptions import RedisError
from app.redis_client import (
    check_login_rate_limit,
    get_cached_balances,
    cache_balances,
    invalidate_balance_cache,
)
from app.services.split import calculate_equal_split
from pydantic import BaseModel, Field, EmailStr
from fastapi import FastAPI
from app.schemas import PercentageExpenseCreate
from app.services.split import calculate_balances
from app.services.split import calculate_percentage_split
from fastapi import Depends
from app.services.split import (
    calculate_equal_split,
    calculate_exact_split,
    calculate_percentage_split,
    calculate_balances,
    suggest_settlements,
)
from fastapi import HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta, timezone

import os

SECRET_KEY = os.getenv("SECRET_KEY", "development-only-change-me")
ALGORITHM = "HS256"

from app.schemas import ExpenseCreate
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()

from app.schemas import LoginRequest, RegisterRequest, GroupCreate, AddMemberRequest
from sqlalchemy import select,func
from app.schemas import ExactExpenseCreate
from app.services.split import calculate_exact_split

from app.database import SessionLocal
from app.models import User, Group, GroupMember, Expense, ExpenseSplit, Settlement


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


@app.get("/health")
def health():
    return {"status": "healthy"}


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

@app.get("/groups/{group_id}/expenses")
def get_group_expenses(
    group_id: int,
    page: int = 1,
    limit: int = 10,
    category: str | None = None,
    member_id: int | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    current_user: User = Depends(get_current_user),
):
    if page < 1:
        raise HTTPException(status_code=400, detail="Page must be at least 1")

    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 100",
        )

    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date cannot be after end_date",
        )

    db = SessionLocal()
    try:
        membership = db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == current_user.id,
            )
        ).scalar_one_or_none()

        if membership is None:
            raise HTTPException(
                status_code=403,
                detail="You are not a member of this group",
            )

        stmt = select(Expense).where(Expense.group_id == group_id)

        if category is not None:
            stmt = stmt.where(Expense.category == category)

        if member_id is not None:
            stmt = stmt.where(Expense.paid_by == member_id)

        if start_date is not None:
            stmt = stmt.where(Expense.created_at >= start_date)

        if end_date is not None:
            stmt = stmt.where(Expense.created_at <= end_date)

        count_stmt = select(func.count()).select_from(
            stmt.order_by(None).subquery()
        )
        total = db.execute(count_stmt).scalar_one()

        offset = (page - 1) * limit
        stmt = stmt.order_by(
            Expense.created_at.desc(),
            Expense.id.desc(),
        ).offset(offset).limit(limit)

        expenses = db.execute(stmt).scalars().all()

        return {
            "group_id": group_id,
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit,
            "expenses": [
                {
                    "id": expense.id,
                    "paid_by": expense.paid_by,
                    "amount_paise": expense.amount_paise,
                    "description": expense.description,
                    "category": expense.category,
                    "created_at": expense.created_at,
                }
                for expense in expenses
            ],
        }
    finally:
        db.close()

class SettlementCreate(BaseModel):
    to_user: int
    amount_paise: int = Field(gt=0)


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
    # Step 1: Check the Redis rate limit before processing login.
    try:
        allowed = check_login_rate_limit(user.email)
    except RedisError:
        raise HTTPException(
            status_code=503,
            detail="Login service temporarily unavailable",
        )

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Try again in a minute.",
        )

    # Step 2: Check the user in PostgreSQL.
    db = SessionLocal()
    try:
        stmt = select(User).where(User.email == user.email)
        existing_user = db.execute(stmt).scalar_one_or_none()

        if not existing_user:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password",
            )

        # Step 3: Verify the password.
        password_valid = password_hash.verify(
            user.password,
            existing_user.password_hash,
        )

        if not password_valid:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password",
            )

        # Step 4: Generate tokens after successful authentication.
        access_token = create_access_token(existing_user.id)
        refresh_token = create_refresh_token(existing_user.id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }
    finally:
        db.close()


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

@app.get("/groups/{group_id}/expenses")
def get_group_expenses(
    group_id: int,
    page: int = 1,
    limit: int = 10,
    category: str | None = None,
    member_id: int | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    current_user: User = Depends(get_current_user),
):
    if page < 1:
        raise HTTPException(status_code=400, detail="Page must be at least 1")

    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 100",
        )

    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date cannot be after end_date",
        )

    db = SessionLocal()
    try:
        membership = db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == current_user.id,
            )
        ).scalar_one_or_none()

        if membership is None:
            raise HTTPException(
                status_code=403,
                detail="You are not a member of this group",
            )

        stmt = select(Expense).where(Expense.group_id == group_id)

        if category is not None:
            stmt = stmt.where(Expense.category == category)

        if member_id is not None:
            stmt = stmt.where(Expense.paid_by == member_id)

        if start_date is not None:
            stmt = stmt.where(Expense.created_at >= start_date)

        if end_date is not None:
            stmt = stmt.where(Expense.created_at <= end_date)

        count_stmt = select(func.count()).select_from(
            stmt.order_by(None).subquery()
        )
        total = db.execute(count_stmt).scalar_one()

        offset = (page - 1) * limit
        stmt = stmt.order_by(
            Expense.created_at.desc(),
            Expense.id.desc(),
        ).offset(offset).limit(limit)

        expenses = db.execute(stmt).scalars().all()

        return {
            "group_id": group_id,
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit,
            "expenses": [
                {
                    "id": expense.id,
                    "paid_by": expense.paid_by,
                    "amount_paise": expense.amount_paise,
                    "description": expense.description,
                    "category": expense.category,
                    "created_at": expense.created_at,
                }
                for expense in expenses
            ],
        }
    finally:
        db.close()


@app.post("/groups/{group_id}/expenses")
def create_expense(
    group_id: int,
    expense: ExpenseCreate,
    current_user: User = Depends(get_current_user),
):
    db = SessionLocal()
    try:
        membership = db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == current_user.id,
            )
        ).scalar_one_or_none()

        if membership is None:
            raise HTTPException(
                status_code=403,
                detail="You are not a member of this group",
            )

        members = db.execute(
            select(GroupMember.user_id).where(
                GroupMember.group_id == group_id
            )
        ).scalars().all()

        splits = calculate_equal_split(
           expense.amount_paise,
           members,
           )
        if expense.paid_by != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can only record an expense that you paid for",
            )

        ssplits = calculate_equal_split(expense.amount_paise, members)

        new_expense = Expense(
            group_id=group_id,
            paid_by=expense.paid_by,
            amount_paise=expense.amount_paise,
            description=expense.description,
        )
        db.add(new_expense)
        db.flush()

        for user_id, share_paise in splits:
         db.add(
        ExpenseSplit(
            expense_id=new_expense.id,
            user_id=user_id,
            share_paise=share_paise,
        )
    )

        db.commit()
        db.refresh(new_expense)
        invalidate_balance_cache(group_id)


        return {
            "id": new_expense.id,
            "group_id": new_expense.group_id,
            "paid_by": new_expense.paid_by,
            "amount_paise": new_expense.amount_paise,
            "description": new_expense.description,
        }

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
        invalidate_balance_cache(group_id)
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
        db.commit()
        db.refresh(new_expense)
        invalidate_balance_cache(group_id)
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


@app.get("/groups/{group_id}/balances")
def get_group_balances(
    group_id: int,
    current_user: User = Depends(get_current_user),
):
    db = SessionLocal()

    try:
        # 1. Check membership BEFORE returning cached data.
        stmt = select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.id,
        )
        membership = db.execute(stmt).scalar_one_or_none()

        if membership is None:
            raise HTTPException(
                status_code=403,
                detail="You are not a member of this group",
            )

        # 2. Try Redis cache.
        cached_balances = get_cached_balances(group_id)

        if cached_balances is not None:
            return cached_balances

        # 3. Initialize every group member's balance to zero.
        stmt = select(GroupMember.user_id).where(
            GroupMember.group_id == group_id
        )
        member_ids = db.execute(stmt).scalars().all()

        balances = {user_id: 0 for user_id in member_ids}

        # 4. Aggregate the amount paid by each user.
        stmt = (
            select(
                Expense.paid_by,
                func.sum(Expense.amount_paise),
            )
            .where(Expense.group_id == group_id)
            .group_by(Expense.paid_by)
        )
        paid_totals = db.execute(stmt).all()

        for user_id, total_paid in paid_totals:
            balances[user_id] += total_paid

        # 5. Aggregate each user's shares.
        stmt = (
            select(
                ExpenseSplit.user_id,
                func.sum(ExpenseSplit.share_paise),
            )
            .join(
                Expense,
                Expense.id == ExpenseSplit.expense_id,
            )
            .where(Expense.group_id == group_id)
            .group_by(ExpenseSplit.user_id)
        )
        share_totals = db.execute(stmt).all()

        for user_id, total_shares in share_totals:
            balances[user_id] -= total_shares

        # 6. Add settlements paid by each user.
        stmt = (
            select(
                Settlement.from_user,
                func.sum(Settlement.amount_paise),
            )
            .where(Settlement.group_id == group_id)
            .group_by(Settlement.from_user)
        )
        paid_settlements = db.execute(stmt).all()

        for user_id, total_paid in paid_settlements:
            balances[user_id] += total_paid

        # 7. Subtract settlements received by each user.
        stmt = (
            select(
                Settlement.to_user,
                func.sum(Settlement.amount_paise),
            )
            .where(Settlement.group_id == group_id)
            .group_by(Settlement.to_user)
        )
        received_settlements = db.execute(stmt).all()

        for user_id, total_received in received_settlements:
            balances[user_id] -= total_received

        # 8. Build the same response format as before.
        response = {
            "group_id": group_id,
            "balances": [
                {
                    "user_id": user_id,
                    "balance_paise": balance,
                }
                for user_id, balance in sorted(balances.items())
            ],
        }

        # 9. Cache the result for 60 seconds.
        cache_balances(group_id, response)

        return response

    finally:
        db.close()



@app.post("/groups/{group_id}/settlements")
def create_settlement(
    group_id: int,
    settlement: SettlementCreate,
    current_user: User = Depends(get_current_user)
):
    db = SessionLocal()

    try:
        # 1. Verify that the payer belongs to the group.
        payer_membership = db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == current_user.id
            )
        ).scalar_one_or_none()

        if payer_membership is None:
            raise HTTPException(
                status_code=403,
                detail="You are not a member of this group"
            )

        # 2. Verify that the recipient belongs to the same group.
        recipient_membership = db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == settlement.to_user
            )
        ).scalar_one_or_none()

        if recipient_membership is None:
            raise HTTPException(
                status_code=400,
                detail="Recipient is not a member of this group"
            )

        # 3. A user cannot pay themselves.
        if current_user.id == settlement.to_user:
            raise HTTPException(
                status_code=400,
                detail="You cannot settle a payment with yourself"
            )

        # 4. Create the settlement record.
        new_settlement = Settlement(
            group_id=group_id,
            from_user=current_user.id,
            to_user=settlement.to_user,
            amount_paise=settlement.amount_paise
        )

        db.add(new_settlement)
        db.commit()
        db.refresh(new_settlement)
        invalidate_balance_cache(group_id)
        return {
            "id": new_settlement.id,
            "group_id": new_settlement.group_id,
            "from_user": new_settlement.from_user,
            "to_user": new_settlement.to_user,
            "amount_paise": new_settlement.amount_paise,
            "created_at": new_settlement.created_at
        }

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


@app.get("/groups/{group_id}/settlements/suggestions")
def get_settlement_suggestions(
    group_id: int,
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

        # 2. Fetch all expenses in the group
        stmt = select(Expense).where(
            Expense.group_id == group_id
        )
        expenses = db.execute(stmt).scalars().all()

        # 3. Fetch splits belonging only to those expenses
        expense_ids = [expense.id for expense in expenses]

        if expense_ids:
            stmt = select(ExpenseSplit).where(
                ExpenseSplit.expense_id.in_(expense_ids)
            )
            expense_splits = db.execute(stmt).scalars().all()
        else:
            expense_splits = []

        # 4. Calculate balances and settlement suggestions
        balances = calculate_balances(expenses, expense_splits)
        settlements = suggest_settlements(balances)

        # 5. Return the suggested payments
        return {
            "group_id": group_id,
            "settlements": [
                {
                    "from_user": from_user,
                    "to_user": to_user,
                    "amount_paise": amount_paise
                }
                for from_user, to_user, amount_paise in settlements
            ]
        }

    finally:
        db.close()



