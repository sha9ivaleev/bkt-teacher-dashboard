from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.db_models import Skill, User
from app.schemas.pydantic_models import SkillCreate, SkillResponse
from app.services.bkt_engine import BKTEngine
from jose import JWTError, jwt
from app.config import SECRET_KEY, ALGORITHM

router = APIRouter(prefix="/skills", tags=["skills"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def skills_page(
    request: Request,
    token: str = None,
    db: Session = Depends(get_db)
):
    """Страница управления навыками"""
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
        
        # Получаем список навыков
        skills = db.query(Skill).filter_by(is_active=True).all()
        
        return templates.TemplateResponse(
            "skills_simple.html",
            {"request": request, "skills": skills, "user": user}
        )
    except JWTError:
        return RedirectResponse(url="/")

@router.get("/api", response_model=List[SkillResponse])
def get_skills(
    request: Request,
    db: Session = Depends(get_db)
):
    """Получение списка всех навыков"""
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.replace("Bearer ", "")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        skills = db.query(Skill).filter_by(is_active=True).all()
        return skills
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/api", response_model=SkillResponse)
def create_skill(
    skill: SkillCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Создание нового навыка"""
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
            raise HTTPException(status_code=403, detail="Guests cannot create skills")
        
        # Проверяем, существует ли уже навык с таким именем
        existing = db.query(Skill).filter(Skill.name == skill.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Skill with this name already exists")
        
        db_skill = Skill(
            name=skill.name,
            description=skill.description,
            p_learn=skill.p_learn,
            p_guess=skill.p_guess,
            p_slip=skill.p_slip,
            p_init=skill.p_init,
            created_by=current_user.id
        )
        db.add(db_skill)
        db.commit()
        db.refresh(db_skill)
        
        return db_skill
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.put("/api/{skill_id}", response_model=SkillResponse)
def update_skill(
    skill_id: int,
    skill_update: SkillCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Обновление параметров навыка"""
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
            raise HTTPException(status_code=403, detail="Guests cannot update skills")
        
        skill = db.query(Skill).filter(Skill.id == skill_id).first()
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")
        
        skill.name = skill_update.name
        skill.description = skill_update.description
        skill.p_learn = skill_update.p_learn
        skill.p_guess = skill_update.p_guess
        skill.p_slip = skill_update.p_slip
        skill.p_init = skill_update.p_init
        
        db.commit()
        db.refresh(skill)
        
        return skill
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.delete("/api/{skill_id}")
def delete_skill(
    skill_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Удаление навыка (мягкое удаление)"""
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
            raise HTTPException(status_code=403, detail="Guests cannot delete skills")
        
        skill = db.query(Skill).filter(Skill.id == skill_id).first()
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")
        
        skill.is_active = False
        db.commit()
        
        return {"message": "Skill deactivated successfully"}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")