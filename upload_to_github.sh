#!/bin/bash

# Скрипт для загрузки файлов в GitHub репозиторий
echo "🚀 Загрузка файлов в GitHub репозиторий..."

# Проверяем, что мы в правильной директории
if [ ! -f "bot_aiogram.py" ]; then
    echo "❌ Файл bot_aiogram.py не найден!"
    echo "Запустите скрипт из директории с файлами бота"
    exit 1
fi

# Инициализируем Git репозиторий (если не инициализирован)
if [ ! -d ".git" ]; then
    echo "📁 Инициализация Git репозитория..."
    git init
    git remote add origin https://github.com/Dmitrij878/Bot.git
fi

# Добавляем все файлы
echo "📦 Добавление файлов..."
git add .

# Создаём коммит
echo "💾 Создание коммита..."
git commit -m "Добавлены файлы бота для Termux"

# Отправляем в GitHub
echo "🚀 Отправка в GitHub..."
git push -u origin main

echo "✅ Файлы успешно загружены в GitHub!"
echo "📋 Теперь можно использовать скрипт установки для Termux" 