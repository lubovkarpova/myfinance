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
            'Расходы': [
                'Продукты',
                'Транспорт',
                'Жилье',
                'Коммунальные услуги',
                'Связь и интернет',
                'Здоровье и медицина',
                'Одежда и обувь',
                'Развлечения',
                'Рестораны и кафе',
                'Образование',
                'Подарки',
                'Спорт и фитнес',
                'Красота',
                'Прочее'
            ],
            'Доходы': [
                'Зарплата',
                'Фриланс',
                'Подработка',
                'Инвестиции',
                'Возврат долга',
                'Подарок',
                'Прочее'
            ]
        }
    
    def parse_transaction(self, text):
        """
        Парсит текст транзакции с помощью OpenAI
        
        Args:
            text: текст сообщения от пользователя
            
        Returns:
            dict с полями: type, amount, category, description
        """
        try:
            # Формируем промпт для OpenAI
            prompt = f"""
Ты - ассистент для учета финансов. Проанализируй следующее сообщение о финансовой транзакции и извлеки из него информацию.

Сообщение: "{text}"

Верни результат СТРОГО в формате JSON со следующими полями:
- type: "Расход" или "Доход"
- amount: числовое значение суммы (только число, без валюты)
- category: одна из категорий ниже
- description: краткое описание транзакции

Категории расходов: {', '.join(self.categories['Расходы'])}
Категории доходов: {', '.join(self.categories['Доходы'])}

Если сумма не указана явно, попробуй её найти в тексте. Если не можешь определить - поставь 0.
Если тип транзакции не указан явно, определи по контексту (по умолчанию - Расход).

Примеры:
- "Купил хлеб за 100 рублей" -> {{"type": "Расход", "amount": 100, "category": "Продукты", "description": "Хлеб"}}
- "Потратил 500 на такси" -> {{"type": "Расход", "amount": 500, "category": "Транспорт", "description": "Такси"}}
- "Получил зарплату 50000" -> {{"type": "Доход", "amount": 50000, "category": "Зарплата", "description": "Зарплата"}}
- "+5000 фриланс" -> {{"type": "Доход", "amount": 5000, "category": "Фриланс", "description": "Фриланс"}}

Верни только JSON, без дополнительного текста.
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Ты - ассистент для анализа финансовых транзакций. Отвечай только в формате JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            # Извлекаем ответ
            result_text = response.choices[0].message.content.strip()
            
            # Убираем markdown форматирование если есть
            result_text = re.sub(r'```json\s*', '', result_text)
            result_text = re.sub(r'```\s*', '', result_text)
            
            # Парсим JSON
            result = json.loads(result_text)
            
            # Валидация результата
            if 'type' not in result or result['type'] not in ['Расход', 'Доход']:
                result['type'] = 'Расход'
            
            if 'amount' not in result:
                result['amount'] = 0
            else:
                # Убеждаемся что amount - число
                try:
                    result['amount'] = float(result['amount'])
                except:
                    result['amount'] = 0
            
            if 'category' not in result:
                result['category'] = 'Прочее'
            
            if 'description' not in result:
                result['description'] = text[:50]  # Первые 50 символов
            
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
        income_keywords = ['получил', 'зарплата', 'доход', 'заработал', '+']
        transaction_type = 'Доход' if any(keyword in text.lower() for keyword in income_keywords) else 'Расход'
        
        return {
            'type': transaction_type,
            'amount': amount,
            'category': 'Прочее',
            'description': text[:100]
        }

