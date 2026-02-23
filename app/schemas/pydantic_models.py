from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, List, Dict, Any

# Схемы для пользователей
class UserBase(BaseModel):
    username: str
    email: Optional[str] = None
    role: str = "teacher"

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

# Схемы для учеников
class StudentBase(BaseModel):
    name: str
    class_name: Optional[str] = None

class StudentCreate(StudentBase):
    pass

class StudentResponse(StudentBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Схемы для навыков
class SkillBase(BaseModel):
    name: str
    description: Optional[str] = None
    p_learn: float = 0.15
    p_guess: float = 0.20
    p_slip: float = 0.10
    p_init: float = 0.20

class SkillCreate(SkillBase):
    pass

class SkillResponse(SkillBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Схемы для тестов
class TestItemInput(BaseModel):
    skill_id: int

class TestCreate(BaseModel):
    description: Optional[str] = None
    items: List[int]

class TestResultInput(BaseModel):
    test_id: int
    results: Dict[str, Dict[str, bool]]

# Схемы для таблицы освоения
class MasteryTableResponse(BaseModel):
    students: List[Dict[str, Any]]
    skills: List[Dict[str, Any]]
    matrix: List[Dict[str, Any]]