from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app import auth
from app.database import get_db
from app.schemas.pydantic_models import UserCreate, UserResponse, Token
from app.models.db_models import User
from app.config import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """Регистрация нового пользователя"""
    # Проверяем, существует ли пользователь
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Создаем нового пользователя
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
    
    return db_user

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Вход в систему"""
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer", "role": user.role}

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(auth.get_current_active_user)):
    """Получение информации о текущем пользователе"""
    return current_user

# Создаем тестового пользователя
@router.post("/create-test-users")
def create_test_users(db: Session = Depends(get_db)):
    """Создание тестовых пользователей"""
    # Проверяем, есть ли уже учитель
    teacher = db.query(User).filter(User.username == "teacher").first()
    if not teacher:
        hashed_password = auth.get_password_hash("teacher123")
        teacher = User(
            username="teacher",
            password_hash=hashed_password,
            email="teacher@school.com",
            role="teacher"
        )
        db.add(teacher)
    
    # Проверяем, есть ли уже гость
    guest = db.query(User).filter(User.username == "guest").first()
    if not guest:
        hashed_password = auth.get_password_hash("guest123")
        guest = User(
            username="guest",
            password_hash=hashed_password,
            email="guest@school.com",
            role="guest"
        )
        db.add(guest)
    
    db.commit()
    
    return {"message": "Test users created: teacher/teacher123, guest/guest123"}
