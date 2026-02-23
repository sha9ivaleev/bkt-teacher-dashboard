from app.database import SessionLocal
from app.models.db_models import User, Skill, Student, Test
import sys

print("="*50)
print("ПРОВЕРКА БАЗЫ ДАННЫХ")
print("="*50)

try:
    db = SessionLocal()
    
    print("\n👥 ПОЛЬЗОВАТЕЛИ:")
    users = db.query(User).all()
    if users:
        for user in users:
            print(f"  - ID: {user.id}, Имя: {user.username}, Роль: {user.role}")
    else:
        print("  ❌ Пользователи не найдены")
    
    print("\n📚 НАВЫКИ:")
    skills = db.query(Skill).all()
    if skills:
        for skill in skills:
            print(f"  - {skill.name} (активен: {skill.is_active})")
    else:
        print("  ✅ Навыков нет (можно создать новые)")
    
    print("\n👨‍🎓 УЧЕНИКИ:")
    students = db.query(Student).all()
    if students:
        for student in students:
            print(f"  - {student.name} ({student.class_name})")
    else:
        print("  ✅ Учеников нет (можно создать новых)")
    
    print("\n📝 ТЕСТЫ:")
    tests = db.query(Test).all()
    if tests:
        for test in tests:
            print(f"  - {test.description} (дата: {test.test_date})")
    else:
        print("  ✅ Тестов нет (можно создать новые)")
    
    print("\n" + "="*50)
    print(f"✅ Всего записей: Пользователей: {len(users)}, Навыков: {len(skills)}, Учеников: {len(students)}, Тестов: {len(tests)}")
    
    db.close()
    
except Exception as e:
    print(f"\n❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    
input("\nНажмите Enter для выхода...")