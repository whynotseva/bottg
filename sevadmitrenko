import asyncio
import logging
import json
import os

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
API_TOKEN = "7959075437:AAGFKPPV3G_tCGGoggkGLA8D5C9AFgn1yvE"
CHANNEL_USERNAME_OR_ID = "-1002490792993"
ADMIN_ID = 44054166

GPT_BOT_USERNAME = "roxsonai_bot"
PROMO_CODE = "SECRET15"
PROMO_DELAY = 10
MY_USERNAME = "dmitrenko_ai"

LOGS_FILE = "logs.json"
USERS_FILE = "users.json"
STATS_FILE = "stats.json"  # для примера, если захотите в будущем вести статистику

# ==== Логирование ====
logging.basicConfig(level=logging.INFO)

# ==== Создаём бот и диспетчер ====
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ==== FSM: состояние для рассылки ====
class BroadcastStates(StatesGroup):
    waiting_broadcast_text = State()

# ==== Функции для логов ====
def load_logs():
    if not os.path.exists(LOGS_FILE):
        return {}
    try:
        with open(LOGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_log(user_id, action):
    logs = load_logs()
    if str(user_id) not in logs:
        logs[str(user_id)] = []
    logs[str(user_id)].append(action)

    with open(LOGS_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

# ==== Функции для хранения списка user_id ====
def load_users() -> set:
    if not os.path.exists(USERS_FILE):
        return set()
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data)
    except Exception:
        return set()

def save_users(users: set):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(users), f, ensure_ascii=False, indent=2)

# ==== /start ====
@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    users = load_users()

    # Добавляем пользователя, если его нет
    if user_id not in users:
        users.add(user_id)
        save_users(users)
        save_log(user_id, "Нажал /start")

    # Полный текст приветствия (возвращён из старых версий)
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

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔥 Вступить в закрытый ТГ-канал",
                    url="https://t.me/+vNg5vVVonNExOWRi"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🤖 Получить доступ к GPT",
                    url=f"https://t.me/{GPT_BOT_USERNAME}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚀 Бесплатная страт сессия",
                    url=f"https://t.me/{MY_USERNAME}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📜 Авторские промты для GPT",
                    url="https://puddle-speedwell-70f.notion.site/pack-v0-1-1a413b51050180fe8045c303ca4d4869?pvs=4"
                )
            ]
        ]
    )

    await message.answer_photo(
        photo="https://i.postimg.cc/KYThRhy6/image.png",
        caption=welcome_text,
        parse_mode="HTML",
        reply_markup=kb
    )

    # Запускаем отправку промокода через PROMO_DELAY
    asyncio.create_task(send_promo_after_delay(user_id))

async def send_promo_after_delay(chat_id: int):
    await asyncio.sleep(PROMO_DELAY)
    try:
        # Полный текст промо (возвращён)
        promo_text = (
            f"🎉 Поздравляю! Ты можешь получить скидку <b>15%</b> на тарифы GPT!\n\n"
            f"🔑 <b>Твой промокод:</b> <code>{PROMO_CODE}</code>\n"
            f"💡 Используй этот код при покупке, чтобы получить скидку."
        )

        await bot.send_message(chat_id, promo_text, parse_mode="HTML")
        save_log(chat_id, "Получил промокод")
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

    file_input = FSInputFile(LOGS_FILE)
    await message.answer_document(
        document=file_input,
        caption="Логи пользователей."
    )

# ==== /admin (админ-панель) ====
@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет прав!")
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👥 Кол-во пользователей",
                    callback_data="admin_users_count"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Статистика кнопок",
                    callback_data="admin_stats"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📢 Рассылка",
                    callback_data="admin_broadcast"
                )
            ]
        ]
    )
    await message.answer("⚙️ <b>Админ-панель</b>", parse_mode="HTML", reply_markup=kb)

@dp.callback_query(lambda c: c.data in ["admin_users_count", "admin_stats", "admin_broadcast"])
async def admin_panel_actions(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        await call.answer("Нет доступа!", show_alert=True)
        return

    if call.data == "admin_users_count":
        users_count = len(load_users())
        await call.message.answer(
            f"👥 В боте сейчас <b>{users_count}</b> пользователей.",
            parse_mode="HTML"
        )

    elif call.data == "admin_stats":
        if not os.path.exists(STATS_FILE):
            await call.message.answer("📊 Пока статистики нет.")
            return

        with open(STATS_FILE, "r", encoding="utf-8") as f:
            stats = json.load(f)

        stats_text = "\n".join([f"🔹 {k}: {v}" for k, v in stats.items()])
        await call.message.answer(
            f"<b>ТОП кнопок:</b>\n{stats_text}",
            parse_mode="HTML"
        )

    elif call.data == "admin_broadcast":
        await call.message.answer("Введите текст для рассылки:")
        await state.set_state(BroadcastStates.waiting_broadcast_text)

@dp.message(BroadcastStates.waiting_broadcast_text)
async def process_broadcast_text(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет прав!")
        return

    text_to_send = message.text
    all_users = load_users()
    sent_count = 0

    for uid in all_users:
        try:
            await bot.send_message(uid, text_to_send)
            sent_count += 1
        except Exception as e:
            logging.error(f"Ошибка при отправке user {uid}: {e}")

    await message.answer(f"📢 Рассылка завершена. Отправлено: {sent_count} из {len(all_users)}.")
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
