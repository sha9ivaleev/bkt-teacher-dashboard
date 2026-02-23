import numpy as np
from app.services.bkt_engine import BKTEngine
from app.database import SessionLocal

# Тест формул BKT
print("="*50)
print("ТЕСТ BKT ФОРМУЛ")
print("="*50)

# Параметры
p_know = 0.5  # начальное знание
p_learn = 0.1  # вероятность выучить
p_guess = 0.2  # вероятность угадать
p_slip = 0.1   # вероятность ошибиться

print(f"Начальное знание: {p_know}")
print(f"Параметры: p_learn={p_learn}, p_guess={p_guess}, p_slip={p_slip}")
print()

# Правильный ответ
p_correct = p_know * (1 - p_slip) + (1 - p_know) * p_guess
p_know_correct = (p_know * (1 - p_slip)) / p_correct
p_know_correct = p_know_correct + (1 - p_know_correct) * p_learn

print(f"После ПРАВИЛЬНОГО ответа: {p_know_correct:.3f}")

# Неправильный ответ
p_wrong = p_know * p_slip + (1 - p_know) * (1 - p_guess)
p_know_wrong = (p_know * p_slip) / p_wrong
p_know_wrong = p_know_wrong + (1 - p_know_wrong) * p_learn

print(f"После НЕПРАВИЛЬНОГО ответа: {p_know_wrong:.3f}")
print()

# Проверка забывания
days = [1, 7, 30]
for day in days:
    forget = 0.2 + (0.5 - 0.2) * np.exp(-0.01 * day)
    print(f"Через {day} дней: {forget:.3f}")