# 🚀 Быстрый старт

## Шаг 1: Установка зависимостей

```bash
pip install -r requirements.txt
```

## Шаг 2: Создание .env файла

Создайте файл `.env` в корне проекта:

```env
TELEGRAM_BOT_TOKEN=ваш_токен_от_botfather
OPENAI_API_KEY=ваш_ключ_openai
GOOGLE_CREDENTIALS_FILE=my-finance-475615-72e35dbf9d52.json
SPREADSHEET_NAME=Финансы
```

### Где взять токены:

1. **TELEGRAM_BOT_TOKEN**: 
   - Напишите [@BotFather](https://t.me/botfather) в Telegram
   - Отправьте `/newbot`
   - Следуйте инструкциям
   - Скопируйте токен

2. **OPENAI_API_KEY**:
   - Зайдите на [platform.openai.com](https://platform.openai.com/)
   - Зарегистрируйтесь/войдите
   - Перейдите в API Keys
   - Создайте новый ключ

## Шаг 3: Запуск

```bash
python bot.py
```

Или используйте скрипт:

```bash
./start.sh
```

## Шаг 4: Использование

1. Найдите своего бота в Telegram
2. Отправьте `/start`
3. Начните отправлять сообщения о тратах:
   - "Купил продукты за 1500"
   - "Потратил 300 на кофе"
4. Когда накопится несколько сообщений, отправьте `/process`
5. Бот обработает всё и добавит в Google таблицу
6. Используйте `/table` чтобы получить ссылку на таблицу

## Готово! 🎉

Теперь у вас есть личный финансовый ассистент!

