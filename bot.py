"""
Телеграм бот для учета финансов
"""
import logging
from datetime import datetime
from telegram import Update, ReactionTypeEmoji
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

import config
from google_sheets import GoogleSheetsManager
from openai_categorizer import TransactionCategorizer
from prompt_trainer import PromptTrainer

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

    # Глобальные объекты
sheets_manager = None
categorizer = None
trainer = None


def _parse_subscription(text):
    """
    Парсит информацию о подписке из текста
    
    Args:
        text: текст транзакции
        
    Returns:
        str: "Yes" если подписка без номера, номер если есть, "" если не подписка
    """
    import re
    
    text_lower = text.lower()
    
    # Проверяем, есть ли слово "подписка"
    if 'подписка' not in text_lower:
        return ''
    
    # Ищем цифру после слова "подписка"
    # Примеры: "подписка 1", "подписка 2", "подписка3"
    match = re.search(r'подписка[^0-9]*([0-9]+)', text_lower)
    
    if match:
        # Нашли цифру - возвращаем её
        return match.group(1)
    else:
        # Подписка без номера - возвращаем "Yes"
        return 'Yes'


async def train_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для ручного запуска обучения"""
    if not trainer:
        await update.message.reply_text("❌ Trainer not initialized.")
        return
    
    await update.message.reply_text("🔄 Training in progress...")
    
    success = trainer.update_categorizer_prompt()
    
    if success:
        stats = trainer.get_stats()
        message = f"✅ Training completed!\n\n"
        message += f"📊 Examples loaded: {stats['training_examples_count']}\n"
        message += f"📅 Last trained: {stats['last_training_date'] or 'Never'}"
        await update.message.reply_text(message)
    else:
        await update.message.reply_text("❌ Training failed. Check logs.")


async def training_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статистику обучения"""
    if not trainer:
        await update.message.reply_text("❌ Trainer not initialized.")
        return
    
    stats = trainer.get_stats()
    
    message = "📊 Training Stats:\n\n"
    message += f"Examples: {stats['training_examples_count']}\n"
    message += f"Last trained: {stats['last_training_date'] or 'Never'}\n"
    message += f"Need retrain: {'Yes' if stats['should_retrain'] else 'No'}"
    
    await update.message.reply_text(message)


def setup_job_queue(app):
    """Настройка периодических задач"""
    from datetime import time
    
    async def weekly_training(context):
        """Выполняется каждую неделю в понедельник"""
        global trainer
        if trainer:
            logger.info("Running weekly training...")
            if trainer.should_retrain():
                success = trainer.update_categorizer_prompt()
                if success:
                    logger.info("Weekly training completed successfully")
                else:
                    logger.warning("Weekly training failed")
    
    # Запускаем задачу каждый понедельник в 9:00
    job_queue = app.job_queue
    
    if job_queue:
        # Запускаем каждый понедельник в 9:00
        job_queue.run_daily(
            weekly_training,
            time=time(9, 0),
            days=(0,),  # 0 = Monday
            name="weekly_training"
        )
        logger.info("Weekly training scheduled for Mondays at 9:00 AM")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    welcome_message = f"""
Hey {user.first_name}! 👋
I'm your money tracker bot. Just drop me messages like:

"Bought groceries 1500₽"
"300₽ on coffee"
"Salary 50k"
"+5k freelance"

I'll parse them instantly and log to Google Sheets. You'll see ✅ when it's done.

🛠 Commands:
/start – This intro
/table – Get your Sheets link
/help – Quick guide
"""
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
👾 How to use me:

Just send me spendings/incomes in plain text.
I'll instantly parse and log them to Google Sheets.
Look for the ✅ reaction when it's logged.

💬 Examples:
"500₽ groceries"
"Coffee 200"
"Taxi 1k"
"Salary 60k"
"+3k freelance"

🧰 Commands:
/start – Intro
/table – Your Sheets link
/help – You're here

That's it. Just text me what you spent. I got you.
"""
    await update.message.reply_text(help_text)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статистику накопленных сообщений"""
    user_id = update.effective_user.id
    
    if 'messages' not in context.user_data:
        context.user_data['messages'] = []
    
    messages_count = len(context.user_data['messages'])
    
    if messages_count == 0:
        await update.message.reply_text("📭 Nothing saved yet.")
    else:
        stats_text = f"📊 Stats:\n"
        stats_text += f"Saved: {messages_count} messages\n\n"
        stats_text += "Latest:\n"
        
        for i, msg in enumerate(context.user_data['messages'][-5:], 1):
            stats_text += f"{i}. {msg['text'][:50]}...\n"
        
        stats_text += f"\nRun /process to log them."
    
    await update.message.reply_text(stats_text)


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Очищает накопленные сообщения"""
    if 'messages' in context.user_data:
        count = len(context.user_data['messages'])
        context.user_data['messages'] = []
        await update.message.reply_text(f"🧹 Cleared {count} messages.")
    else:
        await update.message.reply_text("📭 Nothing to clear.")


async def table_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет ссылку на Google таблицу"""
    if sheets_manager and sheets_manager.spreadsheet:
        url = sheets_manager.get_spreadsheet_url()
        await update.message.reply_text(f"📊 Your sheet:\n{url}")
    else:
        await update.message.reply_text("❌ Couldn't get the link. Try later.")


async def process_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /process - обрабатывает все накопленные сообщения"""
    user = update.effective_user
    
    if 'messages' not in context.user_data or len(context.user_data['messages']) == 0:
        await update.message.reply_text("📭 Nothing to process. Send something first.")
        return
    
    messages = context.user_data['messages']
    await update.message.reply_text(f"⚙️ Processing {len(messages)} messages...\nGimme a sec.")
    
    try:
        # Обрабатываем каждое сообщение
        transactions = []
        
        for msg_data in messages:
            text = msg_data['text']
            timestamp = msg_data['timestamp']
            
            # Используем OpenAI для категоризации
            parsed = categorizer.parse_transaction(text)
            
            # Определяем информацию о подписке
            subscription_info = _parse_subscription(text)
            
            # Формируем данные транзакции
            transaction = {
                'date': timestamp.strftime('%d-%m-%y'),  # Используем дефисы вместо слэшей
                'type': parsed['type'],
                'description': parsed['description'],
                'category': parsed['category'],
                'amount': parsed['amount'],
                'currency': parsed.get('currency', 'ILS'),
                'amount_ils': parsed.get('amount_ils', parsed['amount']),
                'username': user.first_name or user.username or 'Unknown',
                'input': text,  # Сохраняем оригинальный текст для обучения
                'subscription': subscription_info  # Информация о подписке
            }
            
            transactions.append(transaction)
        
        # Добавляем в Google Sheets
        if sheets_manager.add_transactions_batch(transactions):
            # Очищаем буфер сообщений
            context.user_data['messages'] = []
            
            success_message = f"✅ Logged {len(transactions)} transactions!\n\n/table – See the sheet"
            await update.message.reply_text(success_message)
        else:
            await update.message.reply_text("❌ Couldn't add to the sheet. Try again later.")
    
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщений: {e}")
        await update.message.reply_text(f"❌ Something went wrong: {str(e)}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений - мгновенная обработка и отправка в таблицу"""
    user = update.effective_user
    text = update.message.text
    
    try:
        # Сразу обрабатываем через OpenAI
        parsed = categorizer.parse_transaction(text)
        
        # Определяем информацию о подписке
        subscription_info = _parse_subscription(text)
        
        # Формируем данные транзакции
        transaction = {
            'date': datetime.now().strftime('%d-%m-%y'),
            'type': parsed['type'],
            'description': parsed['description'],
            'category': parsed['category'],
            'amount': parsed['amount'],
            'currency': parsed.get('currency', 'ILS'),
            'amount_ils': parsed.get('amount_ils', parsed['amount']),
            'username': user.first_name or user.username or 'Unknown',
            'input': text,  # Сохраняем оригинальный текст для обучения
            'subscription': subscription_info  # Информация о подписке
        }
        
        # Логируем для отладки
        logger.info(f"[DEBUG] Transaction data: {transaction}")
        logger.info(f"[DEBUG] Input text: '{text}'")
        logger.info(f"[DEBUG] Subscription info: '{subscription_info}'")
        
        # Сразу добавляем в Google Sheets
        if sheets_manager.add_transaction(transaction):
            # Молчаливое подтверждение - просто ставим реакцию
            try:
                await update.message.set_reaction(reaction=ReactionTypeEmoji(emoji="👍"))
            except Exception as reaction_error:
                # Игнорируем ошибки реакции, главное что транзакция записана
                logger.debug(f"Не удалось поставить реакцию: {reaction_error}")
        else:
            await update.message.reply_text("❌ Error logging. Try again.")
    
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Update {update} caused error {context.error}")


def main():
    """Запуск бота"""
    global sheets_manager, categorizer, trainer
    
    # Проверка конфигурации
    config_errors = config.validate_config()
    if config_errors:
        logger.error("Ошибки конфигурации:")
        for error in config_errors:
            logger.error(f"  - {error}")
        return
    
    # Инициализация Google Sheets
    logger.info("Подключение к Google Sheets...")
    sheets_manager = GoogleSheetsManager(
        config.GOOGLE_CREDENTIALS_FILE,
        config.SPREADSHEET_NAME
    )
    
    if not sheets_manager.connect():
        logger.error("Не удалось подключиться к Google Sheets")
        return
    
    logger.info(f"✅ Подключено к таблице: {sheets_manager.get_spreadsheet_url()}")
    
    # Инициализация OpenAI categorizer
    logger.info("Инициализация OpenAI...")
    categorizer = TransactionCategorizer(config.OPENAI_API_KEY)
    logger.info("✅ OpenAI готов")
    
    # Инициализация Prompt Trainer
    logger.info("Инициализация Prompt Trainer...")
    trainer = PromptTrainer(categorizer, sheets_manager)
    # Подключаем trainer к categorizer
    categorizer.trainer = trainer
    
    # Загружаем примеры для обучения
    trainer.update_categorizer_prompt()
    logger.info("✅ Prompt Trainer готов")
    
    # Создание приложения
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("table", table_command))
    application.add_handler(CommandHandler("train", train_command))
    application.add_handler(CommandHandler("training_stats", training_stats_command))
    # Оставляем старые команды для обратной совместимости
    application.add_handler(CommandHandler("process", process_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Настройка периодических задач
    setup_job_queue(application)
    
    # Запуск бота
    logger.info("🚀 Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

