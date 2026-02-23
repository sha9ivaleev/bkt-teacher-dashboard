import requests
import json

# Базовый URL
base_url = "http://127.0.0.1:8000"

def test_login(username, password):
    """Тестирование входа"""
    print(f"\n🔐 Тестирование входа: {username}")
    
    # Данные для входа
    data = {
        "username": username,
        "password": password
    }
    
    try:
        # Отправляем запрос
        response = requests.post(
            f"{base_url}/api/auth/login",
            data=data,  # Используем data, не json!
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Успех! Токен получен")
            print(f"Роль: {result.get('role')}")
            print(f"Токен: {result.get('access_token')[:20]}...")
            return result.get('access_token')
        else:
            print(f"❌ Ошибка: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Исключение: {e}")
        return None

def test_protected_endpoint(token, endpoint):
    """Тестирование защищенного эндпоинта"""
    print(f"\n🔒 Тестирование {endpoint}")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{base_url}{endpoint}", headers=headers)
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ Доступ разрешен")
            data = response.json()
            print(f"Получено данных: {len(data) if isinstance(data, list) else 'объект'}")
        else:
            print(f"❌ Ошибка: {response.text}")
            
    except Exception as e:
        print(f"❌ Исключение: {e}")

# Тестируем
print("="*50)
print("ТЕСТИРОВАНИЕ АУТЕНТИФИКАЦИИ")
print("="*50)

# Тестируем учителя
teacher_token = test_login("teacher", "teacher123")

# Тестируем гостя
guest_token = test_login("guest", "guest123")

# Если учитель залогинился, проверяем доступ к API
if teacher_token:
    test_protected_endpoint(teacher_token, "/students/api")
    test_protected_endpoint(teacher_token, "/skills/api")