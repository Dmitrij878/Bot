#!/bin/bash

# DeepSeek Telegram Bot - Быстрый запуск для Termux
# Простой скрипт для запуска бота без сложной настройки

echo "🤖 DeepSeek Telegram Bot - Быстрый запуск"
echo "=========================================="

# Проверяем, что мы в Termux
if ! command -v termux-setup-storage &> /dev/null; then
    echo "❌ Этот скрипт предназначен только для Termux!"
    exit 1
fi

# Переходим в домашнюю директорию
cd ~

# Проверяем, есть ли уже установленный бот
if [ -d "DeepSeek" ]; then
    echo "📁 Найдена существующая установка..."
    cd DeepSeek
    
    # Проверяем наличие файла бота
    if [ -f "bot_aiogram.py" ]; then
        echo "✅ Бот найден!"
        
        # Проверяем .env
        if [ ! -f ".env" ]; then
            echo "⚠️ Файл .env не найден!"
            echo "Создайте файл .env с вашими настройками:"
            echo ""
            echo "TELEGRAM_TOKEN=your_bot_token"
            echo "OPENROUTER_API_KEY=your_api_key"
            echo "OWNER_ID=your_telegram_id"
            echo "OWNER_IDS=your_telegram_id"
            echo "LOG_CHAT_ID=your_log_chat_id"
            echo ""
            echo "Используйте: nano .env"
            exit 1
        fi
        
        # Проверяем зависимости
        echo "📦 Проверка зависимостей..."
        if ! python -c "import aiogram" 2>/dev/null; then
            echo "📦 Установка зависимостей..."
            pip install -r requirements.txt
        fi
        
        echo "🚀 Запуск бота..."
        echo "💡 Для остановки нажмите Ctrl+C"
        echo ""
        
        # Запускаем бота
        python bot_aiogram.py
        
    else
        echo "❌ Файл bot_aiogram.py не найден!"
        echo "Запустите полную установку: bash termux_setup.sh"
    fi
    
else
    echo "📁 Установка не найдена!"
    echo "Запустите полную установку:"
    echo "bash termux_setup.sh"
fi 