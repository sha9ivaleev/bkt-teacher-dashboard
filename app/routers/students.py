from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.db_models import Student, User
from app.schemas.pydantic_models import StudentCreate, StudentResponse
from app.services.bkt_engine import BKTEngine
from app.deps import AuthDeps
from app.logger import logger
from jose import jwt
from app.config import SECRET_KEY, ALGORITHM

router = APIRouter(prefix="/students", tags=["students"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def students_page(
    request: Request,
    token: str = None,
    db: Session = Depends(get_db)
):
    try:
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
        
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        
        if not username:
            return RedirectResponse(url="/")
        
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return RedirectResponse(url="/")
        
        students = db.query(Student).order_by(Student.name).all()
        
        return templates.TemplateResponse(
            "students_simple.html",
            {"request": request, "user": user, "students": students}
        )
    except Exception as e:
        logger.error(f"Ошибка загрузки страницы учеников: {e}")
        return RedirectResponse(url="/dashboard")

@router.get("/mastery", response_class=HTMLResponse)
async def mastery_table_page(
    request: Request,
    token: str = None,
    db: Session = Depends(get_db)
):
    try:
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
        
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        
        if not username:
            return RedirectResponse(url="/")
        
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return RedirectResponse(url="/")
        
        bkt = BKTEngine(db)
        students, skills, matrix = bkt.get_mastery_table()
        
        return templates.TemplateResponse(
            "mastery_simple.html",
            {
                "request": request,
                "students": students,
                "skills": skills,
                "matrix": matrix,
                "user": user
            }
        )
    except Exception as e:
        logger.error(f"Ошибка загрузки таблицы освоения: {e}")
        return RedirectResponse(url="/dashboard")

@router.get("/api/mastery")
async def get_mastery_data(
    request: Request,
    db: Session = Depends(get_db)
):
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
    except Exception as e:
        logger.error(f"Ошибка получения данных освоения: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@router.post("/api", response_model=StudentResponse)
def create_student(
    student: StudentCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.replace("Bearer ", "")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        
        current_user = db.query(User).filter(User.username == username).first()
        if not current_user:
            raise HTTPException(status_code=401, detail="User not found")
        
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
        
        logger.info(f"Ученик создан: {student.name}")
        return db_student
        
    except Exception as e:
        logger.error(f"Ошибка создания ученика: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка при создании ученика")

@router.get("/api", response_model=List[StudentResponse])
def get_students(
    request: Request,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.replace("Bearer ", "")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        students = db.query(Student).order_by(Student.name).offset(skip).limit(limit).all()
        return students
    except Exception as e:
        logger.error(f"Ошибка получения списка учеников: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при получении данных")

@router.delete("/api/{student_id}")
def delete_student(
    student_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.replace("Bearer ", "")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        
        current_user = db.query(User).filter(User.username == username).first()
        if not current_user:
            raise HTTPException(status_code=401, detail="User not found")
        
        if current_user.role == "guest":
            raise HTTPException(status_code=403, detail="Guests cannot delete students")
        
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Ученик не найден")
        
        db.delete(student)
        db.commit()
        
        logger.info(f"Ученик удален: ID {student_id}")
        return {"message": "Ученик успешно удален"}
        
    except Exception as e:
        logger.error(f"Ошибка удаления ученика {student_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка при удалении ученика")