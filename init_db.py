from app.database import engine
from app.models.db_models import Base

print("Создание таблиц в базе данных...")
Base.metadata.create_all(bind=engine)
print("✅ Таблицы успешно созданы!")