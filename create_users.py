# create_users.py
from app.database import SessionLocal
from app.models.db_models import User
from app.auth import get_password_hash

db = SessionLocal()

# Создаем учителя
teacher = User(
    username="teacher",
    password_hash=get_password_hash("teacher123"),
    role="teacher",
    is_active=True
)
db.add(teacher)

# Создаем гостя
guest = User(
    username="guest",
    password_hash=get_password_hash("guest123"),
    role="guest",
    is_active=True
)
db.add(guest)

db.commit()
db.close()

print("✅ Учитель и гость созданы!")
print("   teacher / teacher123")
print("   guest / guest123")