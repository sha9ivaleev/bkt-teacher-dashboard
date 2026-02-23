import logging
from app.database import SessionLocal
from app.models.db_models import User
from app.auth import get_password_hash
from app.config import SECRET_KEY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_users():
    """Создание тестовых пользователей (ТОЛЬКО ДЛЯ РАЗРАБОТКИ)"""
    logger.info("="*50)
    logger.info("СОЗДАНИЕ ТЕСТОВЫХ ПОЛЬЗОВАТЕЛЕЙ")
    logger.info("="*50)
    
    # Проверяем, что не в продакшене
    if SECRET_KEY == "your-super-secret-key-at-least-32-chars":
        logger.warning("⚠️  Используется дефолтный SECRET_KEY. Измените его в .env!")
    
    db = SessionLocal()
    try:
        # Учитель
        teacher = db.query(User).filter(User.username == "teacher").first()
        if not teacher:
            teacher = User(
                username="teacher",
                password_hash=get_password_hash("teacher123"),
                role="teacher",
                is_active=True
            )
            db.add(teacher)
            logger.info("✅ Учитель создан")
        
        # Гость
        guest = db.query(User).filter(User.username == "guest").first()
        if not guest:
            guest = User(
                username="guest",
                password_hash=get_password_hash("guest123"),
                role="guest",
                is_active=True
            )
            db.add(guest)
            logger.info("✅ Гость создан")
        
        db.commit()
        logger.info("✅ Тестовые пользователи готовы")
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_users()