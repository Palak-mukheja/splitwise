
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from app import main
from app.models import Base, User, Group, GroupMember, Expense, ExpenseSplit
from app.schemas import ExpenseCreate


def test_expense_and_splits_rollback_together(monkeypatch):
    # Create a temporary, in-memory database for this test.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestSessionLocal() as db:
        user1 = User(
            name="Test User 1",
            email="test1@example.com",
            password_hash="test",
        )
        user2 = User(
            name="Test User 2",
            email="test2@example.com",
            password_hash="test",
        )
        db.add_all([user1, user2])
        db.flush()

        group = Group(name="Test Group", created_by=user1.id)
        db.add(group)
        db.flush()

        group_id = group.id
        user1_id = user1.id

        db.add_all([
            GroupMember(group_id=group_id, user_id=user1.id),
            GroupMember(group_id=group_id, user_id=user2.id),
        ])
        db.commit()

    # Make the second split insertion fail deliberately.
    original_add = Session.add
    split_attempts = 0

    def failing_add(self, instance, _warn=True):
        nonlocal split_attempts

        if isinstance(instance, ExpenseSplit):
            split_attempts += 1
            if split_attempts == 2:
                raise RuntimeError("Deliberate test failure")

        return original_add(self, instance, _warn=_warn)

    monkeypatch.setattr(main, "SessionLocal", TestSessionLocal)
    monkeypatch.setattr(Session, "add", failing_add)

    with TestSessionLocal() as db:
        current_user = db.get(User, user1_id)

    # The endpoint should fail, but roll back the transaction.
    with pytest.raises(RuntimeError, match="Deliberate test failure"):
        main.create_expense(
            group_id=group_id,
            expense=ExpenseCreate(
                amount_paise=100,
                description="Rollback test",
                paid_by=user1_id,
            ),
            current_user=current_user,
        )

    # Verify that neither the expense nor any splits were saved.
    with TestSessionLocal() as db:
        expense_count = db.scalar(
            select(func.count()).select_from(Expense)
        )
        split_count = db.scalar(
            select(func.count()).select_from(ExpenseSplit)
        )

        assert expense_count == 0
        assert split_count == 0

    engine.dispose()
