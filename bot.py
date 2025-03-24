import asyncio
import logging
import json
import os
import aiofiles
import sqlite3
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.types import (
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    FSInputFile
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ==== 🔹 Настройки бота ====
load_dotenv()

API_TOKEN = os.getenv("BOT_API_TOKEN")
if not API_TOKEN:
    raise ValueError("Не найден токен бота. Проверьте файл .env")

CHANNEL_USERNAME_OR_ID = "-1002490792993"
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

GPT_BOT_USERNAME = "roxsonai_bot"
PROMO_CODE = "SECRET15"
PROMO_DELAY = 10
MY_USERNAME = "dmitrenko_ai"

LOGS_FILE = "logs.json"
USERS_FILE = "users.json"
STATS_FILE = "stats.json"
DB_FILE = "users.db"

# ==== Логирование ====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

# ==== Создаём бот и диспетчер ====
try:
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher()
except Exception as e:
    logging.error(f"Ошибка при инициализации бота: {e}")
    raise

# ==== FSM: состояние для рассылки ====
class BroadcastStates(StatesGroup):
    waiting_broadcast_text = State()
    confirm_broadcast = State()

# ==== Функции для работы с базой данных ====
def init_db():
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (user_id INTEGER PRIMARY KEY,
                      username TEXT,
                      first_name TEXT,
                      last_name TEXT,
                      joined_date TEXT,
                      last_activity TEXT)''')
        conn.commit()
        conn.close()
        logging.info("База данных успешно инициализирована")
    except Exception as e:
        logging.error(f"Ошибка при инициализации базы данных: {e}")
        raise

async def add_user(user_id: int, username: str, first_name: str, last_name: str):
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute('''INSERT OR REPLACE INTO users 
                     (user_id, username, first_name, last_name, joined_date, last_activity)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (user_id, username, first_name, last_name, now, now))
        conn.commit()
        logging.info(f"Пользователь {user_id} добавлен в базу данных")
    except Exception as e:
        logging.error(f"Ошибка при добавлении пользователя {user_id}: {e}")
        raise
    finally:
        if conn:
            conn.close()

async def update_user_activity(user_id: int):
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute('UPDATE users SET last_activity = ? WHERE user_id = ?', (now, user_id))
        conn.commit()
    except Exception as e:
        logging.error(f"Ошибка при обновлении активности пользователя {user_id}: {e}")
        raise
    finally:
        if conn:
            conn.close()

async def get_users_list():
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('SELECT * FROM users ORDER BY joined_date DESC')
        users = c.fetchall()
        return users
    except Exception as e:
        logging.error(f"Ошибка при получении списка пользователей: {e}")
        return []
    finally:
        if conn:
            conn.close()

# ==== Функции для логов ====
async def load_logs():
    if not os.path.exists(LOGS_FILE):
        return {}
    try:
        async with aiofiles.open(LOGS_FILE, "r", encoding="utf-8") as f:
            content = await f.read()
            return json.loads(content)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        logging.error("Ошибка декодирования JSON в логах")
        return {}

async def save_log(user_id, action):
    try:
        logs = await load_logs()
        if str(user_id) not in logs:
            logs[str(user_id)] = []
        logs[str(user_id)].append({
            "action": action,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        async with aiofiles.open(LOGS_FILE, "w", encoding="utf-8") as f:
            await f.write(json.dumps(logs, ensure_ascii=False, indent=2))
    except Exception as e:
        logging.error(f"Ошибка при сохранении лога для пользователя {user_id}: {e}")

# ==== Функции для хранения списка user_id ====
async def load_users() -> set:
    if not os.path.exists(USERS_FILE):
        return set()
    try:
        async with aiofiles.open(USERS_FILE, "r", encoding="utf-8") as f:
            content = await f.read()
            data = json.loads(content)
            return set(data)
    except Exception as e:
        logging.error(f"Ошибка при загрузке пользователей: {e}")
        return set()

async def save_users(users: set):
    try:
        async with aiofiles.open(USERS_FILE, "w", encoding="utf-8") as f:
            await f.write(json.dumps(list(users), ensure_ascii=False, indent=2))
    except Exception as e:
        logging.error(f"Ошибка при сохранении списка пользователей: {e}")

# ==== Функции для работы со статистикой ====
async def update_button_stats(button_name: str):
    try:
        stats = {}
        if os.path.exists(STATS_FILE):
            async with aiofiles.open(STATS_FILE, "r", encoding="utf-8") as f:
                content = await f.read()
                if content:
                    stats = json.loads(content)
        
        if button_name not in stats:
            stats[button_name] = 0
        stats[button_name] += 1
        
        async with aiofiles.open(STATS_FILE, "w", encoding="utf-8") as f:
            await f.write(json.dumps(stats, ensure_ascii=False, indent=2))
            
        logging.info(f"Обновлена статистика для кнопки {button_name}: {stats[button_name]} нажатий")
    except Exception as e:
        logging.error(f"Ошибка при обновлении статистики кнопки {button_name}: {e}")

# ==== Обработчик неизвестных команд ====
@dp.message(lambda message: not message.text.startswith('/'))
async def handle_unknown(message: Message):
    try:
        await update_user_activity(message.from_user.id)
        
        unknown_text = (
            "❌ Я не знаю такой команды.\n\n"
            "💬 Хотите пообщаться с AI? Нажмите кнопку ниже!"
        )
        
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🤖 Бесплатный ChatGPT",
                        url=f"https://t.me/{GPT_BOT_USERNAME}"
                    )
                ]
            ]
        )
        
        await message.answer(unknown_text, reply_markup=kb)
    except Exception as e:
        logging.error(f"Ошибка в обработчике неизвестных команд: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")

# ==== /start ====
@dp.message(Command("start"))
async def cmd_start(message: Message):
    try:
        user_id = message.from_user.id
        users = await load_users()

        # Добавляем пользователя в базу данных
        await add_user(
            user_id=message.from_user.id,
            username=message.from_user.username or "",
            first_name=message.from_user.first_name or "",
            last_name=message.from_user.last_name or ""
        )

        # Добавляем пользователя, если его нет
        if user_id not in users:
            users.add(user_id)
            await save_users(users)
            await save_log(user_id, "Нажал /start")

        # Создаем кнопки
        buttons = [
            ("🔥 Вступить в закрытый ТГ-канал", "https://t.me/+vNg5vVVonNExOWRi", "btn_channel"),
            ("🤖 Получить бесплатный GPT", f"https://t.me/{GPT_BOT_USERNAME}", "btn_gpt"),
            ("🚀 Бесплатная страт сессия", f"https://t.me/{MY_USERNAME}", "btn_strat"),
            ("📜 Авторские промты для GPT", "https://puddle-speedwell-70f.notion.site/pack-v0-1-1a413b51050180fe8045c303ca4d4869?pvs=4", "btn_prompts")
        ]

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=text, url=url, callback_data=callback)]
            for text, url, callback in buttons
        ])

        # Полный текст приветствия
        welcome_text = (
            "<b>Привет!</b> Я <b>Сева Дмитренко</b>, и если ты здесь – значит, "
            "тебе интересно, <i>как использовать нейросети в свою пользу</i>.\n\n"
            "Я не буду грузить тебя скучными лекциями – лучше сразу покажу, "
            "что ты можешь сделать с AI уже сегодня.\n\n"
            "<b>Ты узнаешь:</b>\n"
            "• Как ускорять работу с текстом и контентом в разы\n"
            "• Как использовать AI для заработка и автоматизации\n"
            "• Какие инструменты реально работают, а какие – просто хайп\n\n"
            "❌ Если тебе кажется, что AI – это сложно, забудь про этот миф. "
            "Я научу тебя использовать <b>умные технологии</b> без лишней теории.\n\n"
            "🚀 <b>Выбирай нужный раздел ниже!</b>"
        )

        await message.answer_photo(
            photo="https://i.postimg.cc/KYThRhy6/image.png",
            caption=welcome_text,
            parse_mode="HTML",
            reply_markup=kb
        )

        # Запускаем отправку промокода через PROMO_DELAY
        asyncio.create_task(send_promo_after_delay(user_id))
    except Exception as e:
        logging.error(f"Ошибка в команде /start: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")

async def send_promo_after_delay(chat_id: int):
    await asyncio.sleep(PROMO_DELAY)
    try:
        promo_text = (
            f"🎉 Поздравляю! Ты можешь получить скидку <b>15%</b> на тарифы GPT!\n\n"
            f"🔑 <b>Твой промокод:</b> <code>{PROMO_CODE}</code>\n"
            f"💡 Используй этот код при покупке, чтобы получить скидку."
        )

        await bot.send_message(chat_id, promo_text, parse_mode="HTML")
        await save_log(chat_id, "Получил промокод")
    except Exception as e:
        logging.error(f"Ошибка при отправке промокода: {e}")

# ==== /logs ====
@dp.message(Command("logs"))
async def send_logs(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа к логам.")
        return

    if not os.path.exists(LOGS_FILE):
        await message.answer("❌ Логов пока нет.")
        return

    try:
        file_input = FSInputFile(LOGS_FILE)
        await message.answer_document(
            document=file_input,
            caption="Логи пользователей."
        )
    except Exception as e:
        logging.error(f"Ошибка при отправке логов: {e}")
        await message.answer("❌ Произошла ошибка при отправке логов.")

# ==== /help ====
@dp.message(Command("help"))
async def cmd_help(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа к этой команде.")
        return

    help_text = (
        "<b>Доступные команды администратора:</b>\n\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать это сообщение\n"
        "/admin - Админ-панель\n"
        "/logs - Получить логи\n\n"
        "<b>Функции админ-панели:</b>\n"
        "• Просмотр количества пользователей\n"
        "• Просмотр статистики кнопок\n"
        "• Отправка рассылки\n\n"
        "<b>Если возникли проблемы:</b>\n"
        "• Проверьте подключение к интернету\n"
        "• Проверьте логи в файле bot.log\n"
        "• Перезапустите бота при необходимости"
    )
    await message.answer(help_text, parse_mode="HTML")

# ==== /admin (админ-панель) ====
@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет прав для доступа к админ-панели!")
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 Отчёт по пользователям",
                    callback_data="admin_excel_stats"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📢 Рассылка",
                    callback_data="admin_broadcast"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Закрыть",
                    callback_data="admin_close"
                )
            ]
        ]
    )
    await message.answer("⚙️ <b>Админ-панель</b>", parse_mode="HTML", reply_markup=kb)

@dp.callback_query(lambda c: c.data in ["admin_excel_stats", "admin_broadcast", "admin_close", "admin_return", "broadcast_confirm"])
async def admin_panel_actions(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Нет доступа!", show_alert=True)
        return

    try:
        if call.data == "admin_close":
            await state.clear()
            await call.message.edit_text("❌ Панель закрыта.")
            return

        elif call.data == "admin_excel_stats":
            await call.answer("📊 Создаю отчет...")
            if await create_excel_report():
                file = FSInputFile("bot_statistics.xlsx")
                await call.message.answer_document(
                    document=file,
                    caption="📊 Отчёт по пользователям бота"
                )
                os.remove("bot_statistics.xlsx")
                await return_to_admin_panel(call.message)
            else:
                await call.message.edit_text("❌ Ошибка при создании отчета.")
                await asyncio.sleep(2)
                await return_to_admin_panel(call.message)
            return

        elif call.data == "admin_broadcast":
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="❌ Отменить",
                            callback_data="admin_return"
                        )
                    ]
                ]
            )
            await call.message.edit_text(
                "📢 Введите текст для рассылки:\n\n"
                "⚠️ <i>Сообщение не должно превышать 4096 символов</i>\n\n"
                "Для отмены нажмите кнопку ниже ⬇️",
                parse_mode="HTML",
                reply_markup=kb
            )
            await state.set_state(BroadcastStates.waiting_broadcast_text)
            return

        elif call.data == "admin_return":
            await state.clear()
            await return_to_admin_panel(call.message)
            return

        elif call.data == "broadcast_confirm":
            data = await state.get_data()
            text_to_send = data.get("broadcast_text")
            
            if not text_to_send:
                await call.message.edit_text("❌ Ошибка: текст рассылки не найден.")
                await state.clear()
                await asyncio.sleep(2)
                await return_to_admin_panel(call.message)
                return

            users = await get_users_list()
            if not users:
                await call.message.edit_text("❌ Нет пользователей для рассылки.")
                await state.clear()
                await asyncio.sleep(2)
                await return_to_admin_panel(call.message)
                return

            sent_count = 0
            failed_count = 0
            blocked_count = 0

            status_message = await call.message.edit_text("📢 Начинаю рассылку...")

            for user in users:
                user_id = user[0]
                if await safe_send_message(user_id, text_to_send, parse_mode="HTML"):
                    sent_count += 1
                else:
                    failed_count += 1
                
                if sent_count % 10 == 0:
                    await status_message.edit_text(
                        f"📢 Рассылка в процессе...\n"
                        f"✅ Отправлено: {sent_count}\n"
                        f"❌ Ошибок: {failed_count}\n"
                        f"🚫 Заблокировали: {blocked_count}"
                    )

            await status_message.edit_text(
                f"📢 Рассылка завершена.\n"
                f"✅ Успешно отправлено: {sent_count}\n"
                f"❌ Ошибок: {failed_count}\n"
                f"🚫 Заблокировали: {blocked_count}"
            )
            await state.clear()
            await asyncio.sleep(3)
            await return_to_admin_panel(call.message)

    except Exception as e:
        logging.error(f"Ошибка в админ-панели: {e}")
        await call.message.edit_text("❌ Произошла ошибка при выполнении операции.")
        await state.clear()
        await asyncio.sleep(2)
        await return_to_admin_panel(call.message)

async def return_to_admin_panel(message: Message):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 Отчёт по пользователям",
                    callback_data="admin_excel_stats"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📢 Рассылка",
                    callback_data="admin_broadcast"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Закрыть",
                    callback_data="admin_close"
                )
            ]
        ]
    )
    await message.edit_text("⚙️ <b>Админ-панель</b>", parse_mode="HTML", reply_markup=kb)

async def create_excel_report():
    try:
        users = await get_users_list()
        if not users:
            logging.warning("Нет данных для создания отчета")
            return False

        users_data = []
        for user in users:
            user_id, username, first_name, last_name, joined_date, last_activity = user
            users_data.append({
                'ID': user_id,
                'Username': f"@{username}" if username else 'нет',
                'Имя': first_name or 'нет',
                'Фамилия': last_name or 'нет',
                'Дата регистрации': joined_date,
                'Последняя активность': last_activity
            })

        df_users = pd.DataFrame(users_data)

        # Удаляем старый файл, если он существует
        if os.path.exists('bot_statistics.xlsx'):
            os.remove('bot_statistics.xlsx')

        writer = pd.ExcelWriter('bot_statistics.xlsx', engine='xlsxwriter')
        df_users.to_excel(writer, sheet_name='Пользователи', index=False)
        
        workbook = writer.book
        worksheet = writer.sheets['Пользователи']
        
        # Форматирование заголовков
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })
        
        # Форматирование ячеек
        cell_format = workbook.add_format({
            'text_wrap': True,
            'valign': 'top',
            'border': 1
        })
        
        # Применяем форматирование
        for col_num, value in enumerate(df_users.columns.values):
            worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(col_num, col_num, 15, cell_format)
            
            # Устанавливаем ширину колонок
            max_length = max(
                df_users[value].astype(str).apply(len).max(),
                len(str(value))
            )
            worksheet.set_column(col_num, col_num, max_length + 2)
        
        writer.close()
        
        if not os.path.exists('bot_statistics.xlsx'):
            logging.error("Файл отчета не был создан")
            return False
            
        return True
    except Exception as e:
        logging.error(f"Ошибка при создании Excel отчета: {e}")
        return False

# ==== Обработчик для всех inline кнопок ====
@dp.callback_query()
async def process_callback(call: CallbackQuery):
    try:
        # Пропускаем системные callback_data
        if call.data.startswith(('admin_', 'broadcast_')):
            return
            
        # Логируем нажатие кнопки
        await update_button_stats(call.data)
        logging.info(f"Пользователь {call.from_user.id} нажал кнопку {call.data}")
        
        # Отвечаем пользователю, чтобы убрать часы загрузки
        await call.answer()
        
    except Exception as e:
        logging.error(f"Ошибка при обработке нажатия кнопки: {e}")
        await call.answer("Произошла ошибка", show_alert=True)

# Обработчик рассылки
@dp.message(BroadcastStates.waiting_broadcast_text)
async def process_broadcast_text(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет прав!")
        return

    if not message.text:
        await message.answer("❌ Текст сообщения не может быть пустым.")
        return

    if len(message.text) > 4096:
        await message.answer("❌ Текст сообщения не может превышать 4096 символов.")
        return

    await state.update_data(broadcast_text=message.text)
    
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить",
                    callback_data="broadcast_confirm"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data="admin_return"
                )
            ]
        ]
    )
    
    preview_text = message.text if len(message.text) <= 400 else message.text[:397] + "..."
    
    await message.answer(
        f"📢 <b>Предпросмотр сообщения</b>\n\n"
        f"{preview_text}\n\n"
        f"⚠️ Сообщение будет отправлено <b>всем</b> пользователям бота.",
        parse_mode="HTML",
        reply_markup=kb
    )
    await state.set_state(BroadcastStates.confirm_broadcast)

@dp.callback_query(lambda c: c.data in ["broadcast_confirm", "admin_return"])
async def process_broadcast_confirmation(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Нет доступа!", show_alert=True)
        return

    try:
        if call.data == "admin_return":
            await state.clear()
            await return_to_admin_panel(call.message)
            return

        elif call.data == "broadcast_confirm":
            data = await state.get_data()
            text_to_send = data.get("broadcast_text")
            
            if not text_to_send:
                await call.message.edit_text("❌ Ошибка: текст рассылки не найден.")
                await state.clear()
                await asyncio.sleep(2)
                await return_to_admin_panel(call.message)
                return

            users = await get_users_list()
            if not users:
                await call.message.edit_text("❌ Нет пользователей для рассылки.")
                await state.clear()
                await asyncio.sleep(2)
                await return_to_admin_panel(call.message)
                return

            sent_count = 0
            failed_count = 0
            blocked_count = 0

            status_message = await call.message.edit_text("📢 Начинаю рассылку...")

            for user in users:
                user_id = user[0]
                if await safe_send_message(user_id, text_to_send, parse_mode="HTML"):
                    sent_count += 1
                else:
                    failed_count += 1
                
                if sent_count % 10 == 0:
                    await status_message.edit_text(
                        f"📢 Рассылка в процессе...\n"
                        f"✅ Отправлено: {sent_count}\n"
                        f"❌ Ошибок: {failed_count}\n"
                        f"🚫 Заблокировали: {blocked_count}"
                    )

            await status_message.edit_text(
                f"📢 Рассылка завершена.\n"
                f"✅ Успешно отправлено: {sent_count}\n"
                f"❌ Ошибок: {failed_count}\n"
                f"🚫 Заблокировали: {blocked_count}"
            )
            await state.clear()
            await asyncio.sleep(3)
            await return_to_admin_panel(call.message)

    except Exception as e:
        logging.error(f"Ошибка при обработке рассылки: {e}")
        await call.message.edit_text("❌ Произошла ошибка при выполнении рассылки.")
        await state.clear()
        await asyncio.sleep(3)
        await return_to_admin_panel(call.message)

async def safe_send_message(chat_id: int, text: str, parse_mode: str = None) -> bool:
    try:
        await bot.send_message(chat_id, text, parse_mode=parse_mode)
        return True
    except Exception as e:
        error_msg = str(e).lower()
        if "bot was blocked by the user" in error_msg:
            logging.warning(f"Пользователь {chat_id} заблокировал бота")
        elif "chat not found" in error_msg:
            logging.warning(f"Чат {chat_id} не найден")
        else:
            logging.error(f"Ошибка при отправке сообщения пользователю {chat_id}: {e}")
        return False

async def main():
    try:
        # Создаем директорию для файлов, если она не существует
        os.makedirs("data", exist_ok=True)
        
        # Инициализируем базу данных
        init_db()
        
        # Проверяем наличие необходимых файлов
        for file in [LOGS_FILE, USERS_FILE, STATS_FILE]:
            if not os.path.exists(file):
                logging.info(f"Создаю файл {file}")
                if file == LOGS_FILE:
                    async with aiofiles.open(file, "w", encoding="utf-8") as f:
                        await f.write("{}")
                elif file == USERS_FILE:
                    async with aiofiles.open(file, "w", encoding="utf-8") as f:
                        await f.write("[]")
                elif file == STATS_FILE:
                    async with aiofiles.open(file, "w", encoding="utf-8") as f:
                        await f.write("{}")

        # Проверяем подключение к Telegram
        try:
            bot_info = await bot.get_me()
            logging.info(f"Бот {bot_info.username} успешно подключен")
        except Exception as e:
            logging.error(f"Ошибка при подключении к Telegram: {e}")
            raise

        # Запускаем бота
        logging.info("Запуск бота...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")
        raise
    finally:
        # Закрываем сессию бота
        await bot.session.close()
        logging.info("Бот остановлен")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен пользователем")
    except Exception as e:
        logging.error(f"Необработанная ошибка: {e}")
