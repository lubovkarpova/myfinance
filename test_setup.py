"""
Скрипт для тестирования настройки бота
"""
import sys
import os

def test_env_variables():
    """Проверка наличия переменных окружения"""
    print("🔍 Проверка переменных окружения...")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    errors = []
    
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not telegram_token:
        errors.append("❌ TELEGRAM_BOT_TOKEN не установлен")
    else:
        print("✅ TELEGRAM_BOT_TOKEN установлен")
    
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        errors.append("❌ OPENAI_API_KEY не установлен")
    else:
        print("✅ OPENAI_API_KEY установлен")
    
    credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'my-finance-475615-72e35dbf9d52.json')
    if not os.path.exists(credentials_file):
        errors.append(f"❌ Файл credentials не найден: {credentials_file}")
    else:
        print(f"✅ Файл credentials найден: {credentials_file}")
    
    return errors


def test_google_sheets():
    """Проверка подключения к Google Sheets"""
    print("\n📊 Проверка подключения к Google Sheets...")
    
    try:
        from google_sheets import GoogleSheetsManager
        import config
        
        manager = GoogleSheetsManager(
            config.GOOGLE_CREDENTIALS_FILE,
            config.SPREADSHEET_NAME
        )
        
        if manager.connect():
            print("✅ Успешное подключение к Google Sheets")
            url = manager.get_spreadsheet_url()
            print(f"📋 Ссылка на таблицу: {url}")
            return True
        else:
            print("❌ Не удалось подключиться к Google Sheets")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при подключении к Google Sheets: {e}")
        return False


def test_openai():
    """Проверка OpenAI API"""
    print("\n🤖 Проверка OpenAI API...")
    
    try:
        from openai_categorizer import TransactionCategorizer
        import config
        
        categorizer = TransactionCategorizer(config.OPENAI_API_KEY)
        
        # Пробуем обработать тестовую транзакцию
        test_text = "Купил продукты за 500 рублей"
        result = categorizer.parse_transaction(test_text)
        
        print("✅ OpenAI API работает")
        print(f"📝 Тест: '{test_text}'")
        print(f"   Результат: {result}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при работе с OpenAI: {e}")
        return False


def main():
    """Основная функция тестирования"""
    print("=" * 50)
    print("🧪 Тестирование настройки финансового бота")
    print("=" * 50)
    
    # Проверка переменных окружения
    env_errors = test_env_variables()
    
    if env_errors:
        print("\n⚠️  Обнаружены ошибки конфигурации:")
        for error in env_errors:
            print(f"  {error}")
        print("\n💡 Создайте файл .env на основе env_example.txt")
        sys.exit(1)
    
    # Проверка Google Sheets
    sheets_ok = test_google_sheets()
    
    # Проверка OpenAI
    openai_ok = test_openai()
    
    # Итоги
    print("\n" + "=" * 50)
    if sheets_ok and openai_ok:
        print("✅ Все тесты пройдены! Бот готов к запуску.")
        print("🚀 Запустите бота командой: python bot.py")
    else:
        print("❌ Некоторые тесты не прошли.")
        print("⚠️  Проверьте настройки и попробуйте снова.")
    print("=" * 50)


if __name__ == '__main__':
    main()

