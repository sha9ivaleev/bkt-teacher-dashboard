import logging
from app.database import engine
from app.models.db_models import Base
from sqlalchemy import inspect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """Инициализация базы данных"""
    logger.info("="*50)
    logger.info("ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ")
    logger.info("="*50)
    
    try:
        # Проверяем существующие таблицы
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        logger.info(f"Существующие таблицы: {existing_tables}")
        
        # Создаем таблицы
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Таблицы успешно созданы/обновлены")
        
        # Проверяем созданные таблицы
        inspector = inspect(engine)
        new_tables = inspector.get_table_names()
        logger.info(f"Текущие таблицы: {new_tables}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при инициализации БД: {e}")
        raise

if __name__ == "__main__":
    init_database()