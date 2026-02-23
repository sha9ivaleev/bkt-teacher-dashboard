import numpy as np
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Optional, List, Tuple
import logging
from app.models.db_models import (
    Student, Skill, StudentAttempt, TestItem,
    StudentKnowledgeState, KnowledgeHistory
)
from app.config import DEFAULT_BKT_PARAMS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BKTEngine:
    """
    Bayesian Knowledge Tracing Engine с поддержкой забывания
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.forgetting_rate = DEFAULT_BKT_PARAMS["forgetting_rate"]
    
    def _apply_forgetting(self, probability: float, days_passed: float) -> float:
        """
        Применяет эффект забывания к вероятности знания
        Используется экспоненциальное затухание
        """
        if days_passed <= 0:
            return probability
        
        # Чем больше дней прошло, тем сильнее забывание
        decay = np.exp(-self.forgetting_rate * days_passed)
        # Знание не может упасть ниже начального уровня
        min_probability = DEFAULT_BKT_PARAMS["p_init"]
        
        new_probability = min_probability + (probability - min_probability) * decay
        return max(min_probability, min(probability, new_probability))
    
    def get_current_knowledge(self, student_id: int, skill_id: int) -> float:
        """
        Получает текущую вероятность знания с учетом забывания
        """
        state = self.db.query(StudentKnowledgeState).filter_by(
            student_id=student_id, skill_id=skill_id
        ).first()
        
        if not state:
            skill = self.db.query(Skill).get(skill_id)
            return skill.p_init if skill else DEFAULT_BKT_PARAMS["p_init"]
        
        # Исправление: делаем оба времени наивными (без часового пояса)
        if state.last_updated.tzinfo is not None:
            # Если last_updated с часовым поясом, убираем его
            last_updated = state.last_updated.replace(tzinfo=None)
        else:
            last_updated = state.last_updated
        
        # Рассчитываем дни с последнего обновления
        days_passed = (datetime.now() - last_updated).days
        return self._apply_forgetting(state.probability_knowing, days_passed)
    
    def update_from_attempt(self, 
                           student_id: int, 
                           skill_id: int, 
                           is_correct: bool,
                           attempt_date: Optional[datetime] = None) -> float:
        """
        Обновляет знание на основе одной попытки
        """
        if attempt_date is None:
            attempt_date = datetime.now()
        
        # Убираем часовой пояс, если он есть
        if attempt_date.tzinfo is not None:
            attempt_date = attempt_date.replace(tzinfo=None)
        
        # Получаем текущее состояние
        state = self.db.query(StudentKnowledgeState).filter_by(
            student_id=student_id, skill_id=skill_id
        ).first()
        
        skill = self.db.query(Skill).get(skill_id)
        if not skill:
            raise ValueError(f"Skill {skill_id} not found")
        
        # Если состояния нет, создаем новое
        if not state:
            state = StudentKnowledgeState(
                student_id=student_id,
                skill_id=skill_id,
                probability_knowing=skill.p_init
            )
            self.db.add(state)
            self.db.flush()
        
        # Сохраняем историю перед обновлением
        history = KnowledgeHistory(
            student_id=student_id,
            skill_id=skill_id,
            probability=state.probability_knowing,
            recorded_at=attempt_date
        )
        self.db.add(history)
        
        # Получаем текущую вероятность с учетом забывания
        current_prob = self.get_current_knowledge(student_id, skill_id)
        
        # Обновляем статистику
        state.total_attempts += 1
        if is_correct:
            state.correct_attempts += 1
        
        # BKT обновление
        if is_correct:
            # Вероятность правильного ответа
            p_correct = (current_prob * (1 - skill.p_slip) + 
                        (1 - current_prob) * skill.p_guess)
            
            if p_correct > 0:
                # Пост-тестовая вероятность по Байесу
                p_know_given_correct = (current_prob * (1 - skill.p_slip)) / p_correct
                new_prob = p_know_given_correct
            else:
                new_prob = current_prob
        else:
            # Вероятность неправильного ответа
            p_wrong = (current_prob * skill.p_slip + 
                      (1 - current_prob) * (1 - skill.p_guess))
            
            if p_wrong > 0:
                p_know_given_wrong = (current_prob * skill.p_slip) / p_wrong
                new_prob = p_know_given_wrong
            else:
                new_prob = current_prob
        
        # Добавляем вероятность научения (обучение на ошибках)
        new_prob = new_prob + (1 - new_prob) * skill.p_learn
        
        # Ограничиваем значения
        new_prob = max(0.01, min(0.99, new_prob))
        
        # Обновляем состояние
        state.probability_knowing = new_prob
        state.last_updated = attempt_date
        
        self.db.commit()
        
        logger.info(f"Updated student {student_id} skill {skill_id}: "
                   f"{current_prob:.3f} -> {new_prob:.3f} (correct={is_correct})")
        
        return new_prob
    
    def process_test_results(self, test_id: int) -> int:
        """
        Обрабатывает все результаты конкретного теста
        Возвращает количество обновленных записей
        """
        print(f"🔄 BKT: Processing test {test_id}")
        
        # Получаем все попытки для этого теста
        attempts = self.db.query(StudentAttempt).join(
            TestItem
        ).filter(
            TestItem.test_id == test_id
        ).order_by(
            StudentAttempt.created_at
        ).all()
        
        print(f"📊 BKT: Найдено {len(attempts)} попыток")
        
        if not attempts:
            logger.warning(f"No attempts found for test {test_id}")
            return 0
        
        # Группируем по студентам и навыкам
        updates = {}
        for attempt in attempts:
            skill_id = attempt.test_item.skill_id
            key = (attempt.student_id, skill_id)
            
            if key not in updates:
                updates[key] = []
            updates[key].append(attempt)
        
        print(f"📊 BKT: Обновляем {len(updates)} уникальных пар студент-навык")
        
        # Обновляем каждую группу в хронологическом порядке
        updated_count = 0
        for (student_id, skill_id), attempt_list in updates.items():
            print(f"  👤 Студент {student_id}, навык {skill_id}: {len(attempt_list)} попыток")
            # Сортируем по времени
            attempt_list.sort(key=lambda x: x.created_at)
            
            for attempt in attempt_list:
                self.update_from_attempt(
                    student_id=student_id,
                    skill_id=skill_id,
                    is_correct=attempt.is_correct,
                    attempt_date=attempt.created_at
                )
                updated_count += 1
        
        logger.info(f"Processed test {test_id}: {updated_count} updates")
        print(f"✅ BKT: Обработано {updated_count} обновлений")
        return updated_count
    
    def get_mastery_table(self) -> Tuple[List[dict], List[dict], List[dict]]:
        """
        Формирует таблицу освоения для отображения
        Возвращает (студенты, навыки, матрица освоения)
        """
        students = self.db.query(Student).all()
        skills = self.db.query(Skill).filter_by(is_active=True).all()
        
        students_data = [{"id": s.id, "name": s.name, "class": s.class_name} 
                        for s in students]
        skills_data = [{"id": sk.id, "name": sk.name} for sk in skills]
        
        matrix = []
        for student in students:
            student_row = {
                "student_id": student.id,
                "student_name": student.name,
                "mastery": {}
            }
            
            for skill in skills:
                prob = self.get_current_knowledge(student.id, skill.id)
                percentage = round(prob * 100, 1)
                student_row["mastery"][skill.id] = {
                    "percentage": percentage,
                    "probability": prob
                }
            
            matrix.append(student_row)
        
        return students_data, skills_data, matrix
    
    def calibrate_skill_parameters(self, skill_id: int) -> dict:
        """
        Калибровка параметров навыка на основе исторических данных
        """
        # Получаем все попытки по этому навыку
        attempts = self.db.query(StudentAttempt).join(
            TestItem
        ).filter(
            TestItem.skill_id == skill_id
        ).all()
        
        if len(attempts) < 30:  # Нужно минимум данных
            return {"status": "insufficient_data", "required": 30, "got": len(attempts)}
        
        skill = self.db.query(Skill).get(skill_id)
        
        # Простая эмпирическая оценка
        # В реальном проекте здесь можно использовать EM-алгоритм
        total = len(attempts)
        correct = sum(1 for a in attempts if a.is_correct)
        
        # Грубая оценка p_guess - доля правильных у "начинающих"
        # Берем первые попытки учеников
        first_attempts = {}
        for attempt in attempts:
            if attempt.student_id not in first_attempts:
                first_attempts[attempt.student_id] = attempt
        
        if first_attempts:
            first_correct = sum(1 for a in first_attempts.values() if a.is_correct)
            estimated_guess = first_correct / len(first_attempts)
            skill.p_guess = max(0.05, min(0.4, estimated_guess))
        
        # Обновляем в базе
        self.db.commit()
        
        return {
            "status": "calibrated",
            "p_guess": skill.p_guess,
            "p_slip": skill.p_slip,
            "p_learn": skill.p_learn,
            "p_init": skill.p_init
        }