"""
Модуль для категоризации транзакций с помощью OpenAI
"""
from openai import OpenAI
import json
import re


class TransactionCategorizer:
    def __init__(self, api_key):
        """
        Инициализация категоризатора
        
        Args:
            api_key: API ключ OpenAI
        """
        self.client = OpenAI(api_key=api_key)
        
        # Предопределенные категории
        self.categories = {
            'Expense': [
                'Groceries',
                'Transport',
                'Housing',
                'Utilities',
                'Communication',
                'Health & Medical',
                'Clothing',
                'Entertainment',
                'Restaurants & Cafes',
                'Education',
                'Gifts',
                'Sports & Fitness',
                'Beauty',
                'Other'
            ],
            'Income': [
                'Salary',
                'Freelance',
                'Side Job',
                'Investment',
                'Debt Return',
                'Gift',
                'Other'
            ]
        }
        
        # Курсы валют к ILS (примерные, можно обновлять)
        self.exchange_rates = {
            'ILS': 1.0,
            'USD': 3.7,
            'EUR': 4.0,
            'RUB': 0.04,
            'GBP': 4.7
        }
    
    def parse_transaction(self, text):
        """
        Парсит текст транзакции с помощью OpenAI
        
        Args:
            text: текст сообщения от пользователя
            
        Returns:
            dict с полями: type, amount, currency, category, description
        """
        try:
            # Формируем промпт для OpenAI
            prompt = f"""
You are a financial tracking assistant. Analyze the following transaction message and extract information.

Message: "{text}"

Return result STRICTLY in JSON format with the following fields:
- type: "Expense" or "Income"
- amount: numeric value (number only, without currency symbol)
- currency: currency code (ILS, USD, EUR, RUB, GBP, etc.) - determine from context or default to ILS
- category: one of the categories below
- description: BRIEF description in ENGLISH (2-3 words max, just the essence - what was bought/earned, NOT the full original message)

Expense categories: {', '.join(self.categories['Expense'])}
Income categories: {', '.join(self.categories['Income'])}

IMPORTANT for description:
- Keep it SHORT (2-3 words maximum)
- Always in ENGLISH (translate if needed)
- Just the ESSENCE - what item/service, NOT the amount, NOT the full sentence
- Examples: "Coffee" not "Bought coffee for 200", "Groceries" not "Spent on groceries", "Taxi ride" not "Потратил на такси"

If amount is not explicitly stated, try to find it in the text. If you can't determine - set 0.
If transaction type is not explicit, determine from context (default - Expense).
Detect currency from symbols (₪/$//€/£/руб) or words (shekel/dollar/euro/ruble), default to ILS if not specified.

Examples:
- "Купил хлеб за 100 рублей" -> {{"type": "Expense", "amount": 100, "currency": "RUB", "category": "Groceries", "description": "Bread"}}
- "Потратил 300 на кофе" -> {{"type": "Expense", "amount": 300, "currency": "RUB", "category": "Restaurants & Cafes", "description": "Coffee"}}
- "Spent 50$ on taxi" -> {{"type": "Expense", "amount": 50, "currency": "USD", "category": "Transport", "description": "Taxi"}}
- "Got salary 5000₪" -> {{"type": "Income", "amount": 5000, "currency": "ILS", "category": "Salary", "description": "Salary"}}
- "+200 freelance" -> {{"type": "Income", "amount": 200, "currency": "ILS", "category": "Freelance", "description": "Freelance"}}
- "Купил продукты в магазине 1500р" -> {{"type": "Expense", "amount": 1500, "currency": "RUB", "category": "Groceries", "description": "Groceries"}}

Return ONLY JSON, no additional text.
"""
            
            response = self.client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {"role": "system", "content": "You are a financial transaction analysis assistant. Respond only in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            # Извлекаем ответ
            result_text = response.choices[0].message.content.strip()
            print(f"[DEBUG] GPT Raw Response: {result_text}")
            
            # Убираем markdown форматирование если есть
            result_text = re.sub(r'```json\s*', '', result_text)
            result_text = re.sub(r'```\s*', '', result_text)
            
            # Парсим JSON
            result = json.loads(result_text)
            print(f"[DEBUG] Parsed result: {result}")
            
            # Валидация результата
            if 'type' not in result or result['type'] not in ['Expense', 'Income']:
                result['type'] = 'Expense'
            
            if 'amount' not in result:
                result['amount'] = 0
            else:
                # Убеждаемся что amount - число
                try:
                    result['amount'] = float(result['amount'])
                except:
                    result['amount'] = 0
            
            if 'currency' not in result:
                result['currency'] = 'ILS'
            else:
                result['currency'] = result['currency'].upper()
            
            if 'category' not in result:
                result['category'] = 'Other'
            
            if 'description' not in result:
                result['description'] = text[:50]  # Первые 50 символов
            
            # Добавляем конвертацию в ILS
            result['amount_ils'] = self.convert_to_ils(result['amount'], result['currency'])
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"Ошибка парсинга JSON: {e}")
            print(f"Ответ от OpenAI: {result_text}")
            return self._fallback_parse(text)
            
        except Exception as e:
            print(f"Ошибка при обработке транзакции: {e}")
            return self._fallback_parse(text)
    
    def _fallback_parse(self, text):
        """
        Базовый парсинг без OpenAI (на случай ошибки)
        """
        # Ищем числа в тексте
        numbers = re.findall(r'\d+(?:\.\d+)?', text)
        amount = float(numbers[0]) if numbers else 0
        
        # Определяем тип по ключевым словам
        income_keywords = ['получил', 'зарплата', 'доход', 'заработал', '+', 'income', 'salary', 'earned']
        transaction_type = 'Income' if any(keyword in text.lower() for keyword in income_keywords) else 'Expense'
        
        # Определяем валюту по символам
        currency = 'ILS'
        if '$' in text or 'usd' in text.lower() or 'dollar' in text.lower():
            currency = 'USD'
        elif '€' in text or 'eur' in text.lower() or 'euro' in text.lower():
            currency = 'EUR'
        elif '₽' in text or 'руб' in text.lower() or 'rub' in text.lower():
            currency = 'RUB'
        elif '£' in text or 'gbp' in text.lower() or 'pound' in text.lower():
            currency = 'GBP'
        
        amount_ils = self.convert_to_ils(amount, currency)
        
        return {
            'type': transaction_type,
            'amount': amount,
            'currency': currency,
            'category': 'Other',
            'description': text[:100],
            'amount_ils': amount_ils
        }
    
    def convert_to_ils(self, amount, currency):
        """
        Конвертирует сумму в шекели
        
        Args:
            amount: сумма
            currency: валюта
            
        Returns:
            сумма в шекелях
        """
        currency = currency.upper()
        rate = self.exchange_rates.get(currency, 1.0)
        return round(amount * rate, 2)

