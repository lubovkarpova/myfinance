"""
Модуль для категоризации транзакций с помощью OpenAI
"""
from openai import OpenAI
import json
import re
import os


class TransactionCategorizer:
    def __init__(self, api_key, trainer=None):
        """
        Инициализация категоризатора
        
        Args:
            api_key: API ключ OpenAI
            trainer: экземпляр PromptTrainer (опционально)
        """
        self.client = OpenAI(api_key=api_key)
        self.trainer = trainer
        
        # Файл для сохранения динамических категорий
        self.categories_file = 'categories.json'
        
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
        
        # Загружаем дополнительные категории из файла, если есть
        self._load_categories()
        
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
            # Получаем примеры из тренера, если есть
            training_examples = ""
            if self.trainer:
                training_examples = self.trainer.get_training_examples_for_prompt()
            
            # Если есть примеры из тренера, используем их, иначе базовые
            if training_examples:
                examples_section = f"REAL EXAMPLES from your transaction history:\n{training_examples}"
            else:
                examples_section = """REAL EXAMPLES from user's data:
- "25 кофе" -> {"type": "Expense", "amount": 25, "currency": "ILS", "category": "Restaurant", "description": "Coffee"}
- "такси 70" -> {"type": "Expense", "amount": 70, "currency": "ILS", "category": "Transport", "description": "Taxi"}
- "70 лимонады" -> {"type": "Expense", "amount": 70, "currency": "ILS", "category": "Restaurant", "description": "Limonades"}
- "55 кофе зерна" -> {"type": "Expense", "amount": 55, "currency": "ILS", "category": "Grocery", "description": "Coffee"}
- "185 супермаркет" -> {"type": "Expense", "amount": 185, "currency": "ILS", "category": "Grocery", "description": "Supermarker"}
- "79 вино" -> {"type": "Expense", "amount": 79, "currency": "ILS", "category": "Alcohol", "description": "Vine"}
- "350 массаж" -> {"type": "Expense", "amount": 350, "currency": "ILS", "category": "Health", "description": "Massage"}
- "6000 руб терапия" -> {"type": "Expense", "amount": 6000, "currency": "RUB", "category": "Health", "description": "Phycotherapy"}
- "Цветы 60" -> {"type": "Expense", "amount": 60, "currency": "ILS", "category": "Flower", "description": "Flower"}
- "+60302 зарплата и бонус" -> {"type": "Income", "amount": 60302, "currency": "ILS", "category": "Salary", "description": "Salary + Half a year bonus"}"""
            
            # Формируем промпт для OpenAI
            prompt = f"""
You are a financial tracking assistant. Analyze the transaction message and extract information.

Message: "{text}"

Return STRICTLY in JSON format with these fields:
- type: "Expense" or "Income"
- amount: numeric value only (no currency symbol)
- currency: ILS, USD, EUR, RUB, GBP (default: ILS)
- category: pick ONE from the list below (or suggest a new one if nothing fits)
- description: Brief English description (1-3 words, item/service only, NO amount, NO verbs)

Expense categories: {', '.join(self.categories['Expense'])}
Income categories: {', '.join(self.categories['Income'])}

{examples_section}

RULES:
- Currency detection: руб/рублей->RUB, $->USD, €->EUR, ₪/шекель->ILS, default->ILS
- Categories: TRY to use exact names from the list. If nothing fits well, feel free to suggest a NEW descriptive category name (use capital first letter, keep it short and clear, max 2-3 words)
- Description: translate to English, 1-3 words, essence only
- IMPORTANT: If you create a new category, it will be automatically saved and available for future use

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
            
            # Валидация и нормализация категории
            result = self._validate_category(result)
            
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
        print(f"[FALLBACK] Using fallback parser for: {text}")
        
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
        
        # Убираем число из описания
        description = re.sub(r'\d+(?:\.\d+)?', '', text).strip()
        description = re.sub(r'[₪$€£₽]', '', description).strip()
        # Первое слово как описание
        description = description.split()[0] if description else text[:20]
        
        amount_ils = self.convert_to_ils(amount, currency)
        
        return {
            'type': transaction_type,
            'amount': amount,
            'currency': currency,
            'category': 'Other',
            'description': description,
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
    
    def _load_categories(self):
        """
        Загружает дополнительные категории из файла
        """
        if not os.path.exists(self.categories_file):
            return
        
        try:
            with open(self.categories_file, 'r', encoding='utf-8') as f:
                additional_categories = json.load(f)
                
            # Добавляем категории к существующим (без дубликатов)
            for transaction_type in ['Expense', 'Income']:
                if transaction_type in additional_categories:
                    for cat in additional_categories[transaction_type]:
                        if cat not in self.categories[transaction_type]:
                            self.categories[transaction_type].append(cat)
                            print(f"[INFO] Loaded additional category: {transaction_type}/{cat}")
        except Exception as e:
            print(f"[WARNING] Could not load categories from file: {e}")
    
    def _save_categories(self):
        """
        Сохраняет текущие категории в файл
        """
        try:
            with open(self.categories_file, 'w', encoding='utf-8') as f:
                json.dump(self.categories, f, indent=2, ensure_ascii=False)
            print(f"[INFO] Categories saved to {self.categories_file}")
        except Exception as e:
            print(f"[WARNING] Could not save categories to file: {e}")

    def _validate_category(self, result):
        """
        Проверяет и нормализует категорию
        Если категория не из списка - пытается найти похожую
        Если не находит - создаёт новую категорию динамически
        """
        if 'category' not in result:
            result['category'] = 'Other'
            return result
        
        category = result['category']
        transaction_type = result.get('type', 'Expense')
        
        # Проверяем, есть ли категория в списке
        valid_categories = self.categories.get(transaction_type, [])
        
        if category in valid_categories:
            return result
        
        # Категории нет в списке - пытаемся найти похожую
        print(f"[WARNING] Category '{category}' not in the list. Trying to match...")
        
        # Поиск похожей категории (простой алгоритм)
        matched = False
        for valid_cat in valid_categories:
            if self._category_similar(category, valid_cat):
                print(f"[INFO] Matched '{category}' -> '{valid_cat}'")
                result['category'] = valid_cat
                matched = True
                break
        
        # Если не нашли похожую - создаём новую категорию
        if not matched:
            print(f"[INFO] Creating new category: {transaction_type}/{category}")
            # Добавляем категорию в список
            if transaction_type not in self.categories:
                self.categories[transaction_type] = []
            
            self.categories[transaction_type].append(category)
            
            # Сохраняем обновлённые категории в файл
            self._save_categories()
        
        return result
    
    def _category_similar(self, cat1, cat2):
        """
        Проверяет, похожи ли две категории
        """
        cat1_lower = cat1.lower()
        cat2_lower = cat2.lower()
        
        # Точное совпадение
        if cat1_lower == cat2_lower:
            return True
        
        # Одна содержит другую
        if cat1_lower in cat2_lower or cat2_lower in cat1_lower:
            return True
        
        # Проверка на опечатки (простой способ)
        if len(cat1) > 3 and len(cat2) > 3:
            # Если первые 4 буквы совпадают
            if cat1_lower[:4] == cat2_lower[:4]:
                return True
        
        return False

