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
Hey {user.first_name}! 👋
I'm your money tracker bot. Just drop me messages like:

"Bought groceries 1500₽"
"300₽ on coffee"
"Salary 50k"
"+5k freelance"

I'll stash them till you run /process.

🛠 Commands:
/start – This intro
/process – Parse all messages, send to Google Sheets
/clear – Wipe the message buffer
/table – Get your Sheets link
/stats – See what's saved
/help – Quick guide
"""
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
👾 How to use me:

Send spendings/incomes in plain text
Run /process once you've sent a few
I'll sort them and log everything to Google Sheets

💬 Examples:
"500₽ groceries"
"Coffee 200"
"Taxi 1k"
"Salary 60k"
"+3k freelance"

🧰 Commands:
/start – Intro
/process – Log stuff
/clear – Clean up messages
/table – Your Sheets link
/stats – What's saved
/help – You're here

Got questions? Just text me what you spent. I got you.
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
            
            # Формируем данные транзакции
            transaction = {
                'date': timestamp.strftime('%d-%m-%y'),  # Используем дефисы вместо слэшей
                'type': parsed['type'],
                'description': parsed['description'],
                'category': parsed['category'],
                'amount': parsed['amount'],
                'currency': parsed.get('currency', 'ILS'),
                'amount_ils': parsed.get('amount_ils', parsed['amount']),
                'username': user.first_name or user.username or 'Unknown'
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
        f"✅ Got it! {count} messages saved.\n\n"
        f"💡 Run /process to log them."
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

