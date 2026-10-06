from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime
from sqlalchemy import ForeignKey
from sqlalchemy import func

class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__= "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str]=mapped_column(unique=True)
    name:Mapped[str]=mapped_column()
    password_hash:Mapped[str]=mapped_column()
    created_at:Mapped[datetime]=mapped_column(server_default=func.current_timestamp())
    
class Group(Base):
    __tablename__="groups"
    id:Mapped[int]=mapped_column(primary_key=True)
    name:Mapped[str]=mapped_column()
    created_by:Mapped[int]=mapped_column(ForeignKey("users.id"))
    
class GroupMember(Base):
    __tablename__="group_members"
    group_id:Mapped[int]=mapped_column(ForeignKey("groups.id"), primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey("users.id"), primary_key=True)
    joined_at:Mapped[datetime]=mapped_column(server_default=func.current_timestamp())

class Expenses(Base):
    __tablename__="expenses"
    id:Mapped[int]=mapped_column(primary_key=True)
    group_id:Mapped[int]=mapped_column(ForeignKey("groups.id"))
    paid_by:Mapped[int]=mapped_column(ForeignKey("users.id"))
    amount_paise: Mapped[int]=mapped_column()
    description: Mapped[str]=mapped_column()
    category:Mapped[str]=mapped_column()
    
class ExpenseSplit(Base):
    __tablename__="expense_splits"
    id: Mapped[int]=mapped_column(primary_key=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey("expenses.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    share_paise: Mapped[int]=mapped_column()

class Settlement(Base):
 __tablename__="settlements"
 id: Mapped[int]=mapped_column(primary_key=True)
 group_id:Mapped[int]=mapped_column(ForeignKey("groups.id"))
 from_user:Mapped[int]=mapped_column(ForeignKey("users.id"))
 to_user:Mapped[int]=mapped_column(ForeignKey("users.id"))
 amount_paise:Mapped[int]=mapped_column() 
 created_at:Mapped[datetime]=mapped_column(server_default=func.current_timestamp())