"""
Модуль для обучения промпта категоризации на основе реальных данных
"""
import logging
from google_sheets import GoogleSheetsManager
from datetime import datetime, timedelta
import config

logger = logging.getLogger(__name__)


class PromptTrainer:
    def __init__(self, categorizer, sheets_manager):
        """
        Инициализация тренера промпта
        
        Args:
            categorizer: экземпляр TransactionCategorizer
            sheets_manager: экземпляр GoogleSheetsManager
        """
        self.categorizer = categorizer
        self.sheets_manager = sheets_manager
        self.last_training_date = None
        self.training_data_cache = []
    
    def load_training_data(self, limit=50):
        """
        Загружает примеры из Google Sheets для обучения
        
        Args:
            limit: максимум примеров для загрузки (по умолчанию 50)
            
        Returns:
            list: список примеров [{"input": "...", "category": "...", "description": "..."}, ...]
        """
        if not self.sheets_manager or not self.sheets_manager.worksheet:
            logger.error("Sheets manager not connected")
            return []
        
        try:
            # Получаем все данные из таблицы
            all_values = self.sheets_manager.worksheet.get_all_records()
            
            training_data = []
            for row in all_values:
                # Пропускаем пустые строки
                if not row.get('input'):
                    continue
                
                training_example = {
                    'input': row.get('input', ''),
                    'type': row.get('Type', ''),
                    'category': row.get('Category', ''),
                    'description': row.get('Description', ''),
                    'amount': row.get('Amount', ''),
                    'currency': row.get('Currency', 'ILS'),
                    'corrected': row.get('Corrected', '')
                }
                
                # Добавляем только если есть все необходимые поля
                if training_example['input'] and training_example['category']:
                    training_data.append(training_example)
                    
                    if len(training_data) >= limit:
                        break
            
            logger.info(f"Loaded {len(training_data)} training examples")
            self.training_data_cache = training_data
            return training_data
            
        except Exception as e:
            logger.error(f"Error loading training data: {e}")
            return []
    
    def build_training_examples_text(self, training_data=None):
        """
        Формирует текст с примерами для промпта
        
        Args:
            training_data: список примеров (если None - использует кеш)
            
        Returns:
            str: форматированная строка с примерами
        """
        if training_data is None:
            training_data = self.training_data_cache
        
        if not training_data:
            return ""
        
        examples = []
        
        # Разделяем на исправленные и обычные
        corrected_examples = [ex for ex in training_data if ex.get('corrected', '').lower() in ['yes', 'true', '1', '✓', 'v']]
        regular_examples = [ex for ex in training_data if ex.get('corrected', '').lower() not in ['yes', 'true', '1', '✓', 'v']]
        
        # Приоритет: сначала исправленные, потом обычные
        # Берем последние исправленные + остальное из обычных до 15
        selected_examples = []
        
        # Добавляем последние исправленные (максимум 10)
        selected_examples.extend(corrected_examples[-10:])
        
        # Добавляем обычные до общего лимита 15
        remaining_slots = 15 - len(selected_examples)
        if remaining_slots > 0:
            selected_examples.extend(regular_examples[-remaining_slots:])
        
        # Берем последние 15 из выбранных
        final_examples = selected_examples[-15:] if len(selected_examples) > 15 else selected_examples
        
        for i, example in enumerate(final_examples, 1):
            input_text = example['input']
            category = example['category']
            description = example.get('description', input_text.split()[0])
            amount = example.get('amount', '')
            
            # Форматируем пример
            if '+' in input_text or 'salary' in input_text.lower() or 'доход' in input_text.lower():
                transaction_type = 'Income'
            else:
                transaction_type = 'Expense'
            
            example_text = f'- "{input_text}" -> {{"type": "{transaction_type}", "category": "{category}", "description": "{description}"}}'
            examples.append(example_text)
        
        return '\n'.join(examples)
    
    def update_categorizer_prompt(self):
        """
        Обновляет промпт категоризатора с новыми примерами
        """
        try:
            # Загружаем данные
            training_data = self.load_training_data()
            
            if not training_data:
                logger.warning("No training data available")
                return False
            
            # Сохраняем дату обучения
            self.last_training_date = datetime.now()
            
            logger.info(f"Prompt trainer updated with {len(training_data)} examples")
            return True
            
        except Exception as e:
            logger.error(f"Error updating prompt: {e}")
            return False
    
    def should_retrain(self):
        """
        Проверяет, нужно ли переобучать (каждый понедельник)
        
        Returns:
            bool: True если нужно переобучить
        """
        if self.last_training_date is None:
            return True
        
        now = datetime.now()
        
        # Проверяем, был ли уже понедельник после последнего обучения
        days_since_training = (now - self.last_training_date).days
        is_monday = now.weekday() == 0  # 0 = Monday
        
        # Переобучаем каждый понедельник
        if is_monday and days_since_training >= 7:
            return True
        
        return False
    
    def get_training_examples_for_prompt(self):
        """
        Возвращает примеры для добавления в промпт GPT
        Используется в openai_categorizer.py
        """
        if not self.training_data_cache:
            self.load_training_data()
        
        return self.build_training_examples_text()
    
    def get_stats(self):
        """
        Возвращает статистику по обучению
        
        Returns:
            dict: статистика
        """
        return {
            'training_examples_count': len(self.training_data_cache),
            'last_training_date': self.last_training_date.isoformat() if self.last_training_date else None,
            'should_retrain': self.should_retrain()
        }


def schedule_weekly_training(app, trainer):
    """
    Запускает еженедельное обучение по понедельникам
    """
    import asyncio
    from telegram.ext import CallbackContext
    
    async def train_task(context: CallbackContext):
        if trainer.should_retrain():
            logger.info("Starting weekly training...")
            success = trainer.update_categorizer_prompt()
            if success:
                logger.info("Weekly training completed successfully")
            else:
                logger.warning("Weekly training failed")
    
    # Проверяем каждые 6 часов
    return asyncio.create_task(train_task(None))
