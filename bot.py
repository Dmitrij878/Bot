import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import aiohttp
import json
from dotenv import load_dotenv
from pathlib import Path
import re
from datetime import datetime
import asyncio
import sqlite3
from typing import Dict, List
import base64
import urllib.parse
from telegram.error import RetryAfter

# Загрузка переменных окружения
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler()  # Вывод в консоль
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
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
OWNER_ID = int(os.getenv('OWNER_ID', '0'))  # ID владельца бота
LOG_CHAT_ID = os.getenv('LOG_CHAT_ID')  # ID чата для логов

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, username TEXT, chat_id INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history
                 (user_id INTEGER, message_id INTEGER, role TEXT, content TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_models (user_id INTEGER PRIMARY KEY, model TEXT)''')
    
    # Миграция старых моделей на новые
    migrate_old_models()
    
    conn.commit()
    conn.close()

def migrate_old_models():
    """Мигрирует пользователей со старых недействительных моделей на новые"""
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    
    # Словарь старых моделей и их новых аналогов
    model_migrations = {
        'meta-llama/llama-2-7b-chat': 'meta-llama/llama-3.1-8b-instruct:free',
        'openchat/openchat-3.5': 'mistralai/mistral-7b-instruct:free',
        'openchat/openchat-3.5-0106': 'mistralai/mistral-7b-instruct:free',
    }
    
    for old_model, new_model in model_migrations.items():
        c.execute('UPDATE user_models SET model = ? WHERE model = ?', (new_model, old_model))
        if c.rowcount > 0:
            logger.info(f"Мигрировано {c.rowcount} пользователей с модели {old_model} на {new_model}")
    
    conn.commit()
    conn.close()

# Проверка наличия необходимых переменных окружения
if not TELEGRAM_TOKEN or not OPENROUTER_API_KEY:
    logger.error("Отсутствуют необходимые переменные окружения!")
    raise ValueError("Пожалуйста, проверьте наличие TELEGRAM_TOKEN и OPENROUTER_API_KEY в файле .env")

if not OWNER_ID:
    logger.warning("OWNER_ID не установлен! Команды владельца будут недоступны.")

if not LOG_CHAT_ID:
    logger.warning("LOG_CHAT_ID не установлен! Логи не будут отправляться в чат.")

# Словарь для хранения статусов печати
typing_status: Dict[int, bool] = {}

class TelegramLogHandler(logging.Handler):
    def __init__(self, bot, chat_id):
        super().__init__()
        self.bot = bot
        self.chat_id = chat_id

    def emit(self, record):
        try:
            msg = self.format(record)
            asyncio.create_task(self.bot.send_message(
                chat_id=self.chat_id,
                text=f"<b>LOG [{record.levelname}]</b>\n{msg}",
                parse_mode='HTML'
            ))
        except Exception as e:
            print(f"Ошибка отправки лога: {e}")

def convert_markdown_to_telegram(text):
    # Заменяем жирный текст
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    # Заменяем курсив
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    # Заменяем зачеркнутый текст
    text = re.sub(r'~~(.*?)~~', r'<s>\1</s>', text)
    # Заменяем код
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    # Заменяем ссылки
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', text)
    # Удаляем заголовки, оставляя только текст
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    # Удаляем горизонтальные линии
    text = re.sub(r'^[-*_]{3,}$', '', text, flags=re.MULTILINE)
    # Удаляем лишние переносы строк
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Удаляем пробелы в начале и конце
    text = text.strip()
    return text

async def is_owner(update: Update) -> bool:
    """Проверяет, является ли пользователь владельцем бота"""
    return update.effective_user.id == OWNER_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    chat_id = update.effective_chat.id

    # Сохраняем пользователя в базу данных
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO users (user_id, username, chat_id) VALUES (?, ?, ?)',
              (user_id, username, chat_id))
    conn.commit()
    conn.close()

    # Получаем выбранную модель
    model = get_user_model(user_id) or DEFAULT_MODEL
    model_name = [k for k, v in AVAILABLE_MODELS.items() if v['id'] == model]
    model_name = model_name[0] if model_name else model

    await update.message.reply_text(
        f'Привет! Я бот с моделью <b>{model_name}</b>\n'
        'В личном чате просто напишите сообщение, в группе — ответьте на моё сообщение.\n\n'
        'Для списка команд используйте /help',
        parse_mode='HTML'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "<b>Доступные команды:</b>\n"
        "/start — начать работу с ботом и узнать текущую модель\n"
        "/help — показать это сообщение\n"
        "/models — список доступных моделей с кнопками для выбора\n"
        "/setmodel &lt;имя&gt; — выбрать модель вручную (короткое или полное имя)\n"
        "/clear — очистить историю диалога\n"
        "\n<b>Просто напишите сообщение — бот ответит через выбранную модель.</b>"
    )
    await update.message.reply_text(text, parse_mode='HTML')

async def ownerhelp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update):
        await update.message.reply_text("Эта команда только для владельца.")
        return
    text = (
        "<b>Команды владельца:</b>\n"
        "/broadcast &lt;текст&gt; — рассылка всем пользователям\n"
        "/stats — статистика использования\n"
        "/go — глобальный запуск бота (разрешает отвечать всем)\n"
        "/stop — глобальная остановка бота (бот не отвечает никому, кроме владельца)\n"
        "/migrate — миграция пользователей со старых моделей на новые\n"
        "/block &lt;id&gt; — заблокировать пользователя\n"
        "/unblock &lt;id&gt; — разблокировать пользователя\n"
    )
    await update.message.reply_text(text, parse_mode='HTML')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем, что update.message не None и содержит текст
    if update.message is None or update.message.text is None:
        return

    user_message = update.message.text
    if not update.message or update.message.chat_id is None:
        return
    chat_id = update.message.chat_id
    
    # Проверяем, что effective_user не None
    if not hasattr(update, 'effective_user') or update.effective_user is None or not hasattr(update.effective_user, 'id') or update.effective_user.id is None:
        logger.warning(f"Received update without effective user: {update}")
        return
        
    user_id = update.effective_user.id
    username = update.effective_user.username if hasattr(update.effective_user, 'username') and update.effective_user.username else "Unknown"
    is_private = update.effective_chat.type == 'private' if hasattr(update, 'effective_chat') and update.effective_chat and hasattr(update.effective_chat, 'type') else False

    # Проверяем условия для ответа
    if not is_private and (not update.message or not hasattr(update.message, 'reply_to_message') or not update.message.reply_to_message):
        return
    if not is_private and update.message and hasattr(update.message, 'reply_to_message') and update.message.reply_to_message and hasattr(update.message.reply_to_message, 'from_user') and update.message.reply_to_message.from_user and update.message.reply_to_message.from_user.id != context.bot.id:
        return

    # Отправляем статус печати
    typing_status[chat_id] = True
    if not hasattr(update.message, 'reply_text') or update.message.reply_text is None:
        return
    status_message = await safe_reply_text(update.message, "⏳ Обрабатываю ваш запрос...")
    
    try:
        # Открываем соединение с базой данных
        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        
        # Сохраняем сообщение пользователя в историю
        c.execute('INSERT INTO chat_history (user_id, message_id, role, content) VALUES (?, ?, ?, ?)',
                  (user_id, update.message.message_id, 'user', user_message))
        conn.commit()

        timeout = aiohttp.ClientTimeout(total=90)  # 90 секунд таймаут
        async with aiohttp.ClientSession(timeout=timeout) as session:
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://github.com/your-repo",
                "X-Title": "DeepSeek Telegram Bot"
            }
            
            # Получаем историю диалога
            c.execute('SELECT content FROM chat_history WHERE user_id = ? ORDER BY message_id DESC LIMIT 5',
                     (user_id,))
            history = c.fetchall()
            messages = [{"role": "user", "content": user_message}]
            for msg in reversed(history):
                messages.append({"role": "user", "content": msg[0]})
            
            # Глобальный стоп: если не владелец и бот выключен — не отвечаем
            if not is_global_bot_enabled() and user_id != OWNER_ID:
                return
            # Чёрный список: если пользователь в чёрном списке — не отвечаем
            if is_blacklisted(user_id):
                return
            # Получаем модель пользователя или дефолтную
            model = get_user_model(user_id) or DEFAULT_MODEL
            data = {
                "model": model,
                "messages": messages
            }

            try:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        ai_response = result['choices'][0]['message']['content']
                        formatted_response = convert_markdown_to_telegram(ai_response)
                        
                        # Сохраняем ответ бота в историю
                        c.execute('INSERT INTO chat_history (user_id, message_id, role, content) VALUES (?, ?, ?, ?)',
                                 (user_id, status_message.message_id, 'assistant', ai_response))
                        conn.commit()
                        
                        # Удаляем статусное сообщение
                        try:
                            await status_message.delete()
                        except RetryAfter as e:
                            await asyncio.sleep(int(e.retry_after))
                        await status_message.delete()
                        
                        # Отправляем ответ
                        await update.message.reply_text(
                            formatted_response,
                            parse_mode='HTML'
                        )
                        
                        # Логируем успешный запрос
                        if LOG_CHAT_ID:
                            log_message = (
                                f"✅ <b>Успешный запрос</b>\n"
                                f"👤 Пользователь: {username} (ID: {user_id})\n"
                                f"💬 Запрос: {user_message}\n"
                                f"📝 Ответ: {formatted_response[:100]}..."
                            )
                            await context.bot.send_message(
                                chat_id=LOG_CHAT_ID,
                                text=log_message,
                                parse_mode='HTML'
                            )
                    else:
                        error_text = await response.text()
                        logger.error(f"API Error: {error_text}")
                        await status_message.delete()
                        await update.message.reply_text(
                            "Извините, произошла ошибка при обработке вашего запроса. Попробуйте позже."
                        )
                        
                        if LOG_CHAT_ID:
                            log_message = (
                                f"❌ <b>Ошибка API</b>\n"
                                f"👤 Пользователь: {username} (ID: {user_id})\n"
                                f"💬 Запрос: {user_message}\n"
                                f"⚠️ Ошибка: {error_text}"
                            )
                            await context.bot.send_message(
                                chat_id=LOG_CHAT_ID,
                                text=log_message,
                                parse_mode='HTML'
                            )
            except asyncio.TimeoutError:
                logger.error("Timeout while waiting for API response")
                await status_message.delete()
                await update.message.reply_text(
                    "Извините, время ожидания ответа истекло. Попробуйте позже."
                )
                
                if LOG_CHAT_ID:
                    log_message = (
                        f"⏰ <b>Таймаут API</b>\n"
                        f"👤 Пользователь: {username} (ID: {user_id})\n"
                        f"💬 Запрос: {user_message}"
                    )
                    await context.bot.send_message(
                        chat_id=LOG_CHAT_ID,
                        text=log_message,
                        parse_mode='HTML'
                    )

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        await status_message.delete()
        await update.message.reply_text(
            "Произошла ошибка при обработке вашего запроса. Попробуйте позже."
        )
        
        if LOG_CHAT_ID:
            log_message = (
                f"❌ <b>Критическая ошибка</b>\n"
                f"👤 Пользователь: {username} (ID: {user_id})\n"
                f"💬 Запрос: {user_message}\n"
                f"⚠️ Ошибка: {str(e)}"
            )
            await context.bot.send_message(
                chat_id=LOG_CHAT_ID,
                text=log_message,
                parse_mode='HTML'
            )
    finally:
        typing_status[chat_id] = False
        # Закрываем соединение с базой данных
        if 'conn' in locals():
            try:
                conn.close()
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Очищает историю диалога пользователя"""
    user_id = update.effective_user.id
    
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('DELETE FROM chat_history WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    await update.message.reply_text("История диалога очищена!")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет сообщение всем пользователям бота"""
    if not await is_owner(update):
        await update.message.reply_text("У вас нет прав для использования этой команды.")
        return
    
    if not context.args:
        await update.message.reply_text("Использование: /broadcast <текст сообщения>")
        return
    
    # Преобразуем Markdown в HTML для поддержки ссылок и форматирования
    message = convert_markdown_to_telegram(" ".join(context.args))
    sent_count = 0
    failed_count = 0
    
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT DISTINCT chat_id FROM users')
    users = c.fetchall()
    conn.close()
    
    status_message = await update.message.reply_text("🔄 Начинаю рассылку...")
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user[0],
                text=message,
                parse_mode='HTML'
            )
            sent_count += 1
        except Exception as e:
            failed_count += 1
            logger.error(f"Ошибка отправки сообщения пользователю {user[0]}: {e}")
    
    await status_message.edit_text(
        f"✅ Рассылка завершена!\n"
        f"📤 Успешно отправлено: {sent_count}\n"
        f"❌ Ошибок: {failed_count}"
    )

# --- Глобальный запуск/остановка ---
GLOBAL_BOT_ENABLED = True

def set_global_bot_enabled(value: bool):
    global GLOBAL_BOT_ENABLED
    GLOBAL_BOT_ENABLED = value

def is_global_bot_enabled():
    return GLOBAL_BOT_ENABLED

async def go_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update):
        await update.message.reply_text("Эта команда только для владельца.")
        return
    set_global_bot_enabled(True)
    await update.message.reply_text("Бот теперь отвечает всем пользователям.")

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update):
        await update.message.reply_text("Эта команда только для владельца.")
        return
    set_global_bot_enabled(False)
    await update.message.reply_text("Бот остановлен. Теперь отвечает только владельцу.")

def set_user_model(user_id, model):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS user_models (user_id INTEGER PRIMARY KEY, model TEXT)')
    c.execute('INSERT OR REPLACE INTO user_models (user_id, model) VALUES (?, ?)', (user_id, model))
    conn.commit()
    conn.close()

def get_user_model(user_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS user_models (user_id INTEGER PRIMARY KEY, model TEXT)')
    c.execute('SELECT model FROM user_models WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    if row and row[0]:
        # Миграция со старой модели на новую
        if row[0] == 'meta-llama/llama-2-7b-chat':
            set_user_model(user_id, 'meta-llama/llama-3.1-8b-instruct:free')
            return 'meta-llama/llama-3.1-8b-instruct:free'
        return row[0]
    return None

async def models_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(f"{k}", callback_data=f"setmodel|{v['id']}")]
        for k, v in AVAILABLE_MODELS.items()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "<b>Доступные модели:</b>\n" + "\n\n".join([
        f"<b>{k}</b>: <i>{v['id']}</i>\n{v['desc']}" for k, v in AVAILABLE_MODELS.items()
    ])
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def setmodel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("setmodel|"):
        model = data.split("|", 1)[1]
        set_user_model(query.from_user.id, model)
        # Находим имя модели для красивого вывода
        model_name = next((k for k, v in AVAILABLE_MODELS.items() if v['id'] == model), model)
        await query.edit_message_text(f"Модель установлена: <b>{model_name}</b>", parse_mode='HTML')

async def setmodel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: /setmodel &lt;короткое_имя_или_id_модели&gt;", parse_mode='HTML')
        return
    model_key = context.args[0].lower()
    model = AVAILABLE_MODELS.get(model_key, {'id': model_key})['id']
    set_user_model(update.effective_user.id, model)
    model_name = next((k for k, v in AVAILABLE_MODELS.items() if v['id'] == model), model)
    await update.message.reply_text(f"Модель установлена: <b>{model_name}</b>", parse_mode='HTML')

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update):
        await update.message.reply_text("У вас нет прав для использования этой команды.")
        return

    conn = sqlite3.connect('bot.db')
    c = conn.cursor()

    # Получаем статистику
    c.execute('SELECT COUNT(DISTINCT user_id) FROM users')
    total_users = c.fetchone()[0]

    c.execute('SELECT COUNT(*) FROM chat_history WHERE role = "user"')
    total_requests = c.fetchone()[0]

    c.execute('SELECT COUNT(*) FROM chat_history WHERE role = "assistant"')
    total_responses = c.fetchone()[0]

    # Получаем топ-5 активных пользователей
    c.execute('''
        SELECT u.username, COUNT(*) as msg_count 
        FROM chat_history ch 
        JOIN users u ON ch.user_id = u.user_id 
        GROUP BY ch.user_id 
        ORDER BY msg_count DESC 
        LIMIT 5
    ''')
    top_users = c.fetchall()

    conn.close()

    stats_text = (
        "📊 <b>Статистика бота</b>\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"💬 Всего запросов: {total_requests}\n"
        f"✅ Всего ответов: {total_responses}\n\n"
        "🏆 <b>Топ-5 активных пользователей:</b>\n"
    )

    for i, (username, count) in enumerate(top_users, 1):
        stats_text += f"{i}. @{username}: {count} сообщений\n"

    await update.message.reply_text(stats_text, parse_mode='HTML')

# --- Чёрный список пользователей ---
def add_to_blacklist(user_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS blacklist (user_id INTEGER PRIMARY KEY)')
    c.execute('INSERT OR IGNORE INTO blacklist (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def is_blacklisted(user_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS blacklist (user_id INTEGER PRIMARY KEY)')
    c.execute('SELECT 1 FROM blacklist WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

async def block_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update):
        await update.message.reply_text("Эта команда только для владельца.")
        return
    # Если есть reply на сообщение — блокируем этого пользователя
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        add_to_blacklist(target_user.id)
        await update.message.reply_text(f"Пользователь {target_user.mention_html()} (ID: <code>{target_user.id}</code>) добавлен в чёрный список.", parse_mode='HTML')
        return
    # Если указан id через аргумент
    if context.args:
        try:
            target_id = int(context.args[0])
            add_to_blacklist(target_id)
            await update.message.reply_text(f"Пользователь с ID <code>{target_id}</code> добавлен в чёрный список.", parse_mode='HTML')
        except Exception:
            await update.message.reply_text("Некорректный формат ID. Используйте /block <id> или ответьте на сообщение пользователя.")
        return
    await update.message.reply_text("Используйте /block <id> или ответьте на сообщение пользователя.")

def remove_from_blacklist(user_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS blacklist (user_id INTEGER PRIMARY KEY)')
    c.execute('DELETE FROM blacklist WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

async def unblock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update):
        await update.message.reply_text("Эта команда только для владельца.")
        return
    # Если есть reply на сообщение — разблокируем этого пользователя
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        remove_from_blacklist(target_user.id)
        await update.message.reply_text(f"Пользователь {target_user.mention_html()} (ID: <code>{target_user.id}</code>) удалён из чёрного списка.", parse_mode='HTML')
        return
    # Если указан id через аргумент
    if context.args:
        try:
            target_id = int(context.args[0])
            remove_from_blacklist(target_id)
            await update.message.reply_text(f"Пользователь с ID <code>{target_id}</code> удалён из чёрного списка.", parse_mode='HTML')
        except Exception:
            await update.message.reply_text("Некорректный формат ID. Используйте /unblock <id> или ответьте на сообщение пользователя.")
        return
    await update.message.reply_text("Используйте /unblock <id> или ответьте на сообщение пользователя.")

async def migrate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update):
        await update.message.reply_text("Эта команда только для владельца.")
        return
    
    await update.message.reply_text("🔄 Запускаю миграцию моделей...")
    
    # Выполняем миграцию
    migrate_old_models()
    
    # Проверяем, есть ли пользователи с недействительными моделями
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    
    # Получаем все уникальные модели пользователей
    c.execute('SELECT DISTINCT model FROM user_models')
    user_models = [row[0] for row in c.fetchall()]
    
    # Проверяем, какие модели не входят в доступные
    invalid_models = []
    for model in user_models:
        if model not in [v['id'] for v in AVAILABLE_MODELS.values()]:
            invalid_models.append(model)
    
    conn.close()
    
    if invalid_models:
        await update.message.reply_text(
            f"⚠️ Обнаружены пользователи с недействительными моделями:\n"
            f"{', '.join(invalid_models)}\n\n"
            f"Используйте /setmodel для ручной установки моделей этим пользователям."
        )
    else:
        await update.message.reply_text("✅ Миграция завершена успешно! Все модели актуальны.")

async def safe_reply_text(message, *args, **kwargs):
    try:
        return await message.reply_text(*args, **kwargs)
    except RetryAfter as e:
        wait_time = int(e.retry_after)
        await asyncio.sleep(wait_time)
        return await message.reply_text(*args, **kwargs)

def main():
    try:
        # Инициализируем базу данных
        init_db()
        
        # Создаем приложение
        application = Application.builder().token(TELEGRAM_TOKEN).build()

        # Добавляем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("stats", stats))
        application.add_handler(CommandHandler("broadcast", broadcast))
        application.add_handler(CommandHandler("clear", clear_history))
        application.add_handler(CommandHandler("models", models_command))
        application.add_handler(CommandHandler("setmodel", setmodel_command))
        application.add_handler(CallbackQueryHandler(setmodel_callback, pattern=r"^setmodel\|"))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("ownerhelp", ownerhelp_command))
        application.add_handler(CommandHandler("go", go_command))
        application.add_handler(CommandHandler("stop", stop_command))
        application.add_handler(CommandHandler("migrate", migrate_command))
        application.add_handler(CommandHandler("block", block_command))
        application.add_handler(CommandHandler("unblock", unblock_command))

        # Запускаем бота
        logger.info("Бот запущен")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}")
        raise

if __name__ == '__main__':
    main() 