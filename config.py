"""
Конфигурация бота
"""
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# OpenAI
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Google Sheets
GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', 'my-finance-475615-72e35dbf9d52.json')
SPREADSHEET_NAME = os.getenv('SPREADSHEET_NAME', 'Финансы')

# Проверка наличия необходимых переменных
def validate_config():
    """Проверяет наличие всех необходимых настроек"""
    errors = []
    
    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN не установлен")
    
    if not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY не установлен")
    
    if not os.path.exists(GOOGLE_CREDENTIALS_FILE):
        errors.append(f"Файл credentials не найден: {GOOGLE_CREDENTIALS_FILE}")
    
    return errors

