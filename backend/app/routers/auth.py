from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from .. import models, schemas, auth, billing, audit
from ..database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.UserOut, status_code=201)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == payload.email).first():
        audit.record("register", status="failed", meta={"email": payload.email, "why": "exists"})
        raise HTTPException(status_code=400, detail="Email already registered")
    user = models.User(
        email=payload.email,
        hashed_password=auth.hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    db.flush()                       # assign user.id before ledger entry
    billing.grant_signup_credits(db, user)
    db.commit()
    db.refresh(user)
    audit.record("register", user_id=user.id, meta={"email": user.email, "plan": user.plan})
    return user


@router.post("/login", response_model=schemas.Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form.username).first()
    if not user or not auth.verify_password(form.password, user.hashed_password):
        audit.record("login_failed", status="failed",
                     user_id=user.id if user else None, meta={"email": form.username})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad credentials")
    audit.record("login", user_id=user.id, meta={"email": user.email})
    return schemas.Token(access_token=auth.create_access_token(user.email))
