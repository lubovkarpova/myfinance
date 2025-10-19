"""
Телеграм бот для учета финансов
"""
import logging
from datetime import datetime
from telegram import Update
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

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальные объекты
sheets_manager = None
categorizer = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    welcome_message = f"""
Привет, {user.first_name}! 👋

Я бот для учета финансов. Просто отправляй мне свои траты и доходы в свободном формате, например:
• "Купил продукты за 1500 рублей"
• "Потратил 300 на кофе"
• "Получил зарплату 50000"
• "+5000 фриланс"

📝 Доступные команды:
/start - Показать это сообщение
/process - Обработать все накопленные сообщения и добавить в Google таблицу
/clear - Очистить накопленные сообщения
/table - Получить ссылку на Google таблицу
/stats - Показать статистику накопленных сообщений
/help - Помощь

Все твои сообщения будут накапливаться, а когда ты напишешь /process, я обработаю их через AI, определю категории и добавлю в таблицу.
"""
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
🤖 Как пользоваться ботом:

1️⃣ Отправляй сообщения о тратах и доходах в свободной форме
2️⃣ Когда накопится несколько сообщений, используй /process
3️⃣ Бот обработает их и добавит в Google таблицу

💡 Примеры сообщений:
• "500 рублей на продукты"
• "Купил кофе 200р"
• "Потратил 1000 на такси"
• "Зарплата 60000"
• "+3000 фриланс"

📋 Команды:
/start - Начать работу
/process - Обработать накопленные сообщения
/clear - Очистить буфер сообщений
/table - Получить ссылку на таблицу
/stats - Статистика накопленных сообщений
/help - Эта помощь

❓ Вопросы? Просто пиши свои траты, бот разберется!
"""
    await update.message.reply_text(help_text)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статистику накопленных сообщений"""
    user_id = update.effective_user.id
    
    if 'messages' not in context.user_data:
        context.user_data['messages'] = []
    
    messages_count = len(context.user_data['messages'])
    
    if messages_count == 0:
        await update.message.reply_text("📭 У тебя пока нет накопленных сообщений.")
    else:
        stats_text = f"📊 Статистика:\n\n"
        stats_text += f"Накоплено сообщений: {messages_count}\n\n"
        stats_text += "Последние сообщения:\n"
        
        for i, msg in enumerate(context.user_data['messages'][-5:], 1):
            stats_text += f"{i}. {msg['text'][:50]}...\n"
        
        stats_text += f"\n💡 Используй /process чтобы обработать их"
    
    await update.message.reply_text(stats_text)


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Очищает накопленные сообщения"""
    if 'messages' in context.user_data:
        count = len(context.user_data['messages'])
        context.user_data['messages'] = []
        await update.message.reply_text(f"🗑 Очищено {count} сообщений")
    else:
        await update.message.reply_text("📭 Нет сообщений для очистки")


async def table_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет ссылку на Google таблицу"""
    if sheets_manager and sheets_manager.spreadsheet:
        url = sheets_manager.get_spreadsheet_url()
        await update.message.reply_text(f"📊 Твоя таблица:\n{url}")
    else:
        await update.message.reply_text("❌ Не удалось получить ссылку на таблицу")


async def process_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /process - обрабатывает все накопленные сообщения"""
    user = update.effective_user
    
    if 'messages' not in context.user_data or len(context.user_data['messages']) == 0:
        await update.message.reply_text("📭 Нет сообщений для обработки. Сначала отправь несколько сообщений о тратах!")
        return
    
    messages = context.user_data['messages']
    await update.message.reply_text(f"⚙️ Обрабатываю {len(messages)} сообщений...\n\nЭто может занять некоторое время.")
    
    try:
        # Обрабатываем каждое сообщение
        transactions = []
        
        for msg_data in messages:
            text = msg_data['text']
            timestamp = msg_data['timestamp']
            
            # Используем OpenAI для категоризации
            parsed = categorizer.parse_transaction(text)
            
            # Формируем данные транзакции
            transaction = {
                'date': timestamp.strftime('%Y-%m-%d'),
                'time': timestamp.strftime('%H:%M:%S'),
                'type': parsed['type'],
                'amount': parsed['amount'],
                'category': parsed['category'],
                'description': parsed['description'],
                'username': user.first_name or user.username or 'Unknown',
                'user_id': str(user.id)
            }
            
            transactions.append(transaction)
        
        # Добавляем в Google Sheets
        if sheets_manager.add_transactions_batch(transactions):
            # Очищаем буфер сообщений
            context.user_data['messages'] = []
            
            success_message = f"""
✅ Успешно обработано и добавлено {len(transactions)} транзакций!

📊 Посмотреть таблицу: /table
"""
            await update.message.reply_text(success_message)
        else:
            await update.message.reply_text("❌ Ошибка при добавлении в таблицу. Попробуй позже.")
    
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщений: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {str(e)}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений - накапливает их для последующей обработки"""
    user = update.effective_user
    text = update.message.text
    
    # Инициализируем список сообщений если его нет
    if 'messages' not in context.user_data:
        context.user_data['messages'] = []
    
    # Добавляем сообщение в буфер
    context.user_data['messages'].append({
        'text': text,
        'timestamp': datetime.now()
    })
    
    # Отправляем подтверждение
    count = len(context.user_data['messages'])
    await update.message.reply_text(
        f"✅ Записал! Всего накоплено: {count} сообщений\n\n"
        f"💡 Используй /process чтобы обработать все сообщения"
    )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Update {update} caused error {context.error}")


def main():
    """Запуск бота"""
    global sheets_manager, categorizer
    
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
    
    # Создание приложения
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("process", process_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CommandHandler("table", table_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запуск бота
    logger.info("🚀 Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

