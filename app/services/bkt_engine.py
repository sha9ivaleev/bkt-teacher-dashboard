import numpy as np
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional, List, Tuple
from app.models.db_models import (
    Student, Skill, StudentAttempt, TestItem,
    StudentKnowledgeState, KnowledgeHistory
)
from app.config import DEFAULT_BKT_PARAMS
from app.logger import logger

class BKTEngine:
    def __init__(self, db: Session):
        self.db = db
        self.forgetting_rate = DEFAULT_BKT_PARAMS["forgetting_rate"]
    
    def _apply_forgetting(self, probability: float, days_passed: float) -> float:
        if days_passed <= 0:
            return probability
        
        decay = np.exp(-self.forgetting_rate * days_passed)
        min_probability = DEFAULT_BKT_PARAMS["p_init"]
        
        new_probability = min_probability + (probability - min_probability) * decay
        return max(min_probability, min(probability, new_probability))
    
    def get_current_knowledge(self, student_id: int, skill_id: int) -> float:
        state = self.db.query(StudentKnowledgeState).filter_by(
            student_id=student_id, skill_id=skill_id
        ).first()
        
        if not state:
            skill = self.db.query(Skill).get(skill_id)
            return skill.p_init if skill else DEFAULT_BKT_PARAMS["p_init"]
        
        if state.last_updated.tzinfo is not None:
            last_updated = state.last_updated.replace(tzinfo=None)
        else:
            last_updated = state.last_updated
        
        days_passed = (datetime.now() - last_updated).days
        return self._apply_forgetting(state.probability_knowing, days_passed)
    
    def update_from_attempt(self, 
                           student_id: int, 
                           skill_id: int, 
                           is_correct: bool,
                           attempt_date: Optional[datetime] = None) -> float:
        if attempt_date is None:
            attempt_date = datetime.now()
        
        if attempt_date.tzinfo is not None:
            attempt_date = attempt_date.replace(tzinfo=None)
        
        state = self.db.query(StudentKnowledgeState).filter_by(
            student_id=student_id, skill_id=skill_id
        ).first()
        
        skill = self.db.query(Skill).get(skill_id)
        if not skill:
            raise ValueError(f"Skill {skill_id} not found")
        
        if not state:
            state = StudentKnowledgeState(
                student_id=student_id,
                skill_id=skill_id,
                probability_knowing=skill.p_init
            )
            self.db.add(state)
            self.db.flush()
        
        history = KnowledgeHistory(
            student_id=student_id,
            skill_id=skill_id,
            probability=state.probability_knowing,
            recorded_at=attempt_date
        )
        self.db.add(history)
        
        current_prob = self.get_current_knowledge(student_id, skill_id)
        
        state.total_attempts += 1
        if is_correct:
            state.correct_attempts += 1
        
        if is_correct:
            p_correct = (current_prob * (1 - skill.p_slip) + 
                        (1 - current_prob) * skill.p_guess)
            
            if p_correct > 0:
                p_know_given_correct = (current_prob * (1 - skill.p_slip)) / p_correct
                new_prob = p_know_given_correct
            else:
                new_prob = current_prob
        else:
            p_wrong = (current_prob * skill.p_slip + 
                      (1 - current_prob) * (1 - skill.p_guess))
            
            if p_wrong > 0:
                p_know_given_wrong = (current_prob * skill.p_slip) / p_wrong
                new_prob = p_know_given_wrong
            else:
                new_prob = current_prob
        
        new_prob = new_prob + (1 - new_prob) * skill.p_learn
        new_prob = max(0.01, min(0.99, new_prob))
        
        state.probability_knowing = new_prob
        state.last_updated = attempt_date
        
        self.db.commit()
        
        logger.info(f"Обновление студента {student_id}, навык {skill_id}: "
                   f"{current_prob:.3f} -> {new_prob:.3f}")
        
        return new_prob
    
    def process_test_results(self, test_id: int) -> int:
        logger.info(f"Обработка теста {test_id}")
        
        attempts = self.db.query(StudentAttempt).join(
            TestItem
        ).filter(
            TestItem.test_id == test_id
        ).order_by(
            StudentAttempt.created_at
        ).all()
        
        logger.info(f"Найдено {len(attempts)} попыток")
        
        if not attempts:
            return 0
        
        updates = {}
        for attempt in attempts:
            skill_id = attempt.test_item.skill_id
            key = (attempt.student_id, skill_id)
            
            if key not in updates:
                updates[key] = []
            updates[key].append(attempt)
        
        logger.info(f"Обновляем {len(updates)} пар студент-навык")
        
        updated_count = 0
        for (student_id, skill_id), attempt_list in updates.items():
            attempt_list.sort(key=lambda x: x.created_at)
            
            for attempt in attempt_list:
                self.update_from_attempt(
                    student_id=student_id,
                    skill_id=skill_id,
                    is_correct=attempt.is_correct,
                    attempt_date=attempt.created_at
                )
                updated_count += 1
        
        logger.info(f"Тест {test_id} обработан, {updated_count} обновлений")
        return updated_count
    
    def get_mastery_table(self) -> Tuple[List[dict], List[dict], List[dict]]:
        students = self.db.query(Student).order_by(Student.name).all()
        skills = self.db.query(Skill).filter_by(is_active=True).order_by(Skill.name).all()
        
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