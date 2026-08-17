import os
import logging
from datetime import date

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# Токен теперь читается из переменной BOT_TOKEN
# В Railway -> Variables создай переменную BOT_TOKEN с токеном этого бота
# ---------------------------------------------------------
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

# Расписание дел по дням недели (0=понедельник ... 6=воскресенье)
SCHEDULE = {
    0: ["Отжимания"],
    1: ["Книжка", "Прогулка", "Уборка"],
    2: ["Приседания"],
    3: ["Книжка", "Прогулка", "Уборка"],
    4: ["Подтягивания"],
    5: ["Книжка", "Прогулка", "Уборка"],
    6: [],  # воскресенье - отдых
}

# Состояние выполнения дел: {user_id: {date_str: {task_index: bool}}}
user_state: dict[int, dict[str, dict[int, bool]]] = {}


def get_today_tasks() -> list[str]:
    weekday = date.today().weekday()
    return SCHEDULE[weekday]


def get_today_key() -> str:
    return date.today().isoformat()


def get_user_today_state(user_id: int) -> dict[int, bool]:
    today_key = get_today_key()
    user_state.setdefault(user_id, {})
    user_state[user_id].setdefault(today_key, {})
    tasks = get_today_tasks()
    for i in range(len(tasks)):
        user_state[user_id][today_key].setdefault(i, False)
    return user_state[user_id][today_key]


def build_today_markup(user_id: int) -> InlineKeyboardMarkup:
    tasks = get_today_tasks()
    state = get_user_today_state(user_id)
    buttons = []
    for i, task in enumerate(tasks):
        mark = "✅" if state[i] else "❌"
        buttons.append(
            [InlineKeyboardButton(f"{mark} {task}", callback_data=f"toggle:{i}")]
        )
    return InlineKeyboardMarkup(buttons)


def build_today_text(user_id: int) -> str:
    tasks = get_today_tasks()
    if not tasks:
        return "Сегодня выходной 🎉 Отдыхай!"
    state = get_user_today_state(user_id)
    done = sum(1 for v in state.values() if v)
    total = len(tasks)
    percent = round(done / total * 100) if total else 0
    return f"Дела на сегодня ({percent}% выполнено):"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я бот-трекер ежедневных дел.\n"
        "Команда /today покажет список дел на сегодня."
    )


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = build_today_text(user_id)
    markup = build_today_markup(user_id)
    await update.message.reply_text(text, reply_markup=markup)


async def toggle_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    _, index_str = query.data.split(":")
    index = int(index_str)

    state = get_user_today_state(user_id)
    state[index] = not state[index]

    text = build_today_text(user_id)
    markup = build_today_markup(user_id)
    await query.edit_message_text(text, reply_markup=markup)


def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("today", today))
    application.add_handler(CallbackQueryHandler(toggle_task, pattern=r"^toggle:"))

    logger.info("Bot started")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
