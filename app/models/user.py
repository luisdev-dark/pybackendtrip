from sqlalchemy import Column, String, Boolean, Enum
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.models.base import Base
import enum

class UserRole(str, enum.Enum):
    passenger = "passenger"
    driver = "driver"
    admin = "admin"

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "app"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role = Column(Enum(UserRole, name="user_role", schema="app"), nullable=False, default=UserRole.passenger)
    full_name = Column(String, nullable=False)
    phone_e164 = Column(String, nullable=False, unique=True)
    is_active = Column(Boolean, nullable=False, default=True)
