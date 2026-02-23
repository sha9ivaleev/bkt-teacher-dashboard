import logging
from app.database import SessionLocal
from app.models.db_models import User
from app.auth import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_users_safe():
    """Безопасное создание пользователей (без удаления существующих)"""
    logger.info("="*50)
    logger.info("БЕЗОПАСНОЕ СОЗДАНИЕ ПОЛЬЗОВАТЕЛЕЙ")
    logger.info("="*50)
    
    db = SessionLocal()
    try:
        # Проверяем и создаем учителя, если его нет
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
            logger.info(f"👤 Учитель уже существует (ID: {teacher.id})")
        
        # Проверяем и создаем гостя, если его нет
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
            logger.info(f"👤 Гость уже существует (ID: {guest.id})")
        
        db.commit()
        
        # Показываем всех пользователей
        users = db.query(User).all()
        logger.info(f"📊 Всего пользователей в БД: {len(users)}")
        for user in users:
            logger.info(f"  - ID: {user.id}, Имя: {user.username}, Роль: {user.role}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_users_safe()