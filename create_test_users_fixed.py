import logging
from app.database import SessionLocal
from app.models.db_models import User
from passlib.context import CryptContext
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем свой CryptContext без лишних проверок
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Хеширование пароля с проверкой длины"""
    # bcrypt требует пароль не длиннее 72 байт
    if len(password.encode('utf-8')) > 72:
        password = password[:50]  # обрезаем до безопасной длины
    return pwd_context.hash(password)

def create_test_users():
    """Создание тестовых пользователей"""
    logger.info("="*50)
    logger.info("СОЗДАНИЕ ТЕСТОВЫХ ПОЛЬЗОВАТЕЛЕЙ")
    logger.info("="*50)
    
    # Проверяем SECRET_KEY
    secret_key = os.getenv("SECRET_KEY", "")
    if secret_key == "your-super-secret-key-at-least-32-chars":
        logger.warning("⚠️  Используется дефолтный SECRET_KEY. Измените его в .env!")
    
    db = SessionLocal()
    try:
        # Удаляем старых пользователей (опционально)
        # db.query(User).delete()
        # db.commit()
        
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
        else:
            logger.info("👤 Учитель уже существует")
        
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
        else:
            logger.info("👤 Гость уже существует")
        
        db.commit()
        
        # Проверяем созданных пользователей
        users = db.query(User).all()
        logger.info(f"📊 Всего пользователей в БД: {len(users)}")
        for user in users:
            logger.info(f"  - {user.username} ({user.role})")
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_users()