from app.database import SessionLocal
from app.models.db_models import User
from app.auth import get_password_hash
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_users():
    db = SessionLocal()
    try:
        # Удаляем существующих пользователей (если есть)
        db.query(User).delete()
        db.commit()
        
        # Создаем учителя
        teacher = User(
            username="teacher",
            password_hash=get_password_hash("teacher123"),
            email="teacher@school.com",
            role="teacher",
            is_active=True
        )
        db.add(teacher)
        
        # Создаем гостя
        guest = User(
            username="guest",
            password_hash=get_password_hash("guest123"),
            email="guest@school.com",
            role="guest",
            is_active=True
        )
        db.add(guest)
        
        db.commit()
        
        # Проверяем
        teacher_check = db.query(User).filter(User.username == "teacher").first()
        guest_check = db.query(User).filter(User.username == "guest").first()
        
        if teacher_check and guest_check:
            logger.info("✅ Тестовые пользователи успешно созданы!")
            logger.info(f"Teacher: {teacher_check.username}, Role: {teacher_check.role}")
            logger.info(f"Guest: {guest_check.username}, Role: {guest_check.role}")
        else:
            logger.error("❌ Пользователи не создались")
            
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_users()