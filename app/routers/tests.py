from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.models.db_models import Test, TestItem, Student, Skill, StudentAttempt, User
from app.services.bkt_engine import BKTEngine
from app.logger import logger
from jose import jwt
from app.config import SECRET_KEY, ALGORITHM

router = APIRouter(prefix="/tests", tags=["tests"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/input", response_class=HTMLResponse)
async def test_input_page(
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
        
        if user.role == "guest":
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "message": "У вас нет прав для ввода тестов", "user": user}
            )
        
        students = db.query(Student).order_by(Student.name).all()
        skills = db.query(Skill).filter_by(is_active=True).order_by(Skill.name).all()
        
        return templates.TemplateResponse(
            "tests_input_simple.html",
            {
                "request": request, 
                "students": students, 
                "skills": skills, 
                "user": user
            }
        )
    except Exception as e:
        logger.error(f"Ошибка загрузки страницы ввода тестов: {e}")
        return RedirectResponse(url="/dashboard")

@router.post("/api/create")
async def create_test(
    request: Request,
    db: Session = Depends(get_db)
):
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.replace("Bearer ", "")
    
    try:
        data = await request.json()
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        
        current_user = db.query(User).filter(User.username == username).first()
        if not current_user:
            raise HTTPException(status_code=401, detail="User not found")
        
        if current_user.role == "guest":
            raise HTTPException(status_code=403, detail="Guests cannot create tests")
        
        test = Test(
            test_date=datetime.now(),
            description=data.get("description", ""),
            created_by=current_user.id
        )
        db.add(test)
        db.flush()
        
        items = data.get("items", [])
        for idx, skill_id in enumerate(items, 1):
            test_item = TestItem(
                test_id=test.id,
                item_order=idx,
                skill_id=int(skill_id)
            )
            db.add(test_item)
        
        db.commit()
        logger.info(f"Тест создан: ID {test.id}")
        
        return {"test_id": test.id, "message": "Test created successfully"}
        
    except Exception as e:
        logger.error(f"Ошибка создания теста: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/save-results")
async def save_test_results(
    request: Request,
    db: Session = Depends(get_db)
):
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.replace("Bearer ", "")
    
    try:
        data = await request.json()
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        
        current_user = db.query(User).filter(User.username == username).first()
        if not current_user:
            raise HTTPException(status_code=401, detail="User not found")
        
        if current_user.role == "guest":
            raise HTTPException(status_code=403, detail="Guests cannot save results")
        
        test_id = data.get("test_id")
        if not test_id:
            raise HTTPException(status_code=400, detail="Missing test_id")
        
        test_items = db.query(TestItem).filter(TestItem.test_id == test_id).all()
        if not test_items:
            raise HTTPException(status_code=404, detail="Test has no items")
        
        test_items_dict = {item.item_order: item for item in test_items}
        results = data.get("results", {})
        
        attempts_count = 0
        for student_id, student_results in results.items():
            for item_idx, is_correct in student_results.items():
                item_idx_int = int(item_idx)
                
                if item_idx_int in test_items_dict:
                    attempt = StudentAttempt(
                        student_id=int(student_id),
                        test_item_id=test_items_dict[item_idx_int].id,
                        is_correct=is_correct,
                        score=1.0 if is_correct else 0.0
                    )
                    db.add(attempt)
                    attempts_count += 1
        
        db.commit()
        logger.info(f"Сохранено {attempts_count} попыток для теста {test_id}")
        
        bkt = BKTEngine(db)
        updated_count = bkt.process_test_results(test_id)
        
        return {
            "message": f"Results saved successfully. BKT updated {updated_count} records.",
            "updated_count": updated_count
        }
        
    except Exception as e:
        logger.error(f"Ошибка сохранения результатов: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/list")
def get_tests(
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
        
        tests = db.query(Test).order_by(Test.test_date.desc()).all()
        
        result = []
        for test in tests:
            items_count = db.query(TestItem).filter(TestItem.test_id == test.id).count()
            result.append({
                "id": test.id,
                "test_date": test.test_date,
                "description": test.description,
                "items_count": items_count,
                "created_at": test.created_at
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Ошибка получения списка тестов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения списка тестов")