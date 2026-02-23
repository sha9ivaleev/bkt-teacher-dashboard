import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Базовые пути
BASE_DIR = Path(__file__).resolve().parent.parent

# Настройки базы данных
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/bkt_db")

# Настройки безопасности
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Настройки BKT (параметры по умолчанию)
DEFAULT_BKT_PARAMS = {
    "p_learn": float(os.getenv("DEFAULT_P_LEARN", "0.15")),
    "p_guess": float(os.getenv("DEFAULT_P_GUESS", "0.20")),
    "p_slip": float(os.getenv("DEFAULT_P_SLIP", "0.10")),
    "p_init": float(os.getenv("DEFAULT_P_INIT", "0.20")),
    "forgetting_rate": float(os.getenv("FORGETTING_RATE", "0.01"))
}

# Настройки приложения
DEBUG = True
HOST = "0.0.0.0"
PORT = 8000