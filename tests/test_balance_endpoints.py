
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
import pytest 
from app import main
from app.models import Base, User, Group, GroupMember


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
