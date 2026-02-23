from app.database import SessionLocal
from app.models.db_models import User
from app.auth import verify_password

def check_users():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print(f"Найдено пользователей: {len(users)}")
        
        for user in users:
            print(f"Username: {user.username}, Role: {user.role}, Active: {user.is_active}")
            
            # Проверяем пароль для тестовых пользователей
            if user.username == "teacher":
                password_valid = verify_password("teacher123", user.password_hash)
                print(f"  Teacher password valid: {password_valid}")
            elif user.username == "guest":
                password_valid = verify_password("guest123", user.password_hash)
                print(f"  Guest password valid: {password_valid}")
                
    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_users()