from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from app.routers import auth, students, skills, tests
from app.database import engine, get_db
from app.models import db_models
from app.config import SECRET_KEY, ALGORITHM
from app import auth as auth_module

# Создаем таблицы
db_models.Base.metadata.create_all(bind=engine)

# Создаем приложение
app = FastAPI(title="BKT Teacher Dashboard")

# Подключаем статику и шаблоны
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Подключаем роутеры
app.include_router(auth.router, prefix="/api")
app.include_router(students.router, prefix="")
app.include_router(skills.router, prefix="")
app.include_router(tests.router, prefix="")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Страница входа"""
    return templates.TemplateResponse("login_simple.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, token: str = None):
    """Главная страница после входа"""
    # Пробуем получить токен из разных мест
    if token:
        access_token = token
    else:
        # Из заголовка
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            access_token = auth_header.replace("Bearer ", "")
        else:
            # Из cookie
            access_token = request.cookies.get("access_token")
    
    if not access_token:
        return RedirectResponse(url="/")
    
    try:
        # Проверяем токен
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        
        if not username:
            return RedirectResponse(url="/")
            
        # Получаем пользователя из БД для отображения в шаблоне
        db = next(get_db())
        user = db.query(db_models.User).filter(db_models.User.username == username).first()
        db.close()
        
        if not user:
            return RedirectResponse(url="/")
        
        # Устанавливаем куку для будущих запросов
        response = templates.TemplateResponse("dashboard_simple.html", {
            "request": request,
            "user": user
        })
        response.set_cookie(key="access_token", value=access_token)
        return response
        
    except JWTError as e:
        print(f"JWT Error: {e}")
        return RedirectResponse(url="/")

@app.get("/logout")
async def logout():
    """Выход"""
    response = RedirectResponse(url="/")
    response.delete_cookie("access_token")
    return response

@app.on_event("startup")
async def startup_event():
    """Создаем тестовых пользователей"""
    db = next(get_db())
    try:
        # Учитель
        if not db.query(db_models.User).filter(db_models.User.username == "teacher").first():
            teacher = db_models.User(
                username="teacher",
                password_hash=auth_module.get_password_hash("teacher123"),
                role="teacher",
                is_active=True
            )
            db.add(teacher)
            print("✅ Учитель создан")
        
        # Гость
        if not db.query(db_models.User).filter(db_models.User.username == "guest").first():
            guest = db_models.User(
                username="guest",
                password_hash=auth_module.get_password_hash("guest123"),
                role="guest",
                is_active=True
            )
            db.add(guest)
            print("✅ Гость создан")
        
        db.commit()
        print("✅ Пользователи созданы")
    except Exception as e:
        print(f"❌ Ошибка при создании пользователей: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)