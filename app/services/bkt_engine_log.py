import logging

# Настраиваем логирование
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='logs/bkt_debug.log',
    filemode='w'
)
logger = logging.getLogger(__name__)

def log_error(func_name, error, data=None):
    """Логирование ошибок с деталями"""
    error_message = f"Error in {func_name}: {error}"
    logger.error(error_message)
    if data:
        logger.error(f"Data: {data}")
        error_message += f"\nData: {data}"
    print(f"❌ {error_message}")

def log_info(message):
    """Логирование информационных сообщений"""
    logger.info(message)
    print(f"ℹ️ {message}")

def log_debug(message):
    """Логирование отладочных сообщений"""
    logger.debug(message)
    print(f"🔍 {message}")

def log_success(message):
    """Логирование успешных операций"""
    logger.info(message)
    print(f"✅ {message}")