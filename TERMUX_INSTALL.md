# DeepSeek Telegram Bot - Установка в Termux

## 📱 Подготовка Termux

### 1. Установка Termux
- Скачайте Termux с [F-Droid](https://f-droid.org/packages/com.termux/)
- Или с [GitHub Releases](https://github.com/termux/termux-app/releases)

### 2. Настройка Termux
```bash
# Обновление пакетов
pkg update && pkg upgrade

# Установка необходимых пакетов
pkg install python git nano

# Настройка доступа к файлам
termux-setup-storage
```

## 🚀 Быстрая установка

### Вариант 1: Автоматическая установка
```bash
# Скачиваем скрипт установки
curl -O https://raw.githubusercontent.com/your-username/DeepSeek/main/termux_setup.sh

# Делаем исполняемым
chmod +x termux_setup.sh

# Запускаем установку
bash termux_setup.sh
```

### Вариант 2: Ручная установка
```bash
# Создаём директорию
mkdir ~/DeepSeek
cd ~/DeepSeek

# Клонируем репозиторий
git clone https://github.com/your-username/DeepSeek.git .

# Устанавливаем зависимости
pip install -r requirements.txt

# Создаём конфигурацию
nano .env
```

## ⚙️ Настройка

### 1. Создание файла .env
```bash
nano .env
```

Добавьте следующие строки:
```env
TELEGRAM_TOKEN=your_bot_token_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
OWNER_ID=your_telegram_id_here
OWNER_IDS=your_telegram_id_here
LOG_CHAT_ID=your_log_chat_id_here
```

### 2. Получение необходимых данных

#### Telegram Bot Token
1. Напишите @BotFather в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Скопируйте полученный токен

#### OpenRouter API Key
1. Зарегистрируйтесь на [OpenRouter](https://openrouter.ai/)
2. Перейдите в раздел API Keys
3. Создайте новый ключ
4. Скопируйте ключ

#### Telegram ID
1. Напишите @userinfobot в Telegram
2. Скопируйте ваш ID

## 🚀 Запуск

### Быстрый запуск
```bash
cd ~/DeepSeek
bash quick_start.sh
```

### Обычный запуск
```bash
cd ~/DeepSeek
python bot_aiogram.py
```

### Автозапуск с перезапуском
```bash
cd ~/DeepSeek
bash auto_start.sh
```

## 📋 Управление ботом

### Запуск
```bash
cd ~/DeepSeek
./start_bot.sh
```

### Остановка
```bash
cd ~/DeepSeek
./stop_bot.sh
```

### Просмотр логов
```bash
cd ~/DeepSeek
./view_logs.sh
```

### Автозапуск при сбоях
```bash
cd ~/DeepSeek
./auto_start.sh
```

## 🔧 Решение проблем

### Ошибка "Python не найден"
```bash
pkg install python
```

### Ошибка "pip не найден"
```bash
pkg install python-pip
```

### Ошибки зависимостей
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### Проблемы с правами
```bash
chmod +x *.sh
```

### Бот не запускается
1. Проверьте файл `.env`
2. Проверьте интернет соединение
3. Проверьте токен бота

### Ошибки API
1. Проверьте ключ OpenRouter
2. Проверьте лимиты API
3. Проверьте интернет соединение

## 📊 Мониторинг

### Системные ресурсы
```bash
# Использование памяти
free -h

# Использование диска
df -h

# Процессы
ps aux | grep python
```

### Логи бота
```bash
# Просмотр логов в реальном времени
tail -f bot.log

# Последние 50 строк
tail -50 bot.log
```

## 🔄 Обновление

### Обновление кода
```bash
cd ~/DeepSeek
git pull
```

### Обновление зависимостей
```bash
cd ~/DeepSeek
pip install -r requirements.txt --upgrade
```

### Полное обновление
```bash
cd ~/DeepSeek
git pull
pip install -r requirements.txt --upgrade
```

## 📱 Полезные команды Termux

### Система
```bash
pkg list-installed    # Установленные пакеты
pkg search python     # Поиск пакетов
pkg update            # Обновление пакетов
```

### Файлы
```bash
ls -la               # Список файлов
nano filename        # Редактор
cat filename         # Просмотр файла
```

### Процессы
```bash
top                  # Мониторинг процессов
htop                 # Расширенный мониторинг
pkill process_name   # Убить процесс
```

### Сеть
```bash
ping google.com      # Проверка интернета
curl ifconfig.me     # Внешний IP
```

## 🔄 Автоматизация

### Автозапуск при загрузке Termux
Добавьте в `~/.bashrc`:
```bash
cd ~/DeepSeek && ./auto_start.sh &
```

### Регулярные проверки
Создайте скрипт `check_bot.sh`:
```bash
#!/bin/bash
if ! pgrep -f "python bot_aiogram.py" > /dev/null; then
    cd ~/DeepSeek && ./start_bot.sh &
fi
```

## 📞 Поддержка

### Полезные ссылки
- [Termux Wiki](https://wiki.termux.com/)
- [Python в Termux](https://wiki.termux.com/wiki/Python)
- [Git в Termux](https://wiki.termux.com/wiki/Git)

### Частые проблемы
1. **Бот не отвечает** - проверьте интернет и токен
2. **Ошибки API** - проверьте ключ OpenRouter
3. **Высокое потребление ресурсов** - перезапустите бота
4. **Проблемы с правами** - выполните `chmod +x *.sh`

### Логи для отладки
```bash
cd ~/DeepSeek
python bot_aiogram.py 2>&1 | tee bot_debug.log
```

---

**Версия**: 1.0.0  
**Последнее обновление**: Август 2025  
**Совместимость**: Termux 0.118+ 