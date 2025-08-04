#!/bin/bash

# DeepSeek Telegram Bot - Исправление зависимостей для Termux
echo "🔧 Исправление зависимостей для Termux..."

# Проверяем, что мы в Termux
if ! command -v termux-setup-storage &> /dev/null; then
    echo "❌ Этот скрипт предназначен только для Termux!"
    exit 1
fi

cd ~/DeepSeek

echo "📦 Установка системных зависимостей..."
pkg install -y python rust

echo "🔄 Обновление pip..."
python -m pip install --upgrade pip setuptools wheel

echo "🧹 Очистка кэша pip..."
pip cache purge

echo "📦 Установка предварительно скомпилированных пакетов..."
pip install --only-binary=all aiogram python-dotenv aiohttp aiosqlite langdetect pathlib2

echo "🔧 Установка pydantic с ограничениями версий..."
pip install "pydantic>=2.0.0,<2.6.0" "pydantic-core>=2.0.0,<2.15.0"

echo "✅ Зависимости исправлены!"
echo "🚀 Теперь можно запустить бота:"
echo "   cd ~/DeepSeek && ./start_bot.sh" 