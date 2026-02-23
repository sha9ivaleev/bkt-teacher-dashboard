from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse  # Добавлен RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List
from app import auth
from app.database import get_db
from app.models.db_models import Student, User
from app.schemas.pydantic_models import StudentCreate, StudentResponse
from app.services.bkt_engine import BKTEngine
from jose import JWTError, jwt
from app.config import SECRET_KEY, ALGORITHM

router = APIRouter(prefix="/students", tags=["students"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def students_page(
    request: Request,
    token: str = None,
    db: Session = Depends(get_db)
):
    """Страница со списком учеников"""
    # Проверяем токен
    if token:
        access_token = token
    else:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            access_token = auth_header.replace("Bearer ", "")
        else:
            access_token = request.cookies.get("access_token")
    
    if not access_token:
        return RedirectResponse(url="/")
    
    try:
        # Проверяем токен
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        
        if not username:
            return RedirectResponse(url="/")
        
        # Получаем пользователя
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return RedirectResponse(url="/")
        
        # Отдаем простой шаблон
        return templates.TemplateResponse(
            "students_simple.html",
            {"request": request, "user": user}
        )
    except JWTError:
        return RedirectResponse(url="/")

@router.get("/mastery", response_class=HTMLResponse)
async def mastery_table_page(
    request: Request,
    token: str = None,
    db: Session = Depends(get_db)
):
    """Страница с таблицей освоения навыков"""
    # Проверяем токен
    if token:
        access_token = token
    else:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            access_token = auth_header.replace("Bearer ", "")
        else:
            access_token = request.cookies.get("access_token")
    
    if not access_token:
        return RedirectResponse(url="/")
    
    try:
        # Проверяем токен
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        
        if not username:
            return RedirectResponse(url="/")
        
        # Получаем пользователя
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return RedirectResponse(url="/")
        
        # Получаем данные для таблицы освоения
        bkt = BKTEngine(db)
        students, skills, matrix = bkt.get_mastery_table()
        
        # Отдаем шаблон
        return templates.TemplateResponse(
            "mastery_simple.html",  # Создадим этот шаблон
            {
                "request": request,
                "students": students,
                "skills": skills,
                "matrix": matrix,
                "user": user
            }
        )
    except JWTError:
        return RedirectResponse(url="/")

@router.get("/api/mastery")
async def get_mastery_data(
    request: Request,
    db: Session = Depends(get_db)
):
    """API для получения данных таблицы освоения"""
    # Проверяем токен из заголовка
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.replace("Bearer ", "")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        bkt = BKTEngine(db)
        students, skills, matrix = bkt.get_mastery_table()
        
        return {
            "students": students,
            "skills": skills,
            "matrix": matrix
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/api", response_model=StudentResponse)
def create_student(
    student: StudentCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Создание нового ученика"""
    # Проверяем токен
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.replace("Bearer ", "")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        
        # Получаем пользователя
        current_user = db.query(User).filter(User.username == username).first()
        if not current_user:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Проверяем права
        if current_user.role == "guest":
            raise HTTPException(status_code=403, detail="Guests cannot create students")
        
        db_student = Student(
            name=student.name,
            class_name=student.class_name,
            created_by=current_user.id
        )
        db.add(db_student)
        db.commit()
        db.refresh(db_student)
        
        return db_student
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/api", response_model=List[StudentResponse])
def get_students(
    request: Request,
    db: Session = Depends(get_db)
):
    """Получение списка всех учеников"""
    # Проверяем токен
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.replace("Bearer ", "")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        students = db.query(Student).all()
        return students
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.delete("/api/{student_id}")
def delete_student(
    student_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Удаление ученика"""
    # Проверяем токен
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.replace("Bearer ", "")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        
        # Получаем пользователя
        current_user = db.query(User).filter(User.username == username).first()
        if not current_user:
            raise HTTPException(status_code=401, detail="User not found")
        
        if current_user.role == "guest":
            raise HTTPException(status_code=403, detail="Guests cannot delete students")
        
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        db.delete(student)
        db.commit()
        
        return {"message": "Student deleted successfully"}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")