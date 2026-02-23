from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.db_models import Skill, User, TestItem
from app.schemas.pydantic_models import SkillCreate, SkillResponse
from app.services.bkt_engine import BKTEngine
from app.logger import logger
from jose import jwt
from app.config import SECRET_KEY, ALGORITHM

router = APIRouter(prefix="/skills", tags=["skills"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def skills_page(
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
        
        skills = db.query(Skill).filter_by(is_active=True).order_by(Skill.name).all()
        
        return templates.TemplateResponse(
            "skills_simple.html",
            {"request": request, "skills": skills, "user": user}
        )
    except Exception as e:
        logger.error(f"Ошибка загрузки страницы навыков: {e}")
        return RedirectResponse(url="/dashboard")

@router.get("/api", response_model=List[SkillResponse])
def get_skills(
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
        
        skills = db.query(Skill).filter_by(is_active=True).order_by(Skill.name).offset(skip).limit(limit).all()
        return skills
    except Exception as e:
        logger.error(f"Ошибка получения списка навыков: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при получении данных")

@router.post("/api", response_model=SkillResponse)
def create_skill(
    skill: SkillCreate,
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
            raise HTTPException(status_code=403, detail="Guests cannot create skills")
        
        existing = db.query(Skill).filter(Skill.name == skill.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Навык с таким названием уже существует")
        
        db_skill = Skill(
            name=skill.name,
            description=skill.description,
            p_learn=skill.p_learn,
            p_guess=skill.p_guess,
            p_slip=skill.p_slip,
            p_init=skill.p_init,
            created_by=current_user.id,
            is_active=True
        )
        db.add(db_skill)
        db.commit()
        db.refresh(db_skill)
        
        logger.info(f"Навык создан: {skill.name}")
        return db_skill
        
    except Exception as e:
        logger.error(f"Ошибка создания навыка: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка при создании навыка")

@router.put("/api/{skill_id}", response_model=SkillResponse)
def update_skill(
    skill_id: int,
    skill_update: SkillCreate,
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
            raise HTTPException(status_code=403, detail="Guests cannot update skills")
        
        skill = db.query(Skill).filter(Skill.id == skill_id).first()
        if not skill:
            raise HTTPException(status_code=404, detail="Навык не найден")
        
        skill.name = skill_update.name
        skill.description = skill_update.description
        skill.p_learn = skill_update.p_learn
        skill.p_guess = skill_update.p_guess
        skill.p_slip = skill_update.p_slip
        skill.p_init = skill_update.p_init
        
        db.commit()
        db.refresh(skill)
        
        logger.info(f"Навык обновлен: ID {skill_id}")
        return skill
        
    except Exception as e:
        logger.error(f"Ошибка обновления навыка {skill_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка при обновлении навыка")

@router.delete("/api/{skill_id}")
def delete_skill(
    skill_id: int,
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
            raise HTTPException(status_code=403, detail="Guests cannot delete skills")
        
        skill = db.query(Skill).filter(Skill.id == skill_id).first()
        if not skill:
            raise HTTPException(status_code=404, detail="Навык не найден")
        
        skill.is_active = False
        db.commit()
        
        logger.info(f"Навык деактивирован: ID {skill_id}")
        return {"message": "Навык успешно деактивирован"}
        
    except Exception as e:
        logger.error(f"Ошибка удаления навыка {skill_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка при удалении навыка")