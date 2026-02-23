from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    """Пользователи системы (учителя)"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100))
    role = Column(String(20), default="teacher")  # teacher, admin, guest
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    students = relationship("Student", back_populates="created_by_user")
    skills = relationship("Skill", back_populates="created_by_user")
    tests = relationship("Test", back_populates="created_by_user")

class Student(Base):
    """Ученики"""
    __tablename__ = "students"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    class_name = Column(String(20))  # например, "9А"
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    created_by_user = relationship("User", back_populates="students")
    attempts = relationship("StudentAttempt", back_populates="student")
    knowledge_states = relationship("StudentKnowledgeState", back_populates="student")
    knowledge_history = relationship("KnowledgeHistory", back_populates="student")

class Skill(Base):
    """Навыки (Knowledge Components)"""
    __tablename__ = "skills"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    
    # Параметры BKT
    p_learn = Column(Float, default=0.15)  # P(T)
    p_guess = Column(Float, default=0.20)  # P(G)
    p_slip = Column(Float, default=0.10)   # P(S)
    p_init = Column(Float, default=0.20)   # P(L0)
    
    created_by = Column(Integer, ForeignKey("users.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    created_by_user = relationship("User", back_populates="skills")
    test_items = relationship("TestItem", back_populates="skill")
    knowledge_states = relationship("StudentKnowledgeState", back_populates="skill")
    knowledge_history = relationship("KnowledgeHistory", back_populates="skill")

class Test(Base):
    """Тесты (сессии тестирования)"""
    __tablename__ = "tests"
    
    id = Column(Integer, primary_key=True, index=True)
    test_date = Column(DateTime(timezone=True), nullable=False)
    description = Column(String(200))
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    created_by_user = relationship("User", back_populates="tests")
    items = relationship("TestItem", back_populates="test", cascade="all, delete-orphan")

class TestItem(Base):
    """Задания в тесте"""
    __tablename__ = "test_items"
    
    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey("tests.id", ondelete="CASCADE"))
    item_order = Column(Integer, nullable=False)  # порядковый номер
    skill_id = Column(Integer, ForeignKey("skills.id"))
    max_score = Column(Float, default=1.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    test = relationship("Test", back_populates="items")
    skill = relationship("Skill", back_populates="test_items")
    attempts = relationship("StudentAttempt", back_populates="test_item")
    
    __table_args__ = (UniqueConstraint('test_id', 'item_order', name='unique_test_item_order'),)

class StudentAttempt(Base):
    """Результаты учеников"""
    __tablename__ = "student_attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    test_item_id = Column(Integer, ForeignKey("test_items.id"))
    is_correct = Column(Boolean, nullable=False)
    score = Column(Float, default=0.0)  # 0 или 1 для бинарной оценки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    student = relationship("Student", back_populates="attempts")
    test_item = relationship("TestItem", back_populates="attempts")
    
    __table_args__ = (UniqueConstraint('student_id', 'test_item_id', name='unique_student_attempt'),)

class StudentKnowledgeState(Base):
    """Текущее состояние знаний учеников (кеш BKT)"""
    __tablename__ = "student_knowledge_states"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    skill_id = Column(Integer, ForeignKey("skills.id"))
    probability_knowing = Column(Float, default=0.2)  # P(L_n)
    total_attempts = Column(Integer, default=0)
    correct_attempts = Column(Integer, default=0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Связи
    student = relationship("Student", back_populates="knowledge_states")
    skill = relationship("Skill", back_populates="knowledge_states")
    
    __table_args__ = (UniqueConstraint('student_id', 'skill_id', name='unique_student_skill'),)

class KnowledgeHistory(Base):
    """История изменений знаний (для графиков)"""
    __tablename__ = "knowledge_history"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    skill_id = Column(Integer, ForeignKey("skills.id"))
    probability = Column(Float)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    student = relationship("Student", back_populates="knowledge_history")
    skill = relationship("Skill", back_populates="knowledge_history") 
