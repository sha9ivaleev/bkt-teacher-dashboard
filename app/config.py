import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL не установлен в .env файле")

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("❌ SECRET_KEY не установлен в .env файле")

if len(SECRET_KEY) < 32:
    raise ValueError("❌ SECRET_KEY должен быть минимум 32 символа")

ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

DEFAULT_BKT_PARAMS = {
    "p_learn": float(os.getenv("DEFAULT_P_LEARN", "0.15")),
    "p_guess": float(os.getenv("DEFAULT_P_GUESS", "0.20")),
    "p_slip": float(os.getenv("DEFAULT_P_SLIP", "0.10")),
    "p_init": float(os.getenv("DEFAULT_P_INIT", "0.20")),
    "forgetting_rate": float(os.getenv("FORGETTING_RATE", "0.01"))
}