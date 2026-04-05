"""
Arkadium 2026 — Telegram Bot
Admin commands: /broadcast, /stats, /addcoins, /users
"""

import asyncio
import logging
import os
import httpx
from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

BOT_TOKEN    = os.getenv("BOT_TOKEN", "")
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://arkadium.example.com")
API_BASE     = os.getenv("API_BASE", "http://backend:8000/api")
PANEL_USER   = os.getenv("PANEL_USERNAME", "admin")
PANEL_PASS   = os.getenv("PANEL_PASSWORD", "arkadium2026")
ADMIN_IDS_RAW = os.getenv("ADMIN_TELEGRAM_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_RAW.split(",") if x.strip()]

_db_admin_cache: set[int] = set()
_cache_ts: float = 0


async def get_db_admins() -> set[int]:
    """Fetch DB admins with 60s cache."""
    import time
    global _db_admin_cache, _cache_ts
    if time.time() - _cache_ts < 60:
        return _db_admin_cache
    try:
        token = await get_panel_token()
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{API_BASE}/panel/admins",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            r.raise_for_status()
            ids = {a["telegram_id"] for a in r.json()}
            _db_admin_cache = ids
            _cache_ts = time.time()
            return ids
    except Exception:
        return _db_admin_cache

router = Router()

# ── Helpers ──────────────────────────────────────────────────────────────────

async def get_panel_token() -> str:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{API_BASE}/panel/login",
            json={"username": PANEL_USER, "password": PANEL_PASS},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()["access_token"]


async def api_get(path: str) -> dict:
    token = await get_panel_token()
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{API_BASE}{path}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()


async def api_patch(path: str, payload: dict) -> dict:
    token = await get_panel_token()
    async with httpx.AsyncClient() as client:
        r = await client.patch(
            f"{API_BASE}{path}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()


async def is_admin(user_id: int) -> bool:
    if user_id in ADMIN_IDS:
        return True
    db_admins = await get_db_admins()
    return user_id in db_admins


def mini_app_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🎮 Открыть Аркадиум",
            web_app=WebAppInfo(url=MINI_APP_URL),
        )
    ]])


def admin_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="👥 Пользователи")],
            [KeyboardButton(text="📢 Рассылка"),   KeyboardButton(text="💰 Начислить монеты")],
            [KeyboardButton(text="🎮 Открыть мини-апп")],
        ],
        resize_keyboard=True,
    )


# ── FSM States ───────────────────────────────────────────────────────────────

class BroadcastState(StatesGroup):
    waiting_text    = State()
    waiting_confirm = State()


class AddCoinsState(StatesGroup):
    waiting_user_id = State()
    waiting_amount  = State()
    waiting_confirm = State()


# ── /start ───────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(msg: Message):
    name = msg.from_user.first_name or "Герой"
    welcome = (
        f"Привет, {name}! 👋\n\n"
        "Добро пожаловать в <b>Аркадиум 2026</b> — квест на мероприятии.\n\n"
        "Выбирай персонажа, выполняй задания, зарабатывай аркоины и попадай в топ!"
    )
    if await is_admin(msg.from_user.id):
        await msg.answer(welcome, parse_mode=ParseMode.HTML, reply_markup=admin_menu_kb())
    else:
        await msg.answer(welcome, parse_mode=ParseMode.HTML, reply_markup=mini_app_kb())


# ── Admin: /admin ─────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(msg: Message):
    if not await is_admin(msg.from_user.id):
        return await msg.answer("⛔ Нет доступа.")
    await msg.answer("🛠 Панель администратора", reply_markup=admin_menu_kb())


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.message(F.text == "📊 Статистика")
@router.message(Command("stats"))
async def cmd_stats(msg: Message):
    if not await is_admin(msg.from_user.id):
        return
    try:
        data = await api_get("/panel/stats")
        text = (
            "📊 <b>Статистика Аркадиум</b>\n\n"
            f"👤 Всего пользователей: <b>{data['total_users']}</b>\n"
            f"✅ Зарегистрировано: <b>{data['registered_users']}</b>\n"
            f"🛍 Товаров в магазине: <b>{data['total_products']}</b>\n"
            f"📢 Объявлений: <b>{data['total_announcements']}</b>\n"
            f"🏅 Достижений: <b>{data['total_achievements']}</b>"
        )
        await msg.answer(text, parse_mode=ParseMode.HTML)
    except Exception as e:
        await msg.answer(f"❌ Ошибка: {e}")


# ── Users ─────────────────────────────────────────────────────────────────────

@router.message(F.text == "👥 Пользователи")
@router.message(Command("users"))
async def cmd_users(msg: Message):
    if not await is_admin(msg.from_user.id):
        return
    try:
        data = await api_get("/panel/users?limit=10")
        users = data.get("items", data) if isinstance(data, dict) else data
        lines = []
        for u in users[:10]:
            tg = f"@{u['username']}" if u.get("username") else f"id{u['telegram_id']}"
            lines.append(f"• {u['first_name']} {tg} — <b>{u['balance']} 🪙</b>")
        text = "👥 <b>Последние пользователи:</b>\n\n" + "\n".join(lines)
        await msg.answer(text, parse_mode=ParseMode.HTML)
    except Exception as e:
        await msg.answer(f"❌ Ошибка: {e}")


# ── Broadcast ─────────────────────────────────────────────────────────────────

@router.message(F.text == "📢 Рассылка")
@router.message(Command("broadcast"))
async def cmd_broadcast_start(msg: Message, state: FSMContext):
    if not await is_admin(msg.from_user.id):
        return
    await state.set_state(BroadcastState.waiting_text)
    await msg.answer(
        "✍️ Напиши текст рассылки (поддерживает <b>HTML</b>).\n\n"
        "Или /cancel для отмены.",
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(BroadcastState.waiting_text)
async def broadcast_got_text(msg: Message, state: FSMContext):
    await state.update_data(text=msg.html_text)
    await state.set_state(BroadcastState.waiting_confirm)
    await msg.answer(
        f"📋 Сообщение для рассылки:\n\n{msg.html_text}\n\n"
        "Отправить всем пользователям? (да / нет)",
        parse_mode=ParseMode.HTML,
    )


@router.message(BroadcastState.waiting_confirm)
async def broadcast_confirm(msg: Message, state: FSMContext, bot: Bot):
    if msg.text.lower() not in ("да", "yes", "y", "д"):
        await state.clear()
        await msg.answer("❌ Рассылка отменена.", reply_markup=admin_menu_kb())
        return

    data = await state.get_data()
    text = data["text"]
    await state.clear()

    status_msg = await msg.answer("⏳ Начинаю рассылку…")

    try:
        users_data = await api_get("/panel/users?limit=10000")
        users = users_data.get("items", users_data) if isinstance(users_data, dict) else users_data
    except Exception as e:
        return await status_msg.edit_text(f"❌ Не удалось получить пользователей: {e}")

    sent = 0
    failed = 0
    kb = mini_app_kb()

    for u in users:
        tg_id = u.get("telegram_id")
        if not tg_id:
            continue
        try:
            await bot.send_message(tg_id, text, parse_mode=ParseMode.HTML, reply_markup=kb)
            sent += 1
            await asyncio.sleep(0.05)  # Telegram rate limit ~20 msg/s
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f"✅ Рассылка завершена!\n"
        f"📤 Отправлено: <b>{sent}</b>\n"
        f"❌ Не доставлено: <b>{failed}</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=admin_menu_kb(),
    )


# ── Add Coins ─────────────────────────────────────────────────────────────────

@router.message(F.text == "💰 Начислить монеты")
@router.message(Command("addcoins"))
async def cmd_addcoins_start(msg: Message, state: FSMContext):
    if not await is_admin(msg.from_user.id):
        return
    await state.set_state(AddCoinsState.waiting_user_id)
    await msg.answer(
        "Введи <b>Telegram ID</b> пользователя:\n"
        "(или /cancel для отмены)",
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(AddCoinsState.waiting_user_id)
async def addcoins_got_user(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text.strip())
    except ValueError:
        return await msg.answer("❌ Введи числовой Telegram ID.")
    await state.update_data(telegram_id=uid)
    await state.set_state(AddCoinsState.waiting_amount)
    await msg.answer("Введи количество аркоинов (можно отрицательное для списания):")


@router.message(AddCoinsState.waiting_amount)
async def addcoins_got_amount(msg: Message, state: FSMContext):
    try:
        amount = int(msg.text.strip())
    except ValueError:
        return await msg.answer("❌ Введи целое число.")
    await state.update_data(amount=amount)
    data = await state.get_data()
    await state.set_state(AddCoinsState.waiting_confirm)
    sign = "+" if amount >= 0 else ""
    await msg.answer(
        f"Начислить <b>{sign}{amount} аркоинов</b> пользователю с TG ID <b>{data['telegram_id']}</b>?\n"
        "(да / нет)",
        parse_mode=ParseMode.HTML,
    )


@router.message(AddCoinsState.waiting_confirm)
async def addcoins_confirm(msg: Message, state: FSMContext):
    data = await state.get_data()
    if msg.text.lower() not in ("да", "yes", "y", "д"):
        await state.clear()
        return await msg.answer("❌ Отменено.", reply_markup=admin_menu_kb())

    await state.clear()
    try:
        # Find user by telegram_id via users list
        users_data = await api_get(f"/panel/users?search={data['telegram_id']}&limit=5")
        users = users_data.get("items", users_data) if isinstance(users_data, dict) else users_data
        user = next((u for u in users if u["telegram_id"] == data["telegram_id"]), None)
        if not user:
            return await msg.answer("❌ Пользователь не найден.", reply_markup=admin_menu_kb())

        await api_patch(f"/panel/users/{user['id']}/balance", {"amount": data["amount"]})
        sign = "+" if data["amount"] >= 0 else ""
        await msg.answer(
            f"✅ Готово! {user['first_name']} ({sign}{data['amount']} аркоинов)",
            reply_markup=admin_menu_kb(),
        )
    except Exception as e:
        await msg.answer(f"❌ Ошибка: {e}", reply_markup=admin_menu_kb())


# ── Open Mini App ─────────────────────────────────────────────────────────────

@router.message(F.text == "🎮 Открыть мини-апп")
async def open_mini_app(msg: Message):
    await msg.answer("Открывай:", reply_markup=mini_app_kb())


# ── /cancel ───────────────────────────────────────────────────────────────────

@router.message(Command("cancel"))
async def cmd_cancel(msg: Message, state: FSMContext):
    await state.clear()
    kb = admin_menu_kb() if await is_admin(msg.from_user.id) else None
    await msg.answer("❌ Отменено.", reply_markup=kb or ReplyKeyboardRemove())


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    if not BOT_TOKEN or BOT_TOKEN == "test_bot_token":
        log.error("BOT_TOKEN не задан!")
        return

    bot = Bot(token=BOT_TOKEN)
    dp  = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    log.info("Bot started (polling)")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
