#!/bin/bash

# DeepSeek Telegram Bot - Termux Setup Script
# Автоматическая установка и настройка бота для Termux

echo "🤖 DeepSeek Telegram Bot - Установка для Termux"
echo "================================================"

# Проверяем, что мы в Termux
if ! command -v termux-setup-storage &> /dev/null; then
    echo "❌ Этот скрипт предназначен только для Termux!"
    echo "Запустите его в приложении Termux"
    exit 1
fi

# Обновляем пакеты
echo "📦 Обновление пакетов..."
pkg update -y
pkg upgrade -y

# Устанавливаем необходимые пакеты
echo "🔧 Установка необходимых пакетов..."
pkg install -y python git nano

# Проверяем, что Python установлен
if ! command -v python &> /dev/null; then
    echo "❌ Ошибка: Python не установлен!"
    exit 1
fi

echo "✅ Python установлен: $(python --version)"

# Создаём директорию для проекта
echo "📁 Создание директории проекта..."
mkdir -p ~/DeepSeek
cd ~/DeepSeek

# Клонируем репозиторий (если есть)
if [ -d ".git" ]; then
    echo "📥 Обновление репозитория..."
    git pull
else
    echo "📥 Клонирование репозитория..."
    # Замените на ваш репозиторий
    git clone https://github.com/Dmitrij878/Bot.git .
    
    # Проверяем, что файлы скачались
    if [ ! -f "bot_aiogram.py" ]; then
        echo "⚠️ Файлы бота не найдены в репозитории!"
        echo "📋 Создаём базовые файлы..."
        
        # Создаём базовый bot_aiogram.py
        cat > bot_aiogram.py << 'EOF'
#!/usr/bin/env python3
"""
DeepSeek Telegram Bot
Простой бот для работы с AI моделями
"""

import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Инициализация бота
bot = Bot(token=os.getenv('TELEGRAM_TOKEN'))
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("🤖 Привет! Я DeepSeek бот.\n\nИспользуйте /help для получения справки.")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = """
🤖 **DeepSeek Telegram Bot**

**Основные команды:**
/start - Запуск бота
/help - Справка
/profile - Ваш профиль
/limits - Ваши лимиты

**Для владельцев:**
/ownerhelp - Команды владельца
"""
    await message.answer(help_text, parse_mode="Markdown")

async def main():
    print("🤖 Запуск DeepSeek Telegram Bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
EOF

        # Создаём базовый requirements.txt
        cat > requirements.txt << 'EOF'
# Основные библиотеки для Telegram бота
aiogram>=3.0.0,<4.0.0
python-dotenv>=1.0.0

# HTTP клиент для API запросов
aiohttp>=3.8.0,<4.0.0

# База данных
aiosqlite>=0.19.0

# Дополнительные утилиты
langdetect>=1.0.9
pathlib2>=2.3.7

# Для совместимости с Termux
pydantic>=2.0.0,<2.6.0
pydantic-core>=2.0.0,<2.15.0
EOF

        # Создаём специальный файл для Termux
        cat > requirements_termux.txt << 'EOF'
# DeepSeek Telegram Bot - Зависимости для Termux
# Оптимизированные версии для стабильной работы в Termux

# Основные библиотеки для Telegram бота
aiogram>=3.0.0,<4.0.0
python-dotenv>=1.0.0

# HTTP клиент для API запросов
aiohttp>=3.8.0,<4.0.0

# База данных
aiosqlite>=0.19.0

# Дополнительные утилиты
langdetect>=1.0.9
pathlib2>=2.3.7

# Для совместимости с Termux (более старые версии)
pydantic>=2.0.0,<2.6.0
pydantic-core>=2.0.0,<2.15.0
EOF

        echo "✅ Базовые файлы созданы!"
    fi
fi

# Устанавливаем pip если его нет
if ! command -v pip &> /dev/null; then
    echo "📦 Установка pip..."
    pkg install -y python-pip
fi

# Обновляем pip
echo "🔄 Обновление pip..."
python -m pip install --upgrade pip

# Устанавливаем зависимости
echo "📦 Установка зависимостей Python..."
if [ -f "requirements_termux.txt" ]; then
    echo "📱 Используем оптимизированные зависимости для Termux..."
    pip install -r requirements_termux.txt
else
    echo "📦 Используем стандартные зависимости..."
    pip install -r requirements.txt
fi

# Создаём файл .env если его нет
if [ ! -f ".env" ]; then
    echo "⚙️ Создание файла .env..."
    cat > .env << EOF
# Конфигурация DeepSeek Telegram Bot
# Замените значения на ваши

# Токен вашего Telegram бота (получите у @BotFather)
TELEGRAM_TOKEN=8090535164:AAG5RLekv6Xq9nnhZklJ6qiPKB_WzBSUwdk

# Ключ API OpenRouter (получите на https://openrouter.ai/)
OPENROUTER_API_KEY=d1c373fa0713f35486ee847579f5c6172f8e0b0275af3af3d9faef9fa67a42a5

# Ваш Telegram ID (получите у @userinfobot)
OWNER_ID=7774263220

# Список ID владельцев через запятую
OWNER_IDS=7774263220,1482130292

# ID чата для логов (или ваш ID)
LOG_CHAT_ID=-1002588537040

EOF

    echo "📝 Файл .env создан!"
    echo "⚠️ Отредактируйте файл .env и укажите ваши данные!"
    echo "💡 Используйте команду: nano .env"
fi

# Создаём скрипт запуска
echo "🚀 Создание скрипта запуска..."
cat > start_bot.sh << 'EOF'
#!/bin/bash

# DeepSeek Telegram Bot - Скрипт запуска
cd ~/DeepSeek

echo "🤖 Запуск DeepSeek Telegram Bot..."
echo "📊 Проверка зависимостей..."

# Проверяем наличие .env
if [ ! -f ".env" ]; then
    echo "❌ Файл .env не найден!"
    echo "Создайте файл .env с вашими настройками"
    exit 1
fi

# Проверяем Python
if ! command -v python &> /dev/null; then
    echo "❌ Python не установлен!"
    exit 1
fi

# Проверяем зависимости
if ! python -c "import aiogram" 2>/dev/null; then
    echo "📦 Установка зависимостей..."
    pip install -r requirements.txt
fi

echo "✅ Все проверки пройдены!"
echo "🚀 Запуск бота..."
echo "💡 Для остановки нажмите Ctrl+C"

# Запускаем бота
python bot_aiogram.py
EOF

# Делаем скрипт исполняемым
chmod +x start_bot.sh

# Создаём скрипт для автозапуска
echo "🔄 Создание скрипта автозапуска..."
cat > auto_start.sh << 'EOF'
#!/bin/bash

# DeepSeek Telegram Bot - Автозапуск
# Этот скрипт будет перезапускать бота при сбоях

cd ~/DeepSeek

while true; do
    echo "🤖 Запуск DeepSeek Telegram Bot..."
    echo "⏰ $(date)"
    
    # Запускаем бота
    python bot_aiogram.py
    
    echo "⚠️ Бот остановлен. Перезапуск через 10 секунд..."
    sleep 10
done
EOF

chmod +x auto_start.sh

# Создаём скрипт для остановки
echo "🛑 Создание скрипта остановки..."
cat > stop_bot.sh << 'EOF'
#!/bin/bash

# DeepSeek Telegram Bot - Остановка

echo "🛑 Поиск процессов бота..."
pkill -f "python bot_aiogram.py"
echo "✅ Бот остановлен!"
EOF

chmod +x stop_bot.sh

# Создаём скрипт для просмотра логов
echo "📋 Создание скрипта просмотра логов..."
cat > view_logs.sh << 'EOF'
#!/bin/bash

# DeepSeek Telegram Bot - Просмотр логов

echo "📋 Логи бота:"
echo "=============="

if [ -f "bot.log" ]; then
    tail -f bot.log
else
    echo "Файл логов не найден"
fi
EOF

chmod +x view_logs.sh

# Создаём README для Termux
echo "📖 Создание инструкции для Termux..."
cat > TERMUX_README.md << 'EOF'
# DeepSeek Telegram Bot - Инструкция для Termux

## 🚀 Быстрый запуск

1. **Запуск бота:**
   ```bash
   ./start_bot.sh
   ```

2. **Автозапуск (перезапуск при сбоях):**
   ```bash
   ./auto_start.sh
   ```

3. **Остановка бота:**
   ```bash
   ./stop_bot.sh
   ```

4. **Просмотр логов:**
   ```bash
   ./view_logs.sh
   ```

## ⚙️ Настройка

1. **Редактирование конфигурации:**
   ```bash
   nano .env
   ```

2. **Проверка зависимостей:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Обновление бота:**
   ```bash
   git pull
   pip install -r requirements.txt
   ```

## 📱 Полезные команды Termux

- `termux-setup-storage` - настройка доступа к файлам
- `pkg list-installed` - список установленных пакетов
- `pkg search python` - поиск пакетов
- `top` - мониторинг процессов
- `htop` - расширенный мониторинг (установить: `pkg install htop`)

## 🔧 Решение проблем

### Бот не запускается
1. Проверьте файл `.env` - все ли данные указаны
2. Проверьте интернет соединение
3. Проверьте токен бота у @BotFather

### Ошибки зависимостей
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### Проблемы с правами
```bash
chmod +x *.sh
```

## 📊 Мониторинг

- **Использование памяти:** `free -h`
- **Использование диска:** `df -h`
- **Процессы Python:** `ps aux | grep python`
- **Логи в реальном времени:** `tail -f bot.log`

## 🔄 Автоматизация

Для автозапуска при загрузке Termux добавьте в `~/.bashrc`:
```bash
cd ~/DeepSeek && ./auto_start.sh &
```

## 📞 Поддержка

При проблемах:
1. Проверьте логи: `./view_logs.sh`
2. Перезапустите бота: `./stop_bot.sh && ./start_bot.sh`
3. Обновите зависимости: `pip install -r requirements.txt`
EOF

echo ""
echo "✅ Установка завершена!"
echo ""
echo "📋 Доступные команды:"
echo "  ./start_bot.sh     - Запуск бота"
echo "  ./auto_start.sh    - Автозапуск с перезапуском"
echo "  ./stop_bot.sh      - Остановка бота"
echo "  ./view_logs.sh     - Просмотр логов"
echo ""
echo "⚙️ Настройка:"
echo "  nano .env          - Редактирование конфигурации"
echo ""
echo "📖 Документация:"
echo "  cat TERMUX_README.md - Инструкция для Termux"
echo ""
echo "🚀 Для запуска бота выполните:"
echo "  cd ~/DeepSeek && ./start_bot.sh"
echo ""
echo "💡 Не забудьте настроить файл .env перед запуском!" 