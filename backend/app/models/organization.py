import uuid
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)

    name = Column(String(100), nullable=False)

    invite_code = Column(String(20), unique=True,nullable=False)

    created_at = Column(DateTime(timezone=True),server_default=func.now())

    