from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt

from app.routers import auth, students, skills, tests
from app.database import engine, get_db
from app.models import db_models
from app.config import SECRET_KEY, ALGORITHM
from app.logger import logger

db_models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="BKT Teacher Dashboard")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(auth.router, prefix="/api")
app.include_router(students.router, prefix="")
app.include_router(skills.router, prefix="")
app.include_router(tests.router, prefix="")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    logger.info("Открыта страница входа")
    return templates.TemplateResponse("login_simple.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, token: str = None):
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
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        
        if not username:
            return RedirectResponse(url="/")
            
        db = next(get_db())
        user = db.query(db_models.User).filter(db_models.User.username == username).first()
        db.close()
        
        if not user:
            return RedirectResponse(url="/")
        
        logger.info(f"Успешный вход: {username}")
        
        response = templates.TemplateResponse("dashboard_simple.html", {
            "request": request,
            "user": user
        })
        response.set_cookie(key="access_token", value=access_token)
        return response
        
    except JWTError as e:
        logger.error(f"Ошибка JWT: {e}")
        return RedirectResponse(url="/")

@app.get("/logout")
async def logout():
    logger.info("Выход из системы")
    response = RedirectResponse(url="/")
    response.delete_cookie("access_token")
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)