from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app import auth
from app.database import get_db
from app.schemas.pydantic_models import UserCreate, UserResponse, Token
from app.models.db_models import User
from app.config import ACCESS_TOKEN_EXPIRE_MINUTES
from app.deps import AuthDeps  # Импортируем из deps.py
from app.logger import logger

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Имя пользователя уже занято")
    
    hashed_password = auth.get_password_hash(user.password)
    db_user = User(
        username=user.username,
        password_hash=hashed_password,
        email=user.email,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    logger.info(f"Зарегистрирован новый пользователь: {user.username}")
    return db_user

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        logger.warning(f"Неудачная попытка входа: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    logger.info(f"Успешный вход: {user.username}")
    return {"access_token": access_token, "token_type": "bearer", "role": user.role}

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(AuthDeps.get_current_active_user)):  # Исправлено!
    return current_user