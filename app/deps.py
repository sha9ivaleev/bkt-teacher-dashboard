from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models.db_models import User
from app.config import SECRET_KEY, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

class AuthDeps:
    @staticmethod
    async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
    ) -> Optional[User]:
        if not token:
            return None
        
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                return None
        except JWTError:
            return None
        
        user = db.query(User).filter(User.username == username).first()
        return user
    
    @staticmethod
    async def get_current_active_user(
        current_user: Optional[User] = Depends(get_current_user)
    ) -> User:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Не авторизован"
            )
        if not current_user.is_active:
            raise HTTPException(status_code=400, detail="Неактивный пользователь")
        return current_user
    
    @staticmethod
    async def require_teacher(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if current_user.role not in ["teacher", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Требуются права учителя"
            )
        return current_user