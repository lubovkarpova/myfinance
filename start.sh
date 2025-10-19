#!/bin/bash

# Скрипт для быстрого запуска бота

echo "🤖 Запуск Финансового бота..."

# Проверка наличия .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo "📝 Создайте файл .env на основе env_example.txt"
    exit 1
fi

# Проверка наличия Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не установлен!"
    exit 1
fi

# Проверка наличия requirements
if [ ! -f requirements.txt ]; then
    echo "❌ Файл requirements.txt не найден!"
    exit 1
fi

# Установка зависимостей
echo "📦 Проверка зависимостей..."
pip3 install -r requirements.txt > /dev/null 2>&1

# Запуск бота
echo "🚀 Запуск бота..."
python3 bot.py

