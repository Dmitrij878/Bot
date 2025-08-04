import os
import logging
import asyncio
import aiohttp
import sqlite3
import re
import math
from dotenv import load_dotenv
from pathlib import Path
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command, CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramRetryAfter
from aiogram.enums import ParseMode
import datetime
# 1. Импорт langdetec
from langdetect import detect
import tempfile
import zipfile
from aiogram.types import InputFile
from aiogram.types.input_file import FSInputFile
import hashlib
import json

# Определение notify_file_changes (и все вспомогательные функции для неё)
# должно быть ДО main()

import hashlib
import json
import re
FILES_STATE_PATH = ".last_files_state.json"
SCAN_FILE = "bot_aiogram.py"

def get_file_hash(path):
    try:
        with open(path, "rb") as f:
            content = f.read()
        return hashlib.md5(content).hexdigest()
    except Exception:
        return None

def analyze_changes(old_content, new_content):
    """Анализирует изменения в файле и возвращает описание"""
    changes = []
    
    # Обеспечиваем, что old_content не None
    old_content = old_content or ""
    
    # Проверяем добавление новых команд
    old_commands = re.findall(r'@dp\.message\(Command\("([^"]+)"\)\)', old_content)
    new_commands = re.findall(r'@dp\.message\(Command\("([^"]+)"\)\)', new_content)
    
    added_commands = set(new_commands) - set(old_commands)
    if added_commands:
        changes.append(f"➕ Добавлены команды: {', '.join(added_commands)}")
    
    # Проверяем исправления ошибок
    if "command.args" in old_content and "message.text.split()" in new_content:
        changes.append("🔧 Исправлена ошибка парсинга аргументов команд")
    
    # Проверяем добавление новых функций
    if "async def cmd_profile" in new_content and "async def cmd_profile" not in old_content:
        changes.append("👤 Добавлена команда /profile с подробной информацией")
    
    if "async def cmd_limits" in new_content and "async def cmd_limits" not in old_content:
        changes.append("📊 Добавлена команда /limits для проверки лимитов")
    
    if "async def cmd_chats" in new_content and "async def cmd_chats" not in old_content:
        changes.append("💬 Добавлена система просмотра чатов пользователей")
    
    if "SPONSOR_CHANNEL_ID" in new_content and "SPONSOR_CHANNEL_ID" not in old_content:
        changes.append("📢 Добавлена система подписки на каналы спонсоров")
    
    if "custom_limit" in new_content and "limit INTEGER" not in old_content:
        changes.append("🔧 Исправлена ошибка SQLite с зарезервированным словом 'limit'")
    
    # Проверяем добавление кнопок
    if "InlineKeyboardBuilder" in new_content and "InlineKeyboardBuilder" not in old_content:
        changes.append("🔘 Добавлены интерактивные кнопки")
    
    # Проверяем улучшения безопасности
    if "is_blacklisted" in new_content and "is_blacklisted" not in old_content:
        changes.append("🛡️ Добавлена система чёрного списка")
    
    # Если не найдено конкретных изменений, возвращаем общее сообщение
    if not changes:
        changes.append("📝 Общие изменения в коде")
    
    return changes

async def notify_file_changes(bot):
    await asyncio.sleep(10)  # Ждём 10 секунд после запуска
    old_state = {}
    old_content = None
    
    if os.path.exists(FILES_STATE_PATH):
        with open(FILES_STATE_PATH, "r", encoding="utf-8") as f:
            old_state = json.load(f)
    
    # Читаем старый контент если есть
    if old_state.get(SCAN_FILE + "_content"):
        old_content = old_state.get(SCAN_FILE + "_content")
    
    new_hash = get_file_hash(SCAN_FILE)
    old_hash = old_state.get(SCAN_FILE)
    
    if new_hash and old_hash and new_hash != old_hash:
        # Читаем новый контент для анализа
        try:
            with open(SCAN_FILE, "r", encoding="utf-8") as f:
                new_content = f.read()
        except Exception:
            new_content = ""
        
        # Анализируем изменения
        changes = analyze_changes(old_content, new_content)
        
        msg = f"<b>🔄 Изменения в {SCAN_FILE}:</b>\n\n"
        for change in changes:
            msg += f"• {change}\n"
        
        try:
            await bot.send_message(LOG_CHAT_ID, msg, parse_mode="HTML")
        except Exception:
            pass
        
        # Сохраняем новый контент для следующего сравнения
        old_state[SCAN_FILE + "_content"] = new_content
        
    elif new_hash and not old_hash:
        msg = f"<b>📁 Файл {SCAN_FILE} добавлен или отслеживается впервые.</b>"
        try:
            await bot.send_message(LOG_CHAT_ID, msg, parse_mode="HTML")
        except Exception:
            pass
    
    # Сохраняем состояние
    old_state[SCAN_FILE] = new_hash
    with open(FILES_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(old_state, f, ensure_ascii=False, indent=2)

# Загрузка переменных окружения
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OWNER_ID = int(os.getenv('OWNER_ID', '0'))
OWNER_IDS = [int(x) for x in os.getenv('OWNER_IDS', '0').split(',')]
LOG_CHAT_ID = os.getenv('LOG_CHAT_ID')

AVAILABLE_MODELS = {
    'deepseek': {
        'id': 'deepseek/deepseek-chat-v3-0324:free',
        'desc': (
            'DeepSeek — универсальная крупная модель, отлично справляется с программированием, анализом данных, сложными задачами и техническими вопросами. Хорошо держит длинный контекст, умеет объяснять и рассуждать, подходит для продвинутых пользователей и разработчиков.\n'
            'Оценки:\n'
            '• Повседневные задачи: 8/10\n'
            '• Общение/чат: 8/10\n'
            '• Генерация кода: 10/10\n'
            '• Объяснения и обучение: 9/10\n'
            '• Креатив/истории: 7/10\n'
            '• Ролевые диалоги: 7/10'
        )
    },
    'openchat': {
        'id': 'mistralai/mistral-7b-instruct:free',
        'desc': (
            'Mistral — универсальная бесплатная модель для чата и повседневных задач. Отличается высокой скоростью, дружелюбным стилем, хорошо подходит для общения, советов, коротких диалогов и быстрой генерации текстов. Поддерживает структурированные ответы, справочную информацию и базовое программирование.\n'
            'Оценки:\n'
            '• Повседневные задачи: 9/10\n'
            '• Общение/чат: 9/10\n'
            '• Генерация кода: 7/10\n'
            '• Объяснения и обучение: 8/10\n'
            '• Креатив/истории: 7/10\n'
            '• Ролевые диалоги: 7/10'
        )
    },
    'mistral': {
        'id': 'mistralai/mistral-7b-instruct',
        'desc': (
            'Mistral — компактная и быстрая модель, даёт краткие, лаконичные и структурированные ответы, хорошо держит контекст, подходит для вопросов-ответов, справочной информации, быстрых советов и коротких диалогов.\n'
            'Оценки:\n'
            '• Повседневные задачи: 8/10\n'
            '• Общение/чат: 8/10\n'
            '• Генерация кода: 7/10\n'
            '• Объяснения и обучение: 8/10\n'
            '• Креатив/истории: 6/10\n'
            '• Ролевые диалоги: 6/10'
        )
    },
    'llama': {
        'id': 'meta-llama/llama-3.1-8b-instruct:free',
        'desc': (
            'Llama 3.1 — новая версия творческой модели от Meta, хорошо подходит для генерации идей, написания историй, ролевых и художественных диалогов. Улучшенная версия с лучшим пониманием контекста и более качественными ответами.\n'
            'Оценки:\n'
            '• Повседневные задачи: 8/10\n'
            '• Общение/чат: 9/10\n'
            '• Генерация кода: 7/10\n'
            '• Объяснения и обучение: 8/10\n'
            '• Креатив/истории: 9/10\n'
            '• Ролевые диалоги: 9/10'
        )
    },
    'mythomax': {
        'id': 'gryphe/mythomax-l2-13b',
        'desc': (
            'MythoMax — специализирована на ролевых, творческих и длинных диалогах, сторителлинге, генерации необычных и художественных текстов. Отлично подходит для игр, ролевых сценариев, фантазий и креативных задач.\n'
            'Оценки:\n'
            '• Повседневные задачи: 6/10\n'
            '• Общение/чат: 7/10\n'
            '• Генерация кода: 5/10\n'
            '• Объяснения и обучение: 6/10\n'
            '• Креатив/истории: 10/10\n'
            '• Ролевые диалоги: 10/10'
        )
    },
}
DEFAULT_MODEL = AVAILABLE_MODELS['deepseek']['id']

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# --- База данных ---
def init_db():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, chat_id INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history (user_id INTEGER, message_id INTEGER, role TEXT, content TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_models (user_id INTEGER PRIMARY KEY, model TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS blacklist (user_id INTEGER PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS group_settings (
        group_id INTEGER PRIMARY KEY,
        mode TEXT,
        allowed_users TEXT
    )''')
    conn.commit()
    conn.close()

def migrate_old_models():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    model_migrations = {
        'meta-llama/llama-2-7b-chat': 'meta-llama/llama-3.1-8b-instruct:free',
        'openchat/openchat-3.5': 'mistralai/mistral-7b-instruct:free',
        'openchat/openchat-3.5-0106': 'mistralai/mistral-7b-instruct:free',
    }
    for old_model, new_model in model_migrations.items():
        c.execute('UPDATE user_models SET model = ? WHERE model = ?', (new_model, old_model))
    conn.commit()
    conn.close()

def set_user_model(user_id, model):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO user_models (user_id, model) VALUES (?, ?)', (user_id, model))
    conn.commit()
    conn.close()

def get_user_model(user_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT model FROM user_models WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    if row and row[0]:
        if row[0] == 'meta-llama/llama-2-7b-chat':
            set_user_model(user_id, 'meta-llama/llama-3.1-8b-instruct:free')
            return 'meta-llama/llama-3.1-8b-instruct:free'
        return row[0]
    return None

def add_to_blacklist(user_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO blacklist (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def remove_from_blacklist(user_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('DELETE FROM blacklist WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def is_blacklisted(user_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT 1 FROM blacklist WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

# --- Вспомогательные функции ---
def convert_markdown_to_telegram(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    text = re.sub(r'~~(.*?)~~', r'<s>\1</s>', text)
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', text)
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[-*_]{3,}$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    return text

# --- Глобальный запуск/остановка ---
GLOBAL_BOT_ENABLED = True

def set_global_bot_enabled(value: bool):
    global GLOBAL_BOT_ENABLED
    GLOBAL_BOT_ENABLED = value

def is_global_bot_enabled():
    return GLOBAL_BOT_ENABLED

# --- Логирование в базу ---
def log_event(event, details, user_id=None, username=None):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        user_id INTEGER,
        username TEXT,
        event TEXT,
        details TEXT
    )''')
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('INSERT INTO logs (date, user_id, username, event, details) VALUES (?, ?, ?, ?, ?)',
              (now, user_id, username, event, details))
    conn.commit()
    conn.close()

# log_suspicious теперь пишет в базу и в LOG_CHAT_ID
import functools
def log_suspicious(text, user_id=None, username=None):
    log_event('suspicious', text, user_id, username)
    if LOG_CHAT_ID:
        from aiogram import Bot
        import asyncio
        async def send():
            bot = Bot(token=TELEGRAM_TOKEN)
            try:
                await bot.send_message(LOG_CHAT_ID, f"⚠️ <b>Подозрительное действие:</b>\n{text}", parse_mode=ParseMode.HTML)
            except Exception:
                pass
        asyncio.create_task(send())

# --- Обработка flood control ---
async def safe_send_message(bot, chat_id, *args, **kwargs):
    while True:
        try:
            return await bot.send_message(chat_id, *args, **kwargs)
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {e}")
            break

async def safe_edit_message(message, *args, **kwargs):
    while True:
        try:
            return await message.edit_text(*args, **kwargs)
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
        except Exception as e:
            logger.error(f"Ошибка редактирования сообщения: {e}")
            break

# --- Основные команды ---
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    chat_id = message.chat.id
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO users (user_id, username, chat_id) VALUES (?, ?, ?)', (user_id, username, chat_id))
    conn.commit()
    conn.close()
    model = get_user_model(user_id) or DEFAULT_MODEL
    model_name = [k for k, v in AVAILABLE_MODELS.items() if v['id'] == model]
    model_name = model_name[0] if model_name else model
    await safe_send_message(message.bot, chat_id, f'Привет! Я бот с моделью <b>{model_name}</b>\nВ личном чате просто напишите сообщение, в группе — ответьте на моё сообщение.\n\nДля списка команд используйте /help', parse_mode=ParseMode.HTML)

@dp.message(Command("help"))
async def cmd_help(message: types.Message, command: CommandObject):
    text = (
        "<b>Доступные команды:</b>\n"
        "/start — начать работу с ботом и узнать текущую модель\n"
        "/help — показать это сообщение\n"
        "/models — список доступных моделей с кнопками для выбора\n"
        "/setmodel &lt;имя&gt; — выбрать модель вручную (короткое или полное имя)\n"
        "/clear — очистить историю диалога и кэш\n"
        "/history — посмотреть историю диалога с пагинацией\n"
        "/language — выбрать язык интерфейса\n"
        "/systemprompt &lt;текст&gt; — задать свой системный промпт для LLM\n"
        "/limits — проверить текущие лимиты и подписки\n"
        "/profile — показать профиль пользователя\n"
        "\n<b>Возможности:</b>\n"
        "• Кэширование одинаковых вопросов (ускоряет ответы и экономит лимит)\n"
        "• Лимиты на количество запросов в сутки (увеличиваются для подписчиков каналов/чатов спонсора)\n"
        "• Кнопки после ответа: 🔄 Повторить, 🌐 Перевести, 👍/👎 Оценить, 🗂 Показать весь диалог\n"
        "• Мультиязычный интерфейс\n"
        "• Поддержка групповых чатов (режимы работы настраиваются владельцем)\n"
        "\n<b>В группе:</b>\n"
        "• Бот отвечает только в reply, по команде или определённым пользователям (настраивается владельцем)\n"
        "\n"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)

@dp.message(Command("ownerhelp"))
async def cmd_ownerhelp(message: types.Message, command: CommandObject):
    if message.from_user.id not in OWNER_IDS:
        await safe_send_message(message.bot, message.chat.id, "Эта команда только для владельца.")
        return
    text = (
        "<b>Команды владельца:</b>\n"
        "/broadcast &lt;текст&gt; — рассылка всем пользователям\n"
        "/stats — расширенная статистика\n"
        "/go — глобальный запуск бота (разрешает отвечать всем)\n"
        "/stop — глобальная остановка бота (бот не отвечает никому, кроме владельца)\n"
        "/migrate — миграция пользователей со старых моделей на новые\n"
        "/block &lt;id&gt; — заблокировать пользователя\n"
        "/unblock &lt;id&gt; — разблокировать пользователя\n"
        "/blacklist — посмотреть чёрный список\n"
        "/groupmode — режим работы в группе (только в группе)\n"
        "/addgroupuser &lt;id&gt; — разрешить пользователю использовать бота в группе (режим users)\n"
        "/removegroupuser &lt;id&gt; — убрать пользователя из разрешённых в группе (режим users)\n"
        "/groupusers — список разрешённых пользователей в группе (режим users)\n"
        "/setlimit &lt;user_id&gt; &lt;число&gt; — установить лимит запросов для пользователя\n"
        "/chats — просмотр чатов пользователей\n"
        "/logs — последние логи\n"
    )
    await safe_send_message(message.bot, message.chat.id, text, parse_mode=ParseMode.HTML)

@dp.message(Command("setlimit"))
async def cmd_setlimit(message: types.Message, command: CommandObject):
    if message.from_user.id not in OWNER_IDS:
        await safe_send_message(message.bot, message.chat.id, "Эта команда только для владельца.")
        return
    
    # Извлекаем аргументы из полного текста сообщения
    parts = message.text.split()
    if len(parts) < 3:
        await safe_send_message(message.bot, message.chat.id, "Использование: /setlimit &lt;user_id&gt; &lt;число&gt;", parse_mode=ParseMode.HTML)
        return
    
    try:
        target_user_id = int(parts[1])
        new_limit = int(parts[2])
        
        if new_limit < 0:
            await safe_send_message(message.bot, message.chat.id, "Лимит не может быть отрицательным.")
            return
        
        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS user_custom_limits (user_id INTEGER PRIMARY KEY, custom_limit INTEGER)')
        c.execute('INSERT OR REPLACE INTO user_custom_limits (user_id, custom_limit) VALUES (?, ?)', (target_user_id, new_limit))
        conn.commit()
        conn.close()
        
        await safe_send_message(message.bot, message.chat.id, f"Лимит для пользователя {target_user_id} установлен: {new_limit} запросов в день.")
        
    except ValueError:
        await safe_send_message(message.bot, message.chat.id, "Некорректный формат. Используйте: /setlimit &lt;user_id&gt; &lt;число&gt;", parse_mode=ParseMode.HTML)
    except Exception as e:
        await safe_send_message(message.bot, message.chat.id, f"Ошибка: {str(e)}")

@dp.message(Command("chats"))
async def cmd_chats(message: types.Message, command: CommandObject):
    if message.from_user.id not in OWNER_IDS:
        await safe_send_message(message.bot, message.chat.id, "Эта команда только для владельца.")
        return
    
    await show_chats_list(message.bot, message.chat.id, sort_by="messages_desc")

async def show_chats_list(bot, chat_id, sort_by="messages_desc", page=1):
    """Показывает список чатов с сортировкой"""
    # Определяем SQL запрос в зависимости от сортировки
    sort_queries = {
        "messages_desc": '''
            SELECT DISTINCT u.user_id, u.username, COUNT(ch.message_id) as msg_count
            FROM users u
            LEFT JOIN chat_history ch ON u.user_id = ch.user_id
            GROUP BY u.user_id
            HAVING msg_count > 0
            ORDER BY msg_count DESC
        ''',
        "messages_asc": '''
            SELECT DISTINCT u.user_id, u.username, COUNT(ch.message_id) as msg_count
            FROM users u
            LEFT JOIN chat_history ch ON u.user_id = ch.user_id
            GROUP BY u.user_id
            HAVING msg_count > 0
            ORDER BY msg_count ASC
        ''',
        "username_asc": '''
            SELECT DISTINCT u.user_id, u.username, COUNT(ch.message_id) as msg_count
            FROM users u
            LEFT JOIN chat_history ch ON u.user_id = ch.user_id
            GROUP BY u.user_id
            HAVING msg_count > 0
            ORDER BY COALESCE(u.username, '') ASC
        ''',
        "username_desc": '''
            SELECT DISTINCT u.user_id, u.username, COUNT(ch.message_id) as msg_count
            FROM users u
            LEFT JOIN chat_history ch ON u.user_id = ch.user_id
            GROUP BY u.user_id
            HAVING msg_count > 0
            ORDER BY COALESCE(u.username, '') DESC
        ''',
        "recent": '''
            SELECT DISTINCT u.user_id, u.username, COUNT(ch.message_id) as msg_count,
                   MAX(ch.message_id) as last_message_id
            FROM users u
            LEFT JOIN chat_history ch ON u.user_id = ch.user_id
            GROUP BY u.user_id
            HAVING msg_count > 0
            ORDER BY last_message_id DESC
        ''',
        "oldest": '''
            SELECT DISTINCT u.user_id, u.username, COUNT(ch.message_id) as msg_count,
                   MIN(ch.message_id) as first_message_id
            FROM users u
            LEFT JOIN chat_history ch ON u.user_id = ch.user_id
            GROUP BY u.user_id
            HAVING msg_count > 0
            ORDER BY first_message_id ASC
        '''
    }
    
    # Получаем список пользователей с чатами
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute(sort_queries[sort_by] + f" LIMIT 20 OFFSET {(page - 1) * 20}")
    users = c.fetchall()
    
    # Получаем общее количество пользователей с чатами
    c.execute('''
        SELECT COUNT(DISTINCT u.user_id)
        FROM users u
        LEFT JOIN chat_history ch ON u.user_id = ch.user_id
        GROUP BY u.user_id
        HAVING COUNT(ch.message_id) > 0
    ''')
    total_users = len(c.fetchall())
    conn.close()
    
    if not users:
        await safe_send_message(bot, chat_id, "Нет чатов для просмотра.")
        return
    
    # Определяем название сортировки
    sort_names = {
        "messages_desc": "📊 По количеству сообщений (убывание)",
        "messages_asc": "📊 По количеству сообщений (возрастание)",
        "username_asc": "👤 По имени пользователя (А-Я)",
        "username_desc": "👤 По имени пользователя (Я-А)",
        "recent": "🕒 По последней активности",
        "oldest": "🕒 По первой активности"
    }
    
    text = f"📱 <b>Список чатов пользователей:</b>\n"
    text += f"🔀 Сортировка: {sort_names[sort_by]}\n"
    text += f"📄 Страница {page} из {max(1, (total_users + 19) // 20)}\n\n"
    
    builder = InlineKeyboardBuilder()
    
    for i, user_data in enumerate(users, 1):
        # Обрабатываем разное количество полей в зависимости от сортировки
        if len(user_data) == 3:
            user_id, username, msg_count = user_data
        elif len(user_data) == 4:
            user_id, username, msg_count, _ = user_data  # Игнорируем дополнительное поле
        else:
            continue  # Пропускаем некорректные данные
            
        display_name = f"@{username}" if username else f"ID: {user_id}"
        text += f"{i}. {display_name} ({msg_count} сообщений)\n"
        builder.button(text=f"{i}. {display_name[:15]}", callback_data=f"view_chat|{user_id}|1")
    
    # Кнопки сортировки
    builder.button(text="📊 По сообщениям ↓", callback_data=f"sort_chats|messages_desc|{page}")
    builder.button(text="📊 По сообщениям ↑", callback_data=f"sort_chats|messages_asc|{page}")
    builder.button(text="👤 По имени А-Я", callback_data=f"sort_chats|username_asc|{page}")
    builder.button(text="👤 По имени Я-А", callback_data=f"sort_chats|username_desc|{page}")
    builder.button(text="🕒 По активности", callback_data=f"sort_chats|recent|{page}")
    builder.button(text="🕒 По старшинству", callback_data=f"sort_chats|oldest|{page}")
    
    # Кнопки навигации
    if page > 1:
        builder.button(text="⬅️ Назад", callback_data=f"sort_chats|{sort_by}|{page-1}")
    if page < (total_users + 19) // 20:
        builder.button(text="Вперёд ➡️", callback_data=f"sort_chats|{sort_by}|{page+1}")
    
    builder.adjust(2, 2, 2, 2, 2, 2, 2)  # 7 строк по 2 кнопки
    
    await safe_send_message(bot, chat_id, text, 
                          reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)

@dp.message(Command("clear"))
async def cmd_clear(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('DELETE FROM chat_history WHERE user_id = ?', (user_id,))
    c.execute('DELETE FROM cache WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    await safe_send_message(message.bot, message.chat.id, "История диалога и кэш очищены!")

@dp.message(Command("limits"))
async def cmd_limits(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # Проверяем подписки
    channel_subscribed = False
    chat_subscribed = False
    
    try:
        member = await message.bot.get_chat_member(SPONSOR_CHANNEL_ID, user_id)
        if member.status in ("member", "administrator", "creator"):
            channel_subscribed = True
    except Exception:
        pass
    
    try:
        member = await message.bot.get_chat_member(SPONSOR_CHAT_ID, user_id)
        if member.status in ("member", "administrator", "creator"):
            chat_subscribed = True
    except Exception:
        pass
    
    # Получаем лимиты
    daily_limit = await get_user_daily_limit(message.bot, user_id)
    current_usage = get_user_limit(user_id)
    
    status_text = f"📊 <b>Ваши лимиты:</b>\n\n"
    status_text += f"Использовано сегодня: {current_usage}/{daily_limit}\n\n"
    
    if channel_subscribed and chat_subscribed:
        status_text += "✅ Подписки: Оба канала\n"
        status_text += f"Бонус: +{CHANNEL_BONUS + CHAT_BONUS} запросов"
    elif channel_subscribed:
        status_text += "⚠️ Подписки: Только Axis Messenger\n"
        status_text += f"Бонус: +{CHANNEL_BONUS} запросов"
    elif chat_subscribed:
        status_text += "⚠️ Подписки: Только Axis Messenger Dev\n"
        status_text += f"Бонус: +{CHAT_BONUS} запросов"
    else:
        status_text += "❌ Подписки: Нет\n"
        status_text += "Бонус: +0 запросов"
    
    builder = InlineKeyboardBuilder()
    if not channel_subscribed:
        builder.button(text="📢 Axis Messenger", url="https://t.me/Axis_Messenger")
    if not chat_subscribed:
        builder.button(text="💻 Axis Messenger Dev", url="https://t.me/AxisMessengerDev")
    if not (channel_subscribed and chat_subscribed):
        builder.button(text="✅ Проверить подписки", callback_data="check_subscriptions")
    
    if builder.buttons:
        builder.adjust(2, 1)
        await safe_send_message(message.bot, chat_id, status_text, 
                              reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)
    else:
        await safe_send_message(message.bot, chat_id, status_text, parse_mode=ParseMode.HTML)

@dp.message(Command("profile"))
async def cmd_profile(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    chat_id = message.chat.id
    username = message.from_user.username or "Не указан"
    first_name = message.from_user.first_name or "Не указано"
    last_name = message.from_user.last_name or ""
    
    # Определяем статус пользователя
    if user_id in OWNER_IDS:
        status = "👑 Владелец"
        status_emoji = "👑"
    elif message.from_user.id == (await message.bot.me()).id:
        status = "🤖 Бот"
        status_emoji = "🤖"
    else:
        status = "👤 Пользователь"
        status_emoji = "👤"
    
    # Проверяем бан
    is_banned = is_blacklisted(user_id)
    ban_status = "🔴 Заблокирован" if is_banned else "🟢 Активен"
    
    # Получаем информацию о лимитах
    daily_limit = await get_user_daily_limit(message.bot, user_id)
    current_usage = get_user_limit(user_id)
    
    # Проверяем подписки
    channel_subscribed = False
    chat_subscribed = False
    
    try:
        member = await message.bot.get_chat_member(SPONSOR_CHANNEL_ID, user_id)
        if member.status in ("member", "administrator", "creator"):
            channel_subscribed = True
    except Exception:
        pass
    
    try:
        member = await message.bot.get_chat_member(SPONSOR_CHAT_ID, user_id)
        if member.status in ("member", "administrator", "creator"):
            chat_subscribed = True
    except Exception:
        pass
    
    # Получаем модель пользователя
    user_model = get_user_model(user_id) or DEFAULT_MODEL
    model_name = next((k for k, v in AVAILABLE_MODELS.items() if v['id'] == user_model), user_model)
    
    # Получаем язык пользователя
    user_language = get_user_language(user_id)
    language_name = LANGUAGES.get(user_language, user_language)
    
    # Получаем системный промпт
    system_prompt = get_user_systemprompt(user_id)
    has_custom_prompt = "✅ Да" if system_prompt else "❌ Нет"
    
    # Получаем статистику сообщений
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM chat_history WHERE user_id = ? AND role = "user"', (user_id,))
    messages_count = c.fetchone()[0] or 0
    c.execute('SELECT COUNT(*) FROM chat_history WHERE user_id = ? AND role = "assistant"', (user_id,))
    responses_count = c.fetchone()[0] or 0
    conn.close()
    
    # Формируем профиль
    profile_text = f"<b>{status_emoji} Профиль пользователя</b>\n\n"
    profile_text += f"<b>ID:</b> <code>{user_id}</code>\n"
    profile_text += f"<b>Имя:</b> {first_name} {last_name}\n"
    profile_text += f"<b>Username:</b> @{username}\n"
    profile_text += f"<b>Статус:</b> {status}\n"
    profile_text += f"<b>Статус аккаунта:</b> {ban_status}\n\n"
    
    profile_text += f"<b>📊 Статистика:</b>\n"
    profile_text += f"• Сообщений отправлено: {messages_count}\n"
    profile_text += f"• Ответов получено: {responses_count}\n"
    profile_text += f"• Использовано сегодня: {current_usage}/{daily_limit}\n\n"
    
    profile_text += f"<b>🔧 Настройки:</b>\n"
    profile_text += f"• Модель: {model_name}\n"
    profile_text += f"• Язык: {language_name}\n"
    profile_text += f"• Кастомный промпт: {has_custom_prompt}\n\n"
    
    profile_text += f"<b>📢 Подписки:</b>\n"
    profile_text += f"• Axis Messenger: {'✅' if channel_subscribed else '❌'}\n"
    profile_text += f"• Axis Messenger Dev: {'✅' if chat_subscribed else '❌'}\n"
    
    # Добавляем информацию для владельцев
    if user_id in OWNER_IDS:
        profile_text += f"\n<b>👑 Привилегии владельца:</b>\n"
        profile_text += f"• Доступ к командам администратора\n"
        profile_text += f"• Управление ботом\n"
        profile_text += f"• Просмотр статистики\n"
        profile_text += f"• Управление чёрным списком"
    
    # Кнопки для действий
    builder = InlineKeyboardBuilder()
    
    # Кнопки для обычных пользователей
    if user_id not in OWNER_IDS:
        builder.button(text="📊 Лимиты", callback_data="show_limits_profile")
        builder.button(text="🔧 Настройки", callback_data="show_settings_profile")
        builder.button(text="📢 Подписки", callback_data="check_subscriptions")
    
    # Кнопки для владельцев (если смотрят свой профиль)
    if user_id in OWNER_IDS:
        builder.button(text="📈 Статистика", callback_data="show_stats_profile")
        builder.button(text="⚙️ Управление", callback_data="show_admin_panel")
    
    # Кнопка для связи с владельцем (если пользователь заблокирован)
    if is_banned and user_id not in OWNER_IDS:
        builder.button(text="📞 Связаться с владельцем", url=f"https://t.me/{OWNER_IDS[0] if OWNER_IDS else 'admin'}")
    
    if builder.buttons:
        builder.adjust(2, 1)
        await safe_send_message(message.bot, chat_id, profile_text, 
                              reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)
    else:
        await safe_send_message(message.bot, chat_id, profile_text, parse_mode=ParseMode.HTML)

@dp.message(Command("models"))
async def cmd_models(message: types.Message, command: CommandObject):
    builder = InlineKeyboardBuilder()
    for k, v in AVAILABLE_MODELS.items():
        builder.button(text=k, callback_data=f"setmodel|{v['id']}")
    text = "<b>Доступные модели:</b>\n" + "\n\n".join([
        f"<b>{k}</b>: <i>{v['id']}</i>\n{v['desc']}" for k, v in AVAILABLE_MODELS.items()
    ])
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)

@dp.callback_query(F.data.startswith("setmodel|"))
async def cb_setmodel(callback: types.CallbackQuery):
    model = callback.data.split("|", 1)[1]
    set_user_model(callback.from_user.id, model)
    model_name = next((k for k, v in AVAILABLE_MODELS.items() if v['id'] == model), model)
    await callback.message.edit_text(f"Модель установлена: <b>{model_name}</b>", parse_mode=ParseMode.HTML)
    await callback.answer()

@dp.message(Command("setmodel"))
async def cmd_setmodel(message: types.Message, command: CommandObject):
    if not command.args:
        await safe_send_message(message.bot, message.chat.id, "Использование: /setmodel &lt;короткое_имя_или_id_модели&gt;", parse_mode=ParseMode.HTML)
        return
    model_key = command.args[0].lower()
    model = AVAILABLE_MODELS.get(model_key, {'id': model_key})['id']
    set_user_model(message.from_user.id, model)
    model_name = next((k for k, v in AVAILABLE_MODELS.items() if v['id'] == model), model)
    await safe_send_message(message.bot, message.chat.id, f"Модель установлена: <b>{model_name}</b>", parse_mode=ParseMode.HTML)

@dp.message(Command("go"))
async def cmd_go(message: types.Message, command: CommandObject):
    if message.from_user.id not in OWNER_IDS:
        await safe_send_message(message.bot, message.chat.id, "Эта команда только для владельца.")
        return
    set_global_bot_enabled(True)
    await safe_send_message(message.bot, message.chat.id, "Бот теперь отвечает всем пользователям.")

@dp.message(Command("stop"))
async def cmd_stop(message: types.Message, command: CommandObject):
    if message.from_user.id not in OWNER_IDS:
        await safe_send_message(message.bot, message.chat.id, "Эта команда только для владельца.")
        return
    set_global_bot_enabled(False)
    await safe_send_message(message.bot, message.chat.id, "Бот остановлен. Теперь отвечает только владельцу.")

@dp.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message, command: CommandObject):
    if message.from_user.id not in OWNER_IDS:
        await safe_send_message(message.bot, message.chat.id, "У вас нет прав для использования этой команды.")
        return
    if not command.args:
        await safe_send_message(message.bot, message.chat.id, "Использование: /broadcast &lt;текст сообщения&gt;", parse_mode=ParseMode.HTML)
        return
    text = message.text.partition(' ')[2]
    sent_count = 0
    failed_count = 0
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT DISTINCT chat_id FROM users')
    users = c.fetchall()
    conn.close()
    status_msg = await safe_send_message(message.bot, message.chat.id, "🔄 Начинаю рассылку...")
    for user in users:
        try:
            await safe_send_message(message.bot, user[0], text, parse_mode=ParseMode.HTML)
            sent_count += 1
        except Exception as e:
            failed_count += 1
            logger.error(f"Ошибка отправки сообщения пользователю {user[0]}: {e}")
    await safe_edit_message(status_msg, f"✅ Рассылка завершена!\n📤 Успешно отправлено: {sent_count}\n❌ Ошибок: {failed_count}")

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message, command: CommandObject):
    if message.from_user.id not in OWNER_IDS:
        await message.answer("У вас нет прав для использования этой команды.")
        return
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    # Всего пользователей
    c.execute('SELECT COUNT(DISTINCT user_id) FROM users')
    total_users = c.fetchone()[0]
    # Всего запросов
    c.execute('SELECT COUNT(*) FROM chat_history WHERE role = "user"')
    total_requests = c.fetchone()[0]
    # Всего ответов
    c.execute('SELECT COUNT(*) FROM chat_history WHERE role = "assistant"')
    total_responses = c.fetchone()[0]
    # Топ-5 активных пользователей
    c.execute('''SELECT u.username, ch.user_id, COUNT(*) as msg_count FROM chat_history ch JOIN users u ON ch.user_id = u.user_id WHERE ch.role = "user" GROUP BY ch.user_id ORDER BY msg_count DESC LIMIT 5''')
    top_users = c.fetchall()
    # Статистика по дням (7 дней)
    c.execute('''SELECT date(substr(rowid,1,10), 'unixepoch'), COUNT(*) FROM chat_history WHERE role = "user" GROUP BY date(substr(rowid,1,10), 'unixepoch') ORDER BY date(substr(rowid,1,10), 'unixepoch') DESC LIMIT 7''')
    days = c.fetchall()
    # По группам (топ-5)
    c.execute('''SELECT chat_id, COUNT(*) as cnt FROM users WHERE chat_id < 0 GROUP BY chat_id ORDER BY cnt DESC LIMIT 5''')
    top_groups = c.fetchall()
    # Лайки/дизлайки
    c.execute('''SELECT feedback, COUNT(*) FROM feedback GROUP BY feedback''')
    fb_stats = dict(c.fetchall())
    # Топ-ответы по лайкам
    c.execute('''SELECT message_id, COUNT(*) as cnt FROM feedback WHERE feedback = 'like' GROUP BY message_id ORDER BY cnt DESC LIMIT 3''')
    top_liked = c.fetchall()
    conn.close()
    stats_text = (
        "📊 <b>Статистика бота</b>\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"💬 Всего запросов: {total_requests}\n"
        f"✅ Всего ответов: {total_responses}\n\n"
        "🏆 <b>Топ-5 активных пользователей:</b>\n"
    )
    for i, (username, uid, count) in enumerate(top_users, 1):
        stats_text += f"{i}. @{username or uid}: {count} сообщений\n"
    stats_text += "\n📅 <b>Запросы за последние 7 дней:</b>\n"
    for day, cnt in days:
        stats_text += f"{day}: {cnt}\n"
    stats_text += "\n👥 <b>Топ-5 групп:</b>\n"
    for i, (gid, cnt) in enumerate(top_groups, 1):
        stats_text += f"{i}. <code>{gid}</code>: {cnt} пользователей\n"
    stats_text += "\n👍 <b>Лайки:</b> {0}   👎 <b>Дизлайки:</b> {1}\n".format(fb_stats.get('like', 0), fb_stats.get('dislike', 0))
    stats_text += "\n🔥 <b>Топ-3 ответа по лайкам:</b>\n"
    for mid, cnt in top_liked:
        stats_text += f"Ответ message_id={mid}: {cnt} 👍\n"
    await message.answer(stats_text, parse_mode=ParseMode.HTML)

@dp.message(Command("block"))
async def cmd_block(message: types.Message, command: CommandObject):
    if message.from_user.id not in OWNER_IDS:
        await safe_send_message(message.bot, message.chat.id, "Эта команда только для владельца.")
        return
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        add_to_blacklist(target_user.id)
        await safe_send_message(message.bot, message.chat.id, f"Пользователь {target_user.mention_html()} (ID: <code>{target_user.id}</code>) добавлен в чёрный список.", parse_mode=ParseMode.HTML)
        return
    if command.args:
        try:
            # Извлекаем ID из полного текста сообщения
            parts = message.text.split()
            if len(parts) > 1:
                target_id = int(parts[1])
            else:
                target_id = int(command.args[0])
            
            add_to_blacklist(target_id)
            await safe_send_message(message.bot, message.chat.id, f"Пользователь с ID <code>{target_id}</code> добавлен в чёрный список.", parse_mode=ParseMode.HTML)
        except Exception as e:
            await safe_send_message(message.bot, message.chat.id, "Некорректный формат ID. Используйте /block &lt;id&gt; или ответьте на сообщение пользователя.", parse_mode=ParseMode.HTML)
        return
    await safe_send_message(message.bot, message.chat.id, "Используйте /block &lt;id&gt; или ответьте на сообщение пользователя.", parse_mode=ParseMode.HTML)

@dp.message(Command("unblock"))
async def cmd_unblock(message: types.Message, command: CommandObject):
    if message.from_user.id not in OWNER_IDS:
        await safe_send_message(message.bot, message.chat.id, "Эта команда только для владельца.")
        return
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        remove_from_blacklist(target_user.id)
        await safe_send_message(message.bot, message.chat.id, f"Пользователь {target_user.mention_html()} (ID: <code>{target_user.id}</code>) удалён из чёрного списка.", parse_mode=ParseMode.HTML)
        return
    if command.args:
        try:
            # Извлекаем ID из полного текста сообщения
            parts = message.text.split()
            if len(parts) > 1:
                target_id = int(parts[1])
            else:
                target_id = int(command.args[0])
            
            remove_from_blacklist(target_id)
            await safe_send_message(message.bot, message.chat.id, f"Пользователь с ID <code>{target_id}</code> удалён из чёрного списка.", parse_mode=ParseMode.HTML)
        except Exception:
            await safe_send_message(message.bot, message.chat.id, "Некорректный формат ID. Используйте /unblock &lt;id&gt; или ответьте на сообщение пользователя.", parse_mode=ParseMode.HTML)
        return
    await safe_send_message(message.bot, message.chat.id, "Используйте /unblock &lt;id&gt; или ответьте на сообщение пользователя.", parse_mode=ParseMode.HTML)

@dp.message(Command("migrate"))
async def cmd_migrate(message: types.Message, command: CommandObject):
    if message.from_user.id not in OWNER_IDS:
        await safe_send_message(message.bot, message.chat.id, "Эта команда только для владельца.")
        return
    await safe_send_message(message.bot, message.chat.id, "🔄 Запускаю миграцию моделей...")
    migrate_old_models()
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT DISTINCT model FROM user_models')
    user_models = [row[0] for row in c.fetchall()]
    invalid_models = []
    for model in user_models:
        if model not in [v['id'] for v in AVAILABLE_MODELS.values()]:
            invalid_models.append(model)
    conn.close()
    if invalid_models:
        await safe_send_message(message.bot, message.chat.id, f"⚠️ Обнаружены пользователи с недействительными моделями:\n{', '.join(invalid_models)}\n\nИспользуйте /setmodel для ручной установки моделей этим пользователям.")
    else:
        await safe_send_message(message.bot, message.chat.id, "✅ Миграция завершена успешно! Все модели актуальны.")

@dp.message(Command("export_chats"))
async def cmd_export_chats(message: types.Message, command: CommandObject):
    if message.from_user.id not in OWNER_IDS:
        await message.answer("Эта команда только для владельца.")
        return
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT DISTINCT user_id FROM chat_history')
    user_ids = [row[0] for row in c.fetchall()]
    temp_dir = tempfile.mkdtemp()
    file_paths = []
    for uid in user_ids:
        c.execute('SELECT username FROM users WHERE user_id = ?', (uid,))
        u = c.fetchone()
        username = u[0] if u and u[0] else str(uid)
        c.execute('SELECT message_id, role, content FROM chat_history WHERE user_id = ? ORDER BY message_id', (uid,))
        rows = c.fetchall()
        if not rows:
            continue
        safe_username = username.replace(' ', '_').replace('@', '')
        file_name = f"{safe_username}_{uid}.txt"
        file_path = os.path.join(temp_dir, file_name)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"user_id: {uid}\nusername: {username}\n\n")
            for mid, role, content in rows:
                f.write(f"{role}: {content}\n")
        file_paths.append(file_path)
    conn.close()
    if not file_paths:
        await message.answer("Нет чатов для экспорта.")
        return
    # Архивируем
    zip_path = os.path.join(temp_dir, "chats_export.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in file_paths:
            zipf.write(file_path, os.path.basename(file_path))
    # Отправляем архив
    input_file = FSInputFile(zip_path, filename="chats_export.zip")
    await message.answer_document(document=input_file, caption="Экспорт всех чатов")
    # Удаляем временные файлы и папку
    for file_path in file_paths:
        os.remove(file_path)
    os.remove(zip_path)
    os.rmdir(temp_dir)
    await message.answer("Экспорт завершён!")

# --- /history с пагинацией ---

@dp.message(Command("history"))
async def cmd_history(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    page = 1
    await send_history_page(message, user_id, page)

@dp.callback_query(F.data.startswith("history|"))
async def cb_history(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    _, page = callback.data.split("|", 1)
    page = int(page)
    await send_history_page(callback.message, user_id, page, callback=callback)

async def send_history_page(msg_obj, user_id, page, callback=None):
    PAGE_SIZE = 10
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT role, content FROM chat_history WHERE user_id = ? ORDER BY message_id DESC', (user_id,))
    all_msgs = c.fetchall()
    conn.close()
    total = len(all_msgs)
    pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(1, min(page, pages))
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    msgs = all_msgs[start:end]
    if not msgs:
        text = "История пуста."
    else:
        text = f"<b>История ({start+1}-{min(end,total)} из {total}):</b>\n\n"
        for role, content in reversed(msgs):
            who = "👤" if role == "user" else "🤖"
            text += f"{who} <i>{role}</i>: {content}\n\n"
    builder = InlineKeyboardBuilder()
    if page > 1:
        builder.button(text="⬅️ Назад", callback_data=f"history|{page-1}")
    if page < pages:
        builder.button(text="Вперёд ➡️", callback_data=f"history|{page+1}")
    if callback:
        await callback.answer()
        await msg_obj.edit_text(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)
    else:
        await msg_obj.answer(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)

# --- Обработка сообщений ---
@dp.message(F.text & ~F.text.startswith("/"))
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    is_private = message.chat.type == "private"
    # В группах отвечаем только на reply к боту
    if not is_private:
        if not message.reply_to_message or message.reply_to_message.from_user.id != (await message.bot.me()).id:
            return
    # Глобальный стоп
    if not is_global_bot_enabled() and user_id not in OWNER_IDS:
        return
    # Чёрный список
    if is_blacklisted(user_id):
        return
    
    # Проверка лимитов
    daily_limit = await get_user_daily_limit(message.bot, user_id)
    current_usage = get_user_limit(user_id)
    if current_usage >= daily_limit:
        builder = InlineKeyboardBuilder()
        builder.button(text="📢 Axis Messenger", url="https://t.me/Axis_Messenger")
        builder.button(text="💻 Axis Messenger Dev", url="https://t.me/AxisMessengerDev")
        builder.button(text="✅ Проверить подписки", callback_data="check_subscriptions")
        builder.adjust(2, 1)
        
        await safe_send_message(message.bot, chat_id, 
            f"Достигнут дневной лимит запросов ({current_usage}/{daily_limit}).\n\n"
            "Подпишитесь на каналы спонсоров для увеличения лимита:",
            reply_markup=builder.as_markup())
        return
    
    # Увеличиваем счетчик использования
    increment_user_limit(user_id)
    
    # Сохраняем сообщение пользователя в историю
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('INSERT INTO chat_history (user_id, message_id, role, content) VALUES (?, ?, ?, ?)', (user_id, message.message_id, 'user', message.text))
    conn.commit()
    # Ограничиваем историю 20 сообщениями
    c.execute('SELECT message_id FROM chat_history WHERE user_id = ? ORDER BY message_id DESC', (user_id,))
    all_ids = [row[0] for row in c.fetchall()]
    if len(all_ids) > 20:
        to_delete = all_ids[20:]
        c.executemany('DELETE FROM chat_history WHERE user_id = ? AND message_id = ?', [(user_id, mid) for mid in to_delete])
        conn.commit()
    # Получаем историю
    c.execute('SELECT content FROM chat_history WHERE user_id = ? ORDER BY message_id DESC LIMIT 5', (user_id,))
    history = c.fetchall()

    user_prompt = get_user_systemprompt(user_id)
    if user_prompt:
        system_prompt = user_prompt
    else:
        system_prompt = "Отвечай только на том языке, на котором тебе написали,  не упоминай про безопасность Telegram, если не спрашивают напрямую."
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message.text}
    ]
    for msg in reversed(history):
        messages.append({"role": "user", "content": msg[0]})
    cached = get_cached_answer(user_id, message.text)
    if cached:
        await safe_send_message(message.bot, chat_id, cached, parse_mode=ParseMode.HTML)
        conn.close()
        return
    model = get_user_model(user_id) or DEFAULT_MODEL
    data = {"model": model, "messages": messages}
    status_msg = await safe_send_message(message.bot, chat_id, "⏳ Обрабатываю ваш запрос...")
    try:
        timeout = aiohttp.ClientTimeout(total=90)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://github.com/your-repo",
                "X-Title": "DeepSeek Telegram Bot"
            }
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    ai_response = result['choices'][0]['message']['content']
                    formatted_response = convert_markdown_to_telegram(ai_response)
                    c.execute('INSERT INTO chat_history (user_id, message_id, role, content) VALUES (?, ?, ?, ?)', (user_id, status_msg.message_id, 'assistant', ai_response))
                    conn.commit()
                    await safe_edit_message(status_msg, formatted_response, parse_mode=ParseMode.HTML)
                    set_cached_answer(user_id, message.text, formatted_response)
                    log_event('api_success', f'Ответ: {formatted_response[:100]}...', user_id, username)
                else:
                    error_text = await response.text()
                    logger.error(f"API Error: {error_text}")
                    await safe_edit_message(status_msg, "Извините, произошла ошибка при обработке вашего запроса. Попробуйте позже.")
                    log_event('api_error', error_text, user_id, username)
    except asyncio.TimeoutError:
        logger.error("Timeout while waiting for API response")
        await safe_edit_message(status_msg, "Извините, время ожидания ответа истекло. Попробуйте позже.")
        log_event('timeout', 'Таймаут API', user_id, username)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        await safe_edit_message(status_msg, "Произошла ошибка при обработке вашего запроса. Попробуйте позже.")
        log_event('critical', str(e), user_id, username)
    finally:
        conn.close()

    # --- Кнопка “🔄 Повторить” ---
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Повторить", callback_data=f"repeat|{message.message_id}")
    builder.button(text="🌐 Перевести", callback_data=f"translate|{status_msg.message_id}")
    builder.button(text="👍", callback_data=f"fb|like|{status_msg.message_id}")
    builder.button(text="👎", callback_data=f"fb|dislike|{status_msg.message_id}")
    builder.button(text="🗂 Показать весь диалог", callback_data="showhistory")
    builder.adjust(5)
    await message.answer(
        formatted_response,
        parse_mode=ParseMode.HTML,
        reply_markup=builder.as_markup()
    )
    await status_msg.delete()

# --- Кнопка “🔄 Повторить” ---
@dp.callback_query(F.data.startswith("repeat|"))
async def cb_repeat(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    _, msg_id = callback.data.split("|", 1)
    # Достать текст из chat_history по message_id и role='user'
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT content FROM chat_history WHERE message_id = ? AND role = ?', (int(msg_id), 'user'))
    orig_msg_text = c.fetchone()[0]
    conn.close()
    # Повторяем запрос как будто пользователь его только что отправил
    # Создаём фейковый объект Message с нужным текстом
    class FakeMessage:
        def __init__(self, text, user_id, chat_id, bot):
            self.text = text
            self.from_user = type('User', (), {'id': user_id})()
            self.chat = type('Chat', (), {'id': chat_id, 'type': 'private'})()
            self.bot = bot
            self.message_id = 0
    fake_message = FakeMessage(orig_msg_text, user_id, callback.message.chat.id, callback.bot)
    await handle_message(fake_message)
    await callback.answer("Повтор запроса")

# --- Кнопка “🌐 Перевести” ---
@dp.callback_query(F.data.startswith("translate|"))
async def cb_translate(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    _, msg_id = callback.data.split("|", 1)
    # Достать текст из chat_history по message_id и role='assistant'
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT content FROM chat_history WHERE message_id = ? AND role = ?', (int(msg_id), 'assistant'))
    orig_answer_text = c.fetchone()[0]
    conn.close()
    lang = get_user_language(user_id)
    lang_name = LANGUAGES.get(lang, lang)
    # Определяем язык исходного текста
    try:
        detected_lang = detect(orig_answer_text)
    except Exception:
        detected_lang = None
    if detected_lang and detected_lang == lang:
        await callback.message.answer("Сообщение уже на выбранном языке.")
        await callback.answer()
        return
    # Формируем prompt для перевода
    prompt = f"Переведи на {lang_name}: {orig_answer_text}"
    # Используем LLM для перевода
    # Можно использовать тот же механизм, что и для обычных сообщений, но с system prompt = 'Ты переводчик...'
    data = {
        "model": get_user_model(user_id) or DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": f"Ты переводчик. Переводи только на {lang_name}. Не добавляй ничего лишнего."},
            {"role": "user", "content": orig_answer_text}
        ]
    }
    status_msg = await callback.message.answer("🌐 Перевожу...")
    try:
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://github.com/your-repo",
                "X-Title": "DeepSeek Telegram Bot"
            }
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    translation = result['choices'][0]['message']['content']
                    await status_msg.edit_text(f"🌐 Перевод на {lang_name}:\n{translation}")
                else:
                    await status_msg.edit_text("Ошибка перевода. Попробуйте позже.")
    except Exception:
        await status_msg.edit_text("Ошибка перевода. Попробуйте позже.")
    await callback.answer("Перевод выполнен")

# --- Лимиты на количество запросов в сутки ---
SPONSOR_CHANNEL_ID = -1002380153628
SPONSOR_CHAT_ID = -1002676367535
BASE_LIMIT = 1000
CHANNEL_BONUS = 500
CHAT_BONUS = 500

# Таблица user_limits: user_id, date, count

def get_today():
    return datetime.date.today().isoformat()

def get_user_limit(user_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS user_limits (user_id INTEGER, date TEXT, count INTEGER, PRIMARY KEY(user_id, date))')
    c.execute('SELECT count FROM user_limits WHERE user_id = ? AND date = ?', (user_id, get_today()))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def increment_user_limit(user_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS user_limits (user_id INTEGER, date TEXT, count INTEGER, PRIMARY KEY(user_id, date))')
    today = get_today()
    c.execute('SELECT count FROM user_limits WHERE user_id = ? AND date = ?', (user_id, today))
    row = c.fetchone()
    if row:
        c.execute('UPDATE user_limits SET count = count + 1 WHERE user_id = ? AND date = ?', (user_id, today))
    else:
        c.execute('INSERT INTO user_limits (user_id, date, count) VALUES (?, ?, 1)', (user_id, today))
    conn.commit()
    conn.close()

async def get_user_daily_limit(bot, user_id):
    limit = BASE_LIMIT
    try:
        member = await bot.get_chat_member(SPONSOR_CHANNEL_ID, user_id)
        if member.status in ("member", "administrator", "creator"):
            limit += CHANNEL_BONUS
    except Exception:
        pass
    try:
        member = await bot.get_chat_member(SPONSOR_CHAT_ID, user_id)
        if member.status in ("member", "administrator", "creator"):
            limit += CHAT_BONUS
    except Exception:
        pass
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS user_custom_limits (user_id INTEGER PRIMARY KEY, custom_limit INTEGER)')
    c.execute('SELECT custom_limit FROM user_custom_limits WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    if row and row[0]:
        limit = row[0]
    conn.close()
    return limit

# --- Кэширование ответов на одинаковые вопросы пользователя ---
CACHE_DAYS = 3

def get_cached_answer(user_id, question):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS cache (
        user_id INTEGER,
        question TEXT,
        answer TEXT,
        date TEXT
    )''')
    cutoff = (datetime.date.today() - datetime.timedelta(days=CACHE_DAYS)).isoformat()
    c.execute('''SELECT answer FROM cache WHERE user_id = ? AND question = ? AND date >= ? ORDER BY date DESC LIMIT 1''', (user_id, question, cutoff))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def set_cached_answer(user_id, question, answer):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    today = datetime.date.today().isoformat()
    c.execute('''INSERT INTO cache (user_id, question, answer, date) VALUES (?, ?, ?, ?)''', (user_id, question, answer, today))
    conn.commit()
    conn.close()

# --- /language: выбор языка интерфейса ---
LANGUAGES = {
    'ru': 'Русский',
    'en': 'English',
    'uk': 'Українська',
    'de': 'Deutsch',
    'fr': 'Français',
    'es': 'Español',
    'it': 'Italiano',
    'zh': '中文',
    'tr': 'Türkçe',
    # и т.д.
}

def set_user_language(user_id, lang):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('ALTER TABLE users ADD COLUMN language TEXT')
    try:
        c.execute('UPDATE users SET language = ? WHERE user_id = ?', (lang, user_id))
    except Exception:
        c.execute('INSERT OR IGNORE INTO users (user_id, language) VALUES (?, ?)', (user_id, lang))
    conn.commit()
    conn.close()

def get_user_language(user_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    try:
        c.execute('SELECT language FROM users WHERE user_id = ?', (user_id,))
        row = c.fetchone()
        if row and row[0]:
            return row[0]
    except Exception:
        pass
    conn.close()
    return 'ru'

# --- /systemprompt: кастомный системный промпт пользователя ---
def set_user_systemprompt(user_id, prompt):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('ALTER TABLE users ADD COLUMN systemprompt TEXT')
    try:
        c.execute('UPDATE users SET systemprompt = ? WHERE user_id = ?', (prompt, user_id))
    except Exception:
        c.execute('INSERT OR IGNORE INTO users (user_id, systemprompt) VALUES (?, ?)', (user_id, prompt))
    conn.commit()
    conn.close()

def get_user_systemprompt(user_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    try:
        c.execute('SELECT systemprompt FROM users WHERE user_id = ?', (user_id,))
        row = c.fetchone()
        if row and row[0]:
            return row[0]
    except Exception:
        pass
    conn.close()
    return None

@dp.message(Command("systemprompt"))
async def cmd_systemprompt(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    if not command.args:
        prompt = get_user_systemprompt(user_id)
        if prompt:
            await message.answer(f"Ваш текущий системный промпт:\n<code>{prompt}</code>", parse_mode=ParseMode.HTML)
        else:
            await message.answer("У вас не задан системный промпт. Используйте /systemprompt <текст>")
        return
    prompt = " ".join(command.args)
    set_user_systemprompt(user_id, prompt)
    await message.answer("Системный промпт сохранён! Теперь он будет добавляться к каждому вашему запросу.")

@dp.message(Command("language"))
async def cmd_language(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    builder = InlineKeyboardBuilder()
    for code, name in LANGUAGES.items():
        builder.button(text=name, callback_data=f"setlang|{code}")
    await message.answer(
        "Выберите язык интерфейса / Choose your language:",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data.startswith("setlang|"))
async def cb_setlang(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    _, lang = callback.data.split("|", 1)
    set_user_language(user_id, lang)
    await callback.answer()
    await callback.message.edit_text(
        "Язык интерфейса изменён! / Language changed!",
        reply_markup=None
    )

@dp.callback_query(F.data == "check_subscriptions")
async def cb_check_subscriptions(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    
    # Проверяем подписки
    channel_subscribed = False
    chat_subscribed = False
    
    try:
        member = await callback.bot.get_chat_member(SPONSOR_CHANNEL_ID, user_id)
        if member.status in ("member", "administrator", "creator"):
            channel_subscribed = True
    except Exception:
        pass
    
    try:
        member = await callback.bot.get_chat_member(SPONSOR_CHAT_ID, user_id)
        if member.status in ("member", "administrator", "creator"):
            chat_subscribed = True
    except Exception:
        pass
    
    # Обновляем лимиты
    daily_limit = await get_user_daily_limit(callback.bot, user_id)
    current_usage = get_user_limit(user_id)
    
    if channel_subscribed and chat_subscribed:
        await callback.answer("✅ Подписки подтверждены! Лимит увеличен.", show_alert=True)
        await callback.message.edit_text(
            f"✅ Подписки подтверждены!\n\n"
            f"Ваш лимит: {current_usage}/{daily_limit}\n"
            f"Теперь вы можете использовать бота.",
            reply_markup=None
        )
    elif channel_subscribed or chat_subscribed:
        await callback.answer("⚠️ Подпишитесь на оба канала для максимального лимита.", show_alert=True)
        builder = InlineKeyboardBuilder()
        if not channel_subscribed:
            builder.button(text="📢 Axis Messenger", url="https://t.me/Axis_Messenger")
        if not chat_subscribed:
            builder.button(text="💻 Axis Messenger Dev", url="https://t.me/AxisMessengerDev")
        builder.button(text="✅ Проверить снова", callback_data="check_subscriptions")
        builder.adjust(2, 1)
        
        await callback.message.edit_text(
            f"⚠️ Подпишитесь на оба канала для максимального лимита.\n\n"
            f"Ваш лимит: {current_usage}/{daily_limit}",
            reply_markup=builder.as_markup()
        )
    else:
        await callback.answer("❌ Подписки не найдены.", show_alert=True)
        builder = InlineKeyboardBuilder()
        builder.button(text="📢 Axis Messenger", url="https://t.me/Axis_Messenger")
        builder.button(text="💻 Axis Messenger Dev", url="https://t.me/AxisMessengerDev")
        builder.button(text="✅ Проверить снова", callback_data="check_subscriptions")
        builder.adjust(2, 1)
        
        await callback.message.edit_text(
            f"❌ Подписки не найдены.\n\n"
            f"Подпишитесь на каналы спонсоров для увеличения лимита.\n"
            f"Ваш лимит: {current_usage}/{daily_limit}",
            reply_markup=builder.as_markup()
        )

# --- Обработчики кнопок профиля ---
@dp.callback_query(F.data == "show_limits_profile")
async def cb_show_limits_profile(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    # Получаем лимиты
    daily_limit = await get_user_daily_limit(callback.bot, user_id)
    current_usage = get_user_limit(user_id)
    
    # Проверяем подписки
    channel_subscribed = False
    chat_subscribed = False
    
    try:
        member = await callback.bot.get_chat_member(SPONSOR_CHANNEL_ID, user_id)
        if member.status in ("member", "administrator", "creator"):
            channel_subscribed = True
    except Exception:
        pass
    
    try:
        member = await callback.bot.get_chat_member(SPONSOR_CHAT_ID, user_id)
        if member.status in ("member", "administrator", "creator"):
            chat_subscribed = True
    except Exception:
        pass
    
    status_text = f"📊 <b>Детальная информация о лимитах:</b>\n\n"
    status_text += f"Использовано сегодня: {current_usage}/{daily_limit}\n"
    status_text += f"Осталось запросов: {daily_limit - current_usage}\n\n"
    
    if channel_subscribed and chat_subscribed:
        status_text += "✅ Подписки: Оба канала\n"
        status_text += f"Бонус: +{CHANNEL_BONUS + CHAT_BONUS} запросов"
    elif channel_subscribed:
        status_text += "⚠️ Подписки: Только Axis Messenger\n"
        status_text += f"Бонус: +{CHANNEL_BONUS} запросов"
    elif chat_subscribed:
        status_text += "⚠️ Подписки: Только Axis Messenger Dev\n"
        status_text += f"Бонус: +{CHAT_BONUS} запросов"
    else:
        status_text += "❌ Подписки: Нет\n"
        status_text += "Бонус: +0 запросов"
    
    builder = InlineKeyboardBuilder()
    if not channel_subscribed:
        builder.button(text="📢 Axis Messenger", url="https://t.me/Axis_Messenger")
    if not chat_subscribed:
        builder.button(text="💻 Axis Messenger Dev", url="https://t.me/AxisMessengerDev")
    builder.button(text="🔙 Назад к профилю", callback_data="back_to_profile")
    builder.adjust(2, 1)
    
    await callback.message.edit_text(status_text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)
    await callback.answer()

@dp.callback_query(F.data == "show_settings_profile")
async def cb_show_settings_profile(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    # Получаем настройки пользователя
    user_model = get_user_model(user_id) or DEFAULT_MODEL
    model_name = next((k for k, v in AVAILABLE_MODELS.items() if v['id'] == user_model), user_model)
    
    user_language = get_user_language(user_id)
    language_name = LANGUAGES.get(user_language, user_language)
    
    system_prompt = get_user_systemprompt(user_id)
    has_custom_prompt = "✅ Да" if system_prompt else "❌ Нет"
    
    settings_text = f"🔧 <b>Настройки пользователя:</b>\n\n"
    settings_text += f"<b>Модель:</b> {model_name}\n"
    settings_text += f"<b>Язык:</b> {language_name}\n"
    settings_text += f"<b>Кастомный промпт:</b> {has_custom_prompt}\n\n"
    
    if system_prompt:
        settings_text += f"<b>Ваш промпт:</b>\n<code>{system_prompt[:100]}{'...' if len(system_prompt) > 100 else ''}</code>\n\n"
    
    settings_text += "Используйте команды для изменения настроек:\n"
    settings_text += "• /models — изменить модель\n"
    settings_text += "• /language — изменить язык\n"
    settings_text += "• /systemprompt — установить промпт"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад к профилю", callback_data="back_to_profile")
    
    await callback.message.edit_text(settings_text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)
    await callback.answer()

@dp.callback_query(F.data == "show_stats_profile")
async def cb_show_stats_profile(callback: types.CallbackQuery):
    if callback.from_user.id not in OWNER_IDS:
        await callback.answer("Нет прав", show_alert=True)
        return
    
    # Получаем статистику бота
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(DISTINCT user_id) FROM users')
    total_users = c.fetchone()[0] or 0
    c.execute('SELECT COUNT(*) FROM chat_history WHERE role = "user"')
    total_requests = c.fetchone()[0] or 0
    c.execute('SELECT COUNT(*) FROM chat_history WHERE role = "assistant"')
    total_responses = c.fetchone()[0] or 0
    conn.close()
    
    stats_text = f"📈 <b>Статистика бота:</b>\n\n"
    stats_text += f"👥 Всего пользователей: {total_users}\n"
    stats_text += f"💬 Всего запросов: {total_requests}\n"
    stats_text += f"✅ Всего ответов: {total_responses}\n"
    stats_text += f"📊 Средняя активность: {total_requests // max(total_users, 1)} запросов на пользователя"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад к профилю", callback_data="back_to_profile")
    
    await callback.message.edit_text(stats_text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)
    await callback.answer()

@dp.callback_query(F.data == "show_admin_panel")
async def cb_show_admin_panel(callback: types.CallbackQuery):
    if callback.from_user.id not in OWNER_IDS:
        await callback.answer("Нет прав", show_alert=True)
        return
    
    admin_text = f"⚙️ <b>Панель управления:</b>\n\n"
    admin_text += f"Доступные команды администратора:\n"
    admin_text += f"• /stats — подробная статистика\n"
    admin_text += f"• /broadcast — рассылка\n"
    admin_text += f"• /block — заблокировать пользователя\n"
    admin_text += f"• /unblock — разблокировать пользователя\n"
    admin_text += f"• /blacklist — чёрный список\n"
    admin_text += f"• /chats — просмотр чатов пользователей\n"
    admin_text += f"• /go — запустить бота\n"
    admin_text += f"• /stop — остановить бота\n"
    admin_text += f"• /migrate — миграция моделей\n"
    admin_text += f"• /export_chats — экспорт чатов"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад к профилю", callback_data="back_to_profile")
    
    await callback.message.edit_text(admin_text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)
    await callback.answer()

@dp.callback_query(F.data == "back_to_profile")
async def cb_back_to_profile(callback: types.CallbackQuery):
    # Симулируем команду /profile
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    username = callback.from_user.username or "Не указан"
    first_name = callback.from_user.first_name or "Не указано"
    last_name = callback.from_user.last_name or ""
    
    # Определяем статус пользователя
    if user_id in OWNER_IDS:
        status = "👑 Владелец"
        status_emoji = "👑"
    elif callback.from_user.id == (await callback.bot.me()).id:
        status = "🤖 Бот"
        status_emoji = "🤖"
    else:
        status = "👤 Пользователь"
        status_emoji = "👤"
    
    # Проверяем бан
    is_banned = is_blacklisted(user_id)
    ban_status = "🔴 Заблокирован" if is_banned else "🟢 Активен"
    
    # Получаем информацию о лимитах
    daily_limit = await get_user_daily_limit(callback.bot, user_id)
    current_usage = get_user_limit(user_id)
    
    # Проверяем подписки
    channel_subscribed = False
    chat_subscribed = False
    
    try:
        member = await callback.bot.get_chat_member(SPONSOR_CHANNEL_ID, user_id)
        if member.status in ("member", "administrator", "creator"):
            channel_subscribed = True
    except Exception:
        pass
    
    try:
        member = await callback.bot.get_chat_member(SPONSOR_CHAT_ID, user_id)
        if member.status in ("member", "administrator", "creator"):
            chat_subscribed = True
    except Exception:
        pass
    
    # Получаем модель пользователя
    user_model = get_user_model(user_id) or DEFAULT_MODEL
    model_name = next((k for k, v in AVAILABLE_MODELS.items() if v['id'] == user_model), user_model)
    
    # Получаем язык пользователя
    user_language = get_user_language(user_id)
    language_name = LANGUAGES.get(user_language, user_language)
    
    # Получаем системный промпт
    system_prompt = get_user_systemprompt(user_id)
    has_custom_prompt = "✅ Да" if system_prompt else "❌ Нет"
    
    # Получаем статистику сообщений
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM chat_history WHERE user_id = ? AND role = "user"', (user_id,))
    messages_count = c.fetchone()[0] or 0
    c.execute('SELECT COUNT(*) FROM chat_history WHERE user_id = ? AND role = "assistant"', (user_id,))
    responses_count = c.fetchone()[0] or 0
    conn.close()
    
    # Формируем профиль
    profile_text = f"<b>{status_emoji} Профиль пользователя</b>\n\n"
    profile_text += f"<b>ID:</b> <code>{user_id}</code>\n"
    profile_text += f"<b>Имя:</b> {first_name} {last_name}\n"
    profile_text += f"<b>Username:</b> @{username}\n"
    profile_text += f"<b>Статус:</b> {status}\n"
    profile_text += f"<b>Статус аккаунта:</b> {ban_status}\n\n"
    
    profile_text += f"<b>📊 Статистика:</b>\n"
    profile_text += f"• Сообщений отправлено: {messages_count}\n"
    profile_text += f"• Ответов получено: {responses_count}\n"
    profile_text += f"• Использовано сегодня: {current_usage}/{daily_limit}\n\n"
    
    profile_text += f"<b>🔧 Настройки:</b>\n"
    profile_text += f"• Модель: {model_name}\n"
    profile_text += f"• Язык: {language_name}\n"
    profile_text += f"• Кастомный промпт: {has_custom_prompt}\n\n"
    
    profile_text += f"<b>📢 Подписки:</b>\n"
    profile_text += f"• Axis Messenger: {'✅' if channel_subscribed else '❌'}\n"
    profile_text += f"• Axis Messenger Dev: {'✅' if chat_subscribed else '❌'}\n"
    
    # Добавляем информацию для владельцев
    if user_id in OWNER_IDS:
        profile_text += f"\n<b>👑 Привилегии владельца:</b>\n"
        profile_text += f"• Доступ к командам администратора\n"
        profile_text += f"• Управление ботом\n"
        profile_text += f"• Просмотр статистики\n"
        profile_text += f"• Управление чёрным списком"
    
    # Кнопки для действий
    builder = InlineKeyboardBuilder()
    
    # Кнопки для обычных пользователей
    if user_id not in OWNER_IDS:
        builder.button(text="📊 Лимиты", callback_data="show_limits_profile")
        builder.button(text="🔧 Настройки", callback_data="show_settings_profile")
        builder.button(text="📢 Подписки", callback_data="check_subscriptions")
    
    # Кнопки для владельцев (если смотрят свой профиль)
    if user_id in OWNER_IDS:
        builder.button(text="📈 Статистика", callback_data="show_stats_profile")
        builder.button(text="⚙️ Управление", callback_data="show_admin_panel")
    
    # Кнопка для связи с владельцем (если пользователь заблокирован)
    if is_banned and user_id not in OWNER_IDS:
        builder.button(text="📞 Связаться с владельцем", url=f"https://t.me/{OWNER_IDS[0] if OWNER_IDS else 'admin'}")
    
    if builder.buttons:
        builder.adjust(2, 1)
        await callback.message.edit_text(profile_text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)
    else:
        await callback.message.edit_text(profile_text, parse_mode=ParseMode.HTML)
    
    await callback.answer()

# --- Обработчики для просмотра чатов ---
@dp.callback_query(F.data.startswith("view_chat|"))
async def cb_view_chat(callback: types.CallbackQuery):
    if callback.from_user.id not in OWNER_IDS:
        await callback.answer("Нет прав", show_alert=True)
        return
    
    _, user_id, page = callback.data.split("|")
    user_id = int(user_id)
    page = int(page)
    
    # Получаем информацию о пользователе
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT username FROM users WHERE user_id = ?', (user_id,))
    user_info = c.fetchone()
    username = user_info[0] if user_info else f"ID: {user_id}"
    
    # Получаем сообщения пользователя
    c.execute('''
        SELECT role, content, message_id 
        FROM chat_history 
        WHERE user_id = ? 
        ORDER BY message_id DESC 
        LIMIT 10 OFFSET ?
    ''', (user_id, (page - 1) * 10))
    messages = c.fetchall()
    
    # Получаем общее количество сообщений
    c.execute('SELECT COUNT(*) FROM chat_history WHERE user_id = ?', (user_id,))
    total_messages = c.fetchone()[0]
    conn.close()
    
    if not messages:
        await callback.answer("Нет сообщений в этом чате", show_alert=True)
        return
    
    # Формируем текст чата
    chat_text = f"💬 <b>Чат с {username}</b>\n"
    chat_text += f"📊 Всего сообщений: {total_messages}\n"
    chat_text += f"📄 Страница {page} из {max(1, (total_messages + 9) // 10)}\n\n"
    
    for role, content, msg_id in reversed(messages):  # Показываем в хронологическом порядке
        if role == "user":
            chat_text += f"👤 <b>Пользователь:</b>\n{content[:200]}{'...' if len(content) > 200 else ''}\n\n"
        else:
            chat_text += f"🤖 <b>Бот:</b>\n{content[:200]}{'...' if len(content) > 200 else ''}\n\n"
    
    # Кнопки навигации
    builder = InlineKeyboardBuilder()
    
    if page > 1:
        builder.button(text="⬅️ Назад", callback_data=f"view_chat|{user_id}|{page-1}")
    
    if page < (total_messages + 9) // 10:
        builder.button(text="Вперёд ➡️", callback_data=f"view_chat|{user_id}|{page+1}")
    
    builder.button(text="📱 Список чатов", callback_data="back_to_chats")
    builder.button(text="🔙 Назад", callback_data="back_to_profile")
    
    builder.adjust(2, 2)
    
    await callback.message.edit_text(chat_text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)
    await callback.answer()

@dp.callback_query(F.data == "back_to_chats")
async def cb_back_to_chats(callback: types.CallbackQuery):
    if callback.from_user.id not in OWNER_IDS:
        await callback.answer("Нет прав", show_alert=True)
        return
    
    await show_chats_list(callback.bot, callback.message.chat.id, "messages_desc", 1)
    await callback.answer()

@dp.callback_query(F.data == "show_chats_from_profile")
async def cb_show_chats_from_profile(callback: types.CallbackQuery):
    if callback.from_user.id not in OWNER_IDS:
        await callback.answer("Нет прав", show_alert=True)
        return
    
    await show_chats_list(callback.bot, callback.message.chat.id, "messages_desc", 1)
    await callback.answer()

@dp.callback_query(F.data.startswith("sort_chats|"))
async def cb_sort_chats(callback: types.CallbackQuery):
    if callback.from_user.id not in OWNER_IDS:
        await callback.answer("Нет прав", show_alert=True)
        return
    
    _, sort_by, page = callback.data.split("|")
    page = int(page)
    
    await show_chats_list(callback.bot, callback.message.chat.id, sort_by, page)
    await callback.answer()

# --- /blacklist: просмотр чёрного списка владельцем ---
@dp.message(Command("blacklist"))
async def cmd_blacklist(message: types.Message, command: CommandObject):
    if message.from_user.id not in OWNER_IDS:
        await message.answer("Эта команда только для владельца.")
        return
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS blacklist (user_id INTEGER PRIMARY KEY)')
    c.execute('SELECT user_id FROM blacklist')
    rows = c.fetchall()
    if not rows:
        await message.answer("Чёрный список пуст.")
        conn.close()
        return
    ids = [str(row[0]) for row in rows]
    # Получаем username
    users = []
    for uid in ids:
        c.execute('SELECT username FROM users WHERE user_id = ?', (uid,))
        u = c.fetchone()
        users.append(f"{uid} (@{u[0]})" if u and u[0] else uid)
    conn.close()
    text = "<b>Чёрный список:</b>\n" + "\n".join(users)
    await message.answer(text, parse_mode=ParseMode.HTML)

# --- Кнопки “👍” и “👎” для обратной связи ---
def save_feedback(user_id, message_id, feedback):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS feedback (
        user_id INTEGER,
        message_id INTEGER,
        feedback TEXT,
        date TEXT
    )''')
    today = datetime.date.today().isoformat()
    c.execute('''INSERT INTO feedback (user_id, message_id, feedback, date) VALUES (?, ?, ?, ?)''', (user_id, message_id, feedback, today))
    conn.commit()
    conn.close()

@dp.callback_query(F.data.startswith("fb|"))
async def cb_feedback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    _, fb, msg_id = callback.data.split("|", 2)
    save_feedback(user_id, int(msg_id), fb)
    # Логирование в LOG_CHAT_ID
    if LOG_CHAT_ID:
        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        # Кто задал вопрос
        c.execute('SELECT user_id, content FROM chat_history WHERE message_id = ? LIMIT 1', (msg_id,))
        row = c.fetchone()
        if row:
            asker_id = row[0]
            prompt = row[1]
        else:
            asker_id = None
            prompt = ''
        # username того, кто задал
        asker_username = None
        if asker_id:
            c.execute('SELECT username FROM users WHERE user_id = ?', (asker_id,))
            u = c.fetchone()
            if u and u[0]:
                asker_username = u[0]
        # username того, кто оценил
        c.execute('SELECT username FROM users WHERE user_id = ?', (user_id,))
        u2 = c.fetchone()
        rater_username = u2[0] if u2 and u2[0] else None
        conn.close()
        fb_emoji = '👍' if fb == 'like' else '👎'
        log_text = f"<b>Оценка ответа</b> {fb_emoji}\n"
        if asker_id == user_id:
            log_text += f"👤 <b>Пользователь:</b> {asker_username or asker_id} (ID: <code>{asker_id}</code>)\n"
        else:
            log_text += f"👤 <b>Запросил:</b> {asker_username or asker_id} (ID: <code>{asker_id}</code>)\n"
            log_text += f"🧑 <b>Оценил:</b> {rater_username or user_id} (ID: <code>{user_id}</code>)\n"
        log_text += f"<b>Промпт:</b> <code>{(prompt or '')[:100]}</code>"
        try:
            await callback.bot.send_message(LOG_CHAT_ID, log_text, parse_mode=ParseMode.HTML)
        except Exception:
            pass
    await callback.answer("Спасибо за оценку!", show_alert=False)

# В обработчике сообщений после safe_edit_message/status_msg:
# builder = InlineKeyboardBuilder()
# builder.button(text="🔄 Повторить", callback_data=f"repeat|{message.text}")
# builder.button(text="🌐 Перевести", callback_data=f"translate|{formatted_response}")
# builder.button(text="👍", callback_data=f"fb|like|{status_msg.message_id}")
# builder.button(text="👎", callback_data=f"fb|dislike|{status_msg.message_id}")
# builder.button(text="🗂 Показать весь диалог", callback_data="showhistory")
# builder.adjust(5)  # Все кнопки в одну строку

# await status_msg.edit_text(
#     formatted_response,
#     parse_mode=ParseMode.HTML,
#     reply_markup=builder.as_markup()
# )

# --- Настройки групповых чатов и команда /groupmode ---
GROUP_MODES = {
    'always': 'Отвечать всегда',
    'command': 'Только по команде',
    'reply': 'Только в reply',
    'users': 'Только определённым пользователям',
    'disabled': 'Не отвечать в этой группе'
}

def set_group_mode(group_id, mode, allowed_users=None):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS group_settings (
        group_id INTEGER PRIMARY KEY,
        mode TEXT,
        allowed_users TEXT
    )''')
    c.execute('INSERT OR REPLACE INTO group_settings (group_id, mode, allowed_users) VALUES (?, ?, ?)',
              (group_id, mode, ','.join(map(str, allowed_users)) if allowed_users else None))
    conn.commit()
    conn.close()

def get_group_mode(group_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS group_settings (
        group_id INTEGER PRIMARY KEY,
        mode TEXT,
        allowed_users TEXT
    )''')
    c.execute('SELECT mode, allowed_users FROM group_settings WHERE group_id = ?', (group_id,))
    row = c.fetchone()
    conn.close()
    if row:
        mode, allowed_users = row
        allowed_users = [int(uid) for uid in allowed_users.split(',')] if allowed_users else []
        return mode, allowed_users
    return 'always', []

@dp.message(Command("groupmode"))
async def cmd_groupmode(message: types.Message, command: CommandObject):
    if message.from_user.id not in OWNER_IDS:
        await message.answer("Эта команда только для владельца.")
        return
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Эту команду можно использовать только в группе.")
        return
    group_id = message.chat.id
    mode, allowed_users = get_group_mode(group_id)
    builder = InlineKeyboardBuilder()
    for k, v in GROUP_MODES.items():
        builder.button(text=v, callback_data=f"setgroupmode|{k}")
    text = f"<b>Текущий режим работы в этой группе:</b>\n{GROUP_MODES.get(mode, mode)}"
    if mode == 'users' and allowed_users:
        text += f"\nРазрешённые пользователи: {', '.join(map(str, allowed_users))}"
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)

@dp.callback_query(F.data.startswith("setgroupmode|"))
async def cb_setgroupmode(callback: types.CallbackQuery):
    if callback.from_user.id not in OWNER_IDS:
        await callback.answer("Нет прав", show_alert=True)
        return
    group_id = callback.message.chat.id
    _, mode = callback.data.split("|", 1)
    set_group_mode(group_id, mode)
    await callback.answer("Режим обновлён")
    await callback.message.edit_text(f"Режим работы в группе обновлён: {GROUP_MODES.get(mode, mode)}")

@dp.message(Command("addgroupuser"))
async def cmd_addgroupuser(message: types.Message, command: CommandObject):
    if message.from_user.id not in OWNER_IDS:
        await message.answer("Эта команда только для владельца.")
        return
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Эту команду можно использовать только в группе.")
        return
    if not command.args:
        await message.answer("Использование: /addgroupuser <user_id>")
        return
    group_id = message.chat.id
    user_id = int(command.args[0])
    mode, allowed_users = get_group_mode(group_id)
    if user_id not in allowed_users:
        allowed_users.append(user_id)
        set_group_mode(group_id, 'users', allowed_users)
    await message.answer(f"Пользователь {user_id} добавлен в разрешённые для этой группы.")

@dp.message(Command("removegroupuser"))
async def cmd_removegroupuser(message: types.Message, command: CommandObject):
    if message.from_user.id not in OWNER_IDS:
        await message.answer("Эта команда только для владельца.")
        return
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Эту команду можно использовать только в группе.")
        return
    if not command.args:
        await message.answer("Использование: /removegroupuser <user_id>")
        return
    group_id = message.chat.id
    user_id = int(command.args[0])
    mode, allowed_users = get_group_mode(group_id)
    if user_id in allowed_users:
        allowed_users.remove(user_id)
        set_group_mode(group_id, 'users', allowed_users)
    await message.answer(f"Пользователь {user_id} удалён из разрешённых для этой группы.")

@dp.message(Command("groupusers"))
async def cmd_groupusers(message: types.Message, command: CommandObject):
    if message.from_user.id not in OWNER_IDS:
        await message.answer("Эта команда только для владельца.")
        return
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Эту команду можно использовать только в группе.")
        return
    group_id = message.chat.id
    mode, allowed_users = get_group_mode(group_id)
    if not allowed_users:
        await message.answer("В этой группе нет разрешённых пользователей.")
        return
    await message.answer("Разрешённые пользователи этой группы: " + ", ".join(map(str, allowed_users)))

def check_env_and_warn():
    missing = []
    if not TELEGRAM_TOKEN:
        missing.append('TELEGRAM_TOKEN')
    if not OPENROUTER_API_KEY:
        missing.append('OPENROUTER_API_KEY')
    if not os.getenv('OWNER_IDS'):
        missing.append('OWNER_IDS')
    if not LOG_CHAT_ID:
        missing.append('LOG_CHAT_ID')
    if missing:
        msg = f"[DeepSeekBot] Не заданы переменные окружения: {', '.join(missing)}.\nБот не будет запущен."
        print(msg)
        # Если есть токен и owner_id, пробуем уведомить владельца
        if TELEGRAM_TOKEN and OWNER_ID:
            import asyncio
            from aiogram import Bot
            async def notify_owner():
                bot = Bot(token=TELEGRAM_TOKEN)
                try:
                    await bot.send_message(OWNER_ID, msg)
                except Exception:
                    pass
            asyncio.run(notify_owner())
        exit(1)

# --- Запуск ---
async def main():
    check_env_and_warn()
    init_db()
    bot = Bot(token=TELEGRAM_TOKEN)
    # Запускаем задачу отслеживания изменений
    asyncio.create_task(notify_file_changes(bot))
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 