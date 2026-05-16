import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base
import enum

class UserRole(str,enum.Enum):
    admin = "admin"
    analyst = "analyst"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    email = Column(String(225),nullable=False)
    password_hash = Column(String(100),nullable=False)
    name = Column(String(100),nullable=False)
    org_id = Column(UUID(as_uuid=True),ForeignKey("organizations.id"),nullable=False)
    role = Column(Enum(UserRole),nullable=False,default=UserRole.analyst)
    created_at = Column(DateTime(timezone=True),server_default=func.now())