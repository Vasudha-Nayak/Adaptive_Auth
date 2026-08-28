from sqlalchemy import Column, Integer, String, DateTime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    failed_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)

    otp_code = Column(String, nullable=True)
    otp_expiry = Column(DateTime, nullable=True)

class SessionRecord(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    session_key = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)