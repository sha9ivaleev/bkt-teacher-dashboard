from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
from app.database import get_db
from app.models.db_models import Test, TestItem, Student, Skill, StudentAttempt, User
from app.schemas.pydantic_models import TestCreate, TestResultInput
from app.services.bkt_engine import BKTEngine
from jose import JWTError, jwt
from app.config import SECRET_KEY, ALGORITHM

# Создаем router
router = APIRouter(prefix="/tests", tags=["tests"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/input", response_class=HTMLResponse)
async def test_input_page(
    request: Request,
    token: str = None,
    db: Session = Depends(get_db)
):
    """Страница ввода результатов теста"""
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
        
        # Проверяем права (гости не могут вводить тесты)
        if user.role == "guest":
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "message": "У вас нет прав для ввода тестов", "user": user}
            )
        
        # Получаем списки учеников и навыков
        students = db.query(Student).all()
        skills = db.query(Skill).filter_by(is_active=True).all()
        
        return templates.TemplateResponse(
            "tests_input_simple.html",
            {
                "request": request, 
                "students": students, 
                "skills": skills, 
                "user": user
            }
        )
    except JWTError:
        return RedirectResponse(url="/")

@router.post("/api/create")
async def create_test(
    request: Request,
    db: Session = Depends(get_db)
):
    """Создание нового теста"""
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.replace("Bearer ", "")
    
    try:
        # Получаем данные из тела запроса
        data = await request.json()
        print(f"📥 Создание теста: {data}")
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        
        current_user = db.query(User).filter(User.username == username).first()
        if not current_user:
            raise HTTPException(status_code=401, detail="User not found")
        
        if current_user.role == "guest":
            raise HTTPException(status_code=403, detail="Guests cannot create tests")
        
        # Создаем тест
        test = Test(
            test_date=datetime.now(),
            description=data.get("description", ""),
            created_by=current_user.id
        )
        db.add(test)
        db.flush()
        
        # Создаем задания
        items = data.get("items", [])
        print(f"📋 Задания: {items}")
        
        for idx, skill_id in enumerate(items, 1):
            test_item = TestItem(
                test_id=test.id,
                item_order=idx,
                skill_id=int(skill_id)
            )
            db.add(test_item)
        
        db.commit()
        print(f"✅ Тест создан с ID: {test.id}")
        
        return {"test_id": test.id, "message": "Test created successfully"}
    except JWTError:
        print("❌ Ошибка JWT токена")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/save-results")
async def save_test_results(
    request: Request,
    db: Session = Depends(get_db)
):
    """Сохранение результатов теста и запуск BKT обновления"""
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.replace("Bearer ", "")
    
    try:
        # Получаем данные
        data = await request.json()
        print(f"📥 Получены данные для сохранения: {data}")
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        
        current_user = db.query(User).filter(User.username == username).first()
        if not current_user:
            raise HTTPException(status_code=401, detail="User not found")
        
        if current_user.role == "guest":
            raise HTTPException(status_code=403, detail="Guests cannot save results")
        
        # Проверяем test_id
        test_id = data.get("test_id")
        if not test_id:
            print("❌ Нет test_id в данных")
            raise HTTPException(status_code=400, detail="Missing test_id")
        
        # Получаем все задания теста
        test_items = db.query(TestItem).filter(TestItem.test_id == test_id).all()
        print(f"📋 Найдено заданий в тесте: {len(test_items)}")
        
        if not test_items:
            print(f"❌ Тест {test_id} не имеет заданий")
            raise HTTPException(status_code=404, detail="Test has no items")
        
        test_items_dict = {item.item_order: item for item in test_items}
        print(f"📋 Задания: {test_items_dict}")
        
        # Сохраняем результаты
        results = data.get("results", {})
        print(f"📋 Результаты учеников: {results}")
        
        attempts_count = 0
        for student_id, student_results in results.items():
            print(f"👤 Обработка ученика {student_id}")
            for item_idx, is_correct in student_results.items():
                item_idx_int = int(item_idx)
                print(f"  Задание {item_idx_int}: правильно={is_correct}")
                
                if item_idx_int in test_items_dict:
                    attempt = StudentAttempt(
                        student_id=int(student_id),
                        test_item_id=test_items_dict[item_idx_int].id,
                        is_correct=is_correct,
                        score=1.0 if is_correct else 0.0
                    )
                    db.add(attempt)
                    attempts_count += 1
                else:
                    print(f"  ⚠️ Задание {item_idx_int} не найдено в тесте")
        
        print(f"💾 Сохраняем {attempts_count} попыток в БД")
        db.commit()
        print("✅ Данные сохранены в БД")
        
        # Запускаем BKT обновление
        print("🔄 Запускаем BKT обновление...")
        bkt = BKTEngine(db)
        updated_count = bkt.process_test_results(test_id)
        print(f"✅ BKT обновлено {updated_count} записей")
        
        return {
            "message": f"Results saved successfully. BKT updated {updated_count} records.",
            "updated_count": updated_count
        }
    except JWTError:
        print("❌ Ошибка JWT токена")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/list")
def get_tests(
    request: Request,
    db: Session = Depends(get_db)
):
    """Получение списка тестов"""
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
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")