#!/data/data/com.termux/files/usr/bin/bash

# Переходим в директорию скрипта
cd "$(dirname "$0")"

# Проверяем наличие Python
if ! command -v python &> /dev/null; then
    echo "Установка Python..."
    pkg update -y
    pkg install python -y
fi

# Проверяем наличие pip
if ! command -v pip &> /dev/null; then
    echo "Установка pip..."
    pkg install pip -y
fi

# Устанавливаем зависимости
echo "Установка зависимостей..."
pip install -r requirements.txt

# Запускаем бота
echo "Запуск бота..."
python bot.py 