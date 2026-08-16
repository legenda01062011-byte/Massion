import os
import sqlite3
import datetime
import asyncio

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

# ---------------------------------------------------------------------------
# Уникальное имя переменной токена — TRACKER_BOT_TOKEN, чтобы не путаться
# с BOT_TOKEN другого бота
# ---------------------------------------------------------------------------
TOKEN = os.environ.get("TRACKER_BOT_TOKEN")
DB_PATH = os.environ.get("DB_PATH", "tracker.db")

router = Router()

TASKS = {
    0: [  # Понедельник
        "Отжимания — 4×10–15",
        "Отжимания узким хватом — 3×8–12",
        "Отжимания с ногами на возвышенности — 3×8–12",
        "Отжимания от стула — 3×10–15",
        "Планка — 3×60 сек",
    ],
    1: [  # Вторник
        "Прочитать книжку (1 закон)",
        "Погулять ранним утром",
        "Погулять вечером",
        "Прибрать дома",
    ],
    2: [  # Среда
        "Приседания — 4×15–20",
        "Выпады — 3×12 на каждую ногу",
        "Болгарские приседания — 3×10 на каждую ногу",
        "Подъёмы на носки — 4×20",
        "Скручивания — 3×20",
        "Подъём ног лёжа — 3×15",
    ],
    3: [  # Четверг
        "Прочитать книжку (1 закон)",
        "Погулять ранним утром",
        "Погулять вечером",
        "Прибрать дома",
    ],
    4: [  # Пятница
        "Подтягивания — 4×максимум (или тяга рюкзака 4×12–15)",
        "Тяга рюкзака к поясу — 4×12–15",
        "Сгибания рук с рюкзаком — 3×12–15",
        "Отжимания — 3×максимум",
        "Боковая планка — 3×45 сек на каждую сторону",
    ],
    5: [  # Суббота
        "Прочитать книжку (1 закон)",
        "Погулять ранним утром",
        "Погулять вечером",
        "Прибрать дома",
    ],
    6: [  # Воскресенье
        "Отдохнуть",
    ],
}

WEEKDAY_NAMES = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]


def db_connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS completions (
            user_id INTEGER,
            date TEXT,
            task_idx INTEGER,
            done INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, date, task_idx)
        )"""
    )
    conn.commit()
    return conn


conn = db_connect()


def get_today_key():
    return datetime.date.today().isoformat()


def get_completions(user_id: int, date: str) -> dict[int, bool]:
    cur = conn.execute(
        "SELECT task_idx, done FROM completions WHERE user_id=? AND date=?",
        (user_id, date),
    )
    return {idx: bool(done) for idx, done in cur.fetchall()}


def toggle_task(user_id: int, date: str, task_idx: int):
    current = get_completions(user_id, date).get(task_idx, False)
    new_val = 0 if current else 1
    conn.execute(
        """INSERT INTO completions (user_id, date, task_idx, done) VALUES (?,?,?,?)
           ON CONFLICT(user_id, date, task_idx) DO UPDATE SET done=excluded.done""",
        (user_id, date, task_idx, new_val),
    )
    conn.commit()


def build_day_view(user_id: int, date_str: str):
    date_obj = datetime.date.fromisoformat(date_str)
    weekday = date_obj.weekday()
    tasks = TASKS[weekday]
    done_map = get_completions(user_id, date_str)

    done_count = sum(1 for i in range(len(tasks)) if done_map.get(i, False))
    total = len(tasks)
    percent = round(done_count / total * 100) if total else 0

    text = f"📅 {WEEKDAY_NAMES[weekday]} ({date_str})\nПрогресс: {percent}% ({done_count}/{total})"

    kb = []
    for i, task in enumerate(tasks):
        mark = "✅" if done_map.get(i, False) else "❌"
        kb.append([InlineKeyboardButton(text=f"{mark} {task}", callback_data=f"toggle:{date_str}:{i}")])

    return text, InlineKeyboardMarkup(inline_keyboard=kb)


@router.message(Command("start", "help"))
async def cmd_start(message: Message):
    await message.reply(
        "👋 Привет! Я трекер дел.\n\n"
        "/today — показать список дел на сегодня с кнопками\n"
        "Жми на дело, чтобы отметить выполненным ✅ или снять отметку ❌\n"
        "Процент выполнения дня считается автоматически."
    )


@router.message(Command("today"))
async def cmd_today(message: Message):
    date_str = get_today_key()
    text, kb = build_day_view(message.from_user.id, date_str)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("toggle:"))
async def toggle_callback(callback: CallbackQuery):
    _, date_str, idx_str = callback.data.split(":")
    idx = int(idx_str)

    toggle_task(callback.from_user.id, date_str, idx)
    text, kb = build_day_view(callback.from_user.id, date_str)

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


async def main():
    if not TOKEN:
        raise RuntimeError("TRACKER_BOT_TOKEN is not set. Put your Telegram bot token in the TRACKER_BOT_TOKEN environment variable / Secret.")
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())