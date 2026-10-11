
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
import pytest 
from sqlalchemy import select,func
from app import main
from app.models import (
    Base,
    User,
    Group,
    GroupMember,
    Expense,
    ExpenseSplit,
)


def setup_test_database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestSessionLocal() as db:
        user1 = User(
            name="Group Member",
            email="member@example.com",
            password_hash="test",
        )
        user2 = User(
            name="Non Member",
            email="outsider@example.com",
            password_hash="test",
        )
        db.add_all([user1, user2])
        db.flush()

        group = Group(name="Authorization Test", created_by=user1.id)
        db.add(group)
        db.flush()

        db.add(
            GroupMember(
                group_id=group.id,
                user_id=user1.id,
            )
        )
        db.commit()

        group_id = group.id
        member_id = user1.id
        outsider_id = user2.id

    return engine, TestSessionLocal, group_id, member_id, outsider_id


def test_non_member_cannot_access_balances(monkeypatch):
    engine, TestSessionLocal, group_id, member_id, outsider_id = (
        setup_test_database()
    )

    monkeypatch.setattr(main, "SessionLocal", TestSessionLocal)
    monkeypatch.setattr(
        main,
        "get_current_user",
        lambda: None,
    )

    # Call the endpoint directly with an outsider as the current user.
    from fastapi import HTTPException

    with TestSessionLocal() as db:
        outsider = db.get(User, outsider_id)

    try:
        with pytest.raises(HTTPException) as exc:
            main.get_group_balances(
                group_id=group_id,
                current_user=outsider,
            )

        assert exc.value.status_code == 403
    finally:
        engine.dispose()


def test_non_member_cannot_access_settlement_suggestions(monkeypatch):
    engine, TestSessionLocal, group_id, member_id, outsider_id = (
        setup_test_database()
    )

    monkeypatch.setattr(main, "SessionLocal", TestSessionLocal)

    with TestSessionLocal() as db:
        outsider = db.get(User, outsider_id)

    try:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            main.get_settlement_suggestions(
                group_id=group_id,
                current_user=outsider,
            )

        assert exc.value.status_code == 403
    finally:
        engine.dispose()


def test_balances_endpoint_uses_expenses_and_splits(monkeypatch):
    engine, TestSessionLocal, group_id, member_id, outsider_id = (
        setup_test_database()
    )

    monkeypatch.setattr(main, "SessionLocal", TestSessionLocal)

    try:
        with TestSessionLocal() as db:
            # Find the existing group member and add two more members.
            outsider = db.get(User, outsider_id)

            db.add(
                GroupMember(
                    group_id=group_id,
                    user_id=outsider.id,
                )
            )

            user3 = User(
                name="Chai",
                email="chai@example.com",
                password_hash="test",
            )
            db.add(user3)
            db.flush()

            db.add(
                GroupMember(
                    group_id=group_id,
                    user_id=user3.id,
                )
            )
            db.flush()

            # Alice (member_id) pays Rs. 900.
            expense = Expense(
                group_id=group_id,
                paid_by=member_id,
                amount_paise=90000,
                description="Shared meal",
            )
            db.add(expense)
            db.flush()

            # Each of the three members owes Rs. 300.
            db.add_all([
                ExpenseSplit(
                    expense_id=expense.id,
                    user_id=member_id,
                    share_paise=30000,
                ),
                ExpenseSplit(
                    expense_id=expense.id,
                    user_id=outsider_id,
                    share_paise=30000,
                ),
                ExpenseSplit(
                    expense_id=expense.id,
                    user_id=user3.id,
                    share_paise=30000,
                ),
            ])
            db.commit()

            user3_id = user3.id
            alice = db.get(User, member_id)

        result = main.get_group_balances(
            group_id=group_id,
            current_user=alice,
        )

        balances = {
            item["user_id"]: item["balance_paise"]
            for item in result["balances"]
        }

        assert balances == {
            member_id: 60000,
            outsider_id: -30000,
            user3_id: -30000,
        }

        assert sum(balances.values()) == 0

    finally:
        engine.dispose()
