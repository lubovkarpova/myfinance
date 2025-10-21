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
        
        # Предопределенные категории (based on user's GoldenSet)
        self.categories = {
            'Expense': [
                'Grocery',
                'Grocery/delivery',
                'Restaurant',
                'Food delivery',
                'Transport',
                'Health',
                'Subscription Health',
                'Subcription Enternainment',
                'Subscription Work',
                'Beauty',
                'Clothing',
                'Home Supply',
                'Work Supply',
                'Alcohol',
                'Books',
                'Misha Education',
                'Entertainment',
                'Charity',
                'Flower',
                'Other'
            ],
            'Income': [
                'Salary',
                'Freelance',
                'Bonus',
                'Investment',
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
You are a financial tracking assistant. Analyze the transaction message and extract information.

Message: "{text}"

Return STRICTLY in JSON format with these fields:
- type: "Expense" or "Income"
- amount: numeric value only (no currency symbol)
- currency: ILS, USD, EUR, RUB, GBP (default: ILS)
- category: pick ONE from the list below
- description: Brief English description (1-3 words, item/service only, NO amount, NO verbs)

Expense categories: {', '.join(self.categories['Expense'])}
Income categories: {', '.join(self.categories['Income'])}

REAL EXAMPLES from user's data:
- "25 кофе" -> {{"type": "Expense", "amount": 25, "currency": "ILS", "category": "Restaurant", "description": "Coffee"}}
- "такси 70" -> {{"type": "Expense", "amount": 70, "currency": "ILS", "category": "Transport", "description": "Taxi"}}
- "70 лимонады" -> {{"type": "Expense", "amount": 70, "currency": "ILS", "category": "Restaurant", "description": "Limonades"}}
- "55 кофе зерна" -> {{"type": "Expense", "amount": 55, "currency": "ILS", "category": "Grocery", "description": "Coffee"}}
- "185 супермаркет" -> {{"type": "Expense", "amount": 185, "currency": "ILS", "category": "Grocery", "description": "Supermarker"}}
- "79 вино" -> {{"type": "Expense", "amount": 79, "currency": "ILS", "category": "Alcohol", "description": "Vine"}}
- "350 массаж" -> {{"type": "Expense", "amount": 350, "currency": "ILS", "category": "Health", "description": "Massage"}}
- "6000 руб терапия" -> {{"type": "Expense", "amount": 6000, "currency": "RUB", "category": "Health", "description": "Phycotherapy"}}
- "Цветы 60" -> {{"type": "Expense", "amount": 60, "currency": "ILS", "category": "Flower", "description": "Flower"}}
- "+60302 зарплата и бонус" -> {{"type": "Income", "amount": 60302, "currency": "ILS", "category": "Salary", "description": "Salary + Half a year bonus"}}

RULES:
- Currency detection: руб/рублей->RUB, $->USD, €->EUR, ₪/шекель->ILS, default->ILS
- Categories: use EXACT names from the list
- Description: translate to English, 1-3 words, essence only

Return ONLY JSON, no markdown, no extra text.
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a financial transaction analysis assistant. Respond only in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=150
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

