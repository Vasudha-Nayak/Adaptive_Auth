from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import User, SessionRecord
import auth

Base.metadata.create_all(bind=engine)

app = FastAPI()

# Allow the plain HTML/JS frontend (opened from file:// or any localhost port) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FAILED_ATTEMPTS_FOR_OTP = 2      # after this many failures, require OTP
FAILED_ATTEMPTS_FOR_LOCK = 5     # after this many failures, lock account
LOCK_DURATION_MINUTES = 15


class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class OtpVerifyRequest(BaseModel):
    username: str
    otp: str


@app.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(username=req.username, password_hash=auth.hash_password(req.password))
    db.add(user)
    db.commit()
    return {"message": "Registered successfully"}


@app.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid username or password")

    if user.locked_until and datetime.utcnow() < user.locked_until:
        remaining = int((user.locked_until - datetime.utcnow()).total_seconds())
        raise HTTPException(status_code=403, detail=f"Account locked. Try again in {remaining}s")

    if not auth.verify_password(req.password, user.password_hash):
        user.failed_attempts += 1

        if user.failed_attempts >= FAILED_ATTEMPTS_FOR_LOCK:
            user.locked_until = datetime.utcnow() + timedelta(minutes=LOCK_DURATION_MINUTES)
            db.commit()
            raise HTTPException(status_code=403, detail="Too many failed attempts. Account locked.")

        db.commit()
        raise HTTPException(status_code=400, detail="Invalid username or password")

    # password correct — decide auth level based on failed_attempts so far
    if user.failed_attempts >= FAILED_ATTEMPTS_FOR_OTP:
        otp = auth.generate_otp()
        user.otp_code = otp
        user.otp_expiry = auth.otp_expiry_time()
        db.commit()
        # DEMO MODE: returning OTP directly instead of sending via SMS/email
        return {"status": "otp_required", "demo_otp": otp}

    # low-risk: normal login, issue session key directly
    user.failed_attempts = 0
    db.commit()

    session_key = auth.generate_session_key()
    db.add(SessionRecord(user_id=user.id, session_key=session_key, created_at=datetime.utcnow()))
    db.commit()

    return {"status": "granted", "session_key": session_key}


@app.post("/verify-otp")
def verify_otp(req: OtpVerifyRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid request")

    if not auth.is_otp_valid(user.otp_code, req.otp, user.otp_expiry):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    user.failed_attempts = 0
    user.otp_code = None
    user.otp_expiry = None
    db.commit()

    session_key = auth.generate_session_key()
    db.add(SessionRecord(user_id=user.id, session_key=session_key, created_at=datetime.utcnow()))
    db.commit()

    return {"status": "granted", "session_key": session_key}


@app.get("/health")
def health():
    return {"status": "ok"}