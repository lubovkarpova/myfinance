"""
Скрипт для массовой загрузки исторических транзакций в Google Sheets
"""
import re
from datetime import datetime
from google_sheets import GoogleSheetsManager
from openai_categorizer import TransactionCategorizer
import config

def parse_historical_transaction(text):
    """
    Парсит историческую транзакцию из текста
    
    Args:
        text: строка вида "21 октября аренла скутера 41"
        
    Returns:
        dict: данные транзакции
    """
    # Убираем лишние пробелы
    text = text.strip()
    
    # Ищем дату в начале
    date_match = re.match(r'(\d+)\s+октября', text)
    if not date_match:
        return None
    
    day = date_match.group(1)
    date_str = f"{day}-10-25"  # 2025 год
    
    # Убираем дату из текста
    remaining_text = re.sub(r'^\d+\s+октября\s+', '', text)
    
    # Ищем сумму в конце
    amount_match = re.search(r'(\d+(?:\.\d+)?)\s*(доллары?|рублей?|₽|$|USD|RUB)?\s*$', remaining_text)
    if not amount_match:
        return None
    
    amount = float(amount_match.group(1))
    currency_hint = amount_match.group(2) if amount_match.group(2) else ''
    
    # Определяем валюту
    currency = 'ILS'  # по умолчанию
    if 'доллар' in currency_hint.lower() or 'usd' in currency_hint.lower():
        currency = 'USD'
    elif 'рубл' in currency_hint.lower() or '₽' in currency_hint or 'rub' in currency_hint.lower():
        currency = 'RUB'
    
    # Убираем сумму из текста для описания
    description_text = re.sub(r'\s+\d+(?:\.\d+)?\s*(доллары?|рублей?|₽|USD|RUB)?\s*$', '', remaining_text)
    
    # Определяем тип транзакции
    transaction_type = 'Expense'  # по умолчанию расход
    
    # Конвертируем в ILS
    exchange_rates = {'ILS': 1.0, 'USD': 3.7, 'EUR': 4.0, 'RUB': 0.04, 'GBP': 4.7}
    amount_ils = round(amount * exchange_rates.get(currency, 1.0), 2)
    
    return {
        'date': date_str,
        'type': transaction_type,
        'description': description_text,
        'category': 'Other',  # будет определено через GPT
        'amount': amount,
        'currency': currency,
        'amount_ils': amount_ils,
        'username': 'Liuba',
        'input': text,
        'subscription': _parse_subscription(text)
    }

def _parse_subscription(text):
    """
    Парсит информацию о подписке из текста
    
    Логика: ищет цифру сразу после слова "подписка" (с пробелом или без).
    Если находит - это номер платежа. Если не находит - это простая подписка (Yes).
    """
    import re
    text_lower = text.lower()
    
    if 'подписка' not in text_lower:
        return ''
    
    # Ищем "подписка" и смотрим что идет сразу после него
    # Если идет пробел + однозначная цифра (1-9) - это номер (например "подписка 1")
    # Если идет только цифра сразу - это номер (например "подписка3")
    # Если идет многозначное число или число не сразу - это сумма
    match_immediate = re.search(r'подписка\s+([1-9])\b|подписка([1-9])', text_lower)
    
    if match_immediate:
        # Нашли однозначную цифру сразу после "подписка" - это номер платежа
        result = match_immediate.group(1) or match_immediate.group(2)
        return result
    else:
        # Не нашли - это простая подписка
        return 'Yes'

def categorize_transactions(transactions, categorizer):
    """
    Категоризирует транзакции через GPT
    """
    for transaction in transactions:
        try:
            parsed = categorizer.parse_transaction(transaction['input'])
            transaction['category'] = parsed['category']
            transaction['description'] = parsed['description']
            print(f"✅ {transaction['input']} → {transaction['category']}")
        except Exception as e:
            print(f"❌ Error categorizing {transaction['input']}: {e}")

def main():
    """Основная функция"""
    
    # Список транзакций
    transactions_text = [
        "21 октября аренла скутера 41",
        "22 октября кофе 23",
        "22 октября Амазон прайм подписка 50",
        "23 октября кофе 30",
        "23 октября фрукты и овощи доставка 230 подписка",
        "23 октября ClubMed 11804",
        "23 октября книга 48 законов власти амазон 13.29 доллары",
        "24 октября день рождение вечеринка фрукты bday party 418",
        "24 октября аренда самоката 28",
        "24 октября аренда самоката 38",
        "24 октября доставка готовой еды 410",
        "24 октября день рождение вино bday party 690",
        "24 октября супер маркет 55",
        "24 октября вольт подписка 49",
        "24 октября knafe bday party 336",
        "24 октября кофе 41"
    ]
    
    print("🔄 Parsing transactions...")
    
    # Парсим транзакции
    transactions = []
    for text in transactions_text:
        transaction = parse_historical_transaction(text)
        if transaction:
            transactions.append(transaction)
            print(f"📝 Parsed: {text}")
        else:
            print(f"❌ Failed to parse: {text}")
    
    print(f"\n✅ Parsed {len(transactions)} transactions")
    
    # Инициализируем категоризатор
    print("\n🤖 Initializing categorizer...")
    categorizer = TransactionCategorizer(config.OPENAI_API_KEY)
    
    # Категоризируем транзакции
    print("\n🏷️ Categorizing transactions...")
    categorize_transactions(transactions, categorizer)
    
    # Подключаемся к Google Sheets
    print("\n📊 Connecting to Google Sheets...")
    sheets_manager = GoogleSheetsManager(
        config.GOOGLE_CREDENTIALS_FILE,
        config.SPREADSHEET_NAME
    )
    
    if not sheets_manager.connect():
        print("❌ Failed to connect to Google Sheets")
        return
    
    print("✅ Connected to Google Sheets")
    
    # Загружаем транзакции
    print(f"\n📤 Uploading {len(transactions)} transactions...")
    
    success = sheets_manager.add_transactions_batch(transactions)
    
    if success:
        print("✅ All transactions uploaded successfully!")
        print(f"📊 Check your sheet: {sheets_manager.get_spreadsheet_url()}")
    else:
        print("❌ Failed to upload transactions")

if __name__ == '__main__':
    main()
