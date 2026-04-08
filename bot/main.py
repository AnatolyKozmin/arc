"""
Arkadium 2026 — Telegram Bot
Турниры и меню — в основном кнопки (reply + inline).
Служебные команды для админов: /stats, /users, /broadcast, /addcoins, /cancel
"""

import asyncio
import logging
import os
import httpx
from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart, StateFilter
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


async def api_post(path: str, payload: dict) -> dict:
    token = await get_panel_token()
    async with httpx.AsyncClient() as client:
        r = await client.post(
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


TOURN_GAME_FROM_CB = {"bs": "brawl_stars", "cr": "clash_royale"}
TOURN_GAME_TITLE = {
    "brawl_stars": "Brawl Stars",
    "clash_royale": "Clash Royale",
}

# Тексты кнопок — выбор игры (reply)
BTN_BS = "🟢 Brawl Stars"
BTN_CR = "👑 Clash Royale"
BTN_TOURN_MENU = "🏆 Меню турниров"
BTN_TAG_HELP = "📖 Где взять ник в игре?"
BTN_FLOW_CANCEL = "❌ Отмена"
BTN_FLOW_HINT = "📖 Подсказка по нику"


def main_menu_kb() -> ReplyKeyboardMarkup:
    """Обычные пользователи — по максимуму кнопок, без команд."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎮 Аркадиум", web_app=WebAppInfo(url=MINI_APP_URL))],
            [KeyboardButton(text=BTN_BS), KeyboardButton(text=BTN_CR)],
            [KeyboardButton(text=BTN_TOURN_MENU)],
            [KeyboardButton(text=BTN_TAG_HELP)],
        ],
        resize_keyboard=True,
    )


def admin_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="👥 Пользователи")],
            [KeyboardButton(text="📢 Рассылка"), KeyboardButton(text="💰 Начислить монеты")],
            [KeyboardButton(text=BTN_BS), KeyboardButton(text=BTN_CR)],
            [KeyboardButton(text=BTN_TOURN_MENU), KeyboardButton(text="🏆 Турниры: список")],
            [KeyboardButton(text=BTN_TAG_HELP)],
            [KeyboardButton(text="🎮 Открыть мини-апп")],
        ],
        resize_keyboard=True,
    )


def tournament_hub_inline_kb() -> InlineKeyboardMarkup:
    """Дополнительные действия из «Меню турниров»."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Запись: Brawl Stars", callback_data="tourn:bs"),
                InlineKeyboardButton(text="👑 Запись: Clash Royale", callback_data="tourn:cr"),
            ],
            [
                InlineKeyboardButton(text="📖 Как найти ник?", callback_data="tourn:help"),
            ],
        ]
    )


def tournament_flow_reply_kb() -> ReplyKeyboardMarkup:
    """Во время ввода тега."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_FLOW_CANCEL)],
            [KeyboardButton(text=BTN_FLOW_HINT)],
        ],
        resize_keyboard=True,
    )


def tournament_confirm_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, записать", callback_data="tourn:save"),
                InlineKeyboardButton(text="✏️ Ввести заново", callback_data="tourn:retry"),
            ],
        ]
    )


TAG_HELP_TEXT = (
    "📖 <b>Ник в игре</b>\n\n"
    "После выбора турнира пришли <b>одним сообщением</b> свой "
    "<b>username / ник в игре</b>, как в профиле Brawl Stars или Clash Royale.\n\n"
    "<b>Telegram ID</b> и <b>@username</b> мы возьмём из Telegram сами; "
    "в сообщении нужен только игровой ник."
)


# ── FSM States ───────────────────────────────────────────────────────────────

class BroadcastState(StatesGroup):
    waiting_text    = State()
    waiting_confirm = State()


class AddCoinsState(StatesGroup):
    waiting_user_id = State()
    waiting_amount  = State()
    waiting_confirm = State()


class TournamentState(StatesGroup):
    waiting_tag = State()
    confirming = State()


# ── /start ───────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(msg: Message):
    name = msg.from_user.first_name or "Герой"
    welcome = (
        f"Привет, {name}! 👋\n\n"
        "Добро пожаловать в <b>Аркадиум 2026</b> — квест на мероприятии.\n\n"
        "Выбирай персонажа, выполняй задания, зарабатывай аркоины и попадай в топ!\n\n"
        "🏆 Турниры Brawl Stars / Clash Royale — кнопками ниже, без команд."
    )
    if await is_admin(msg.from_user.id):
        await msg.answer(welcome, parse_mode=ParseMode.HTML, reply_markup=admin_menu_kb())
    else:
        await msg.answer(welcome, parse_mode=ParseMode.HTML, reply_markup=main_menu_kb())


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
    kb = main_menu_kb()

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


# ── Tournament registration (Brawl Stars / Clash Royale) — кнопки, без команд ─


async def tournament_begin_game(message: Message, state: FSMContext, game: str) -> None:
    await state.clear()
    await state.set_state(TournamentState.waiting_tag)
    await state.update_data(game=game, pending_game_username=None)
    title = TOURN_GAME_TITLE[game]
    await message.answer(
        f"🎮 <b>{title}</b>\n\n"
        "Ниже — <b>«Отмена»</b> и <b>«Подсказка по нику»</b>.\n\n"
        "Пришли <b>одним сообщением</b> свой <b>ник в игре</b> (username из профиля игры), "
        "как показано у тебя в Brawl Stars / Clash Royale.\n\n"
        "<b>Telegram ID</b> и <b>@username</b> подставятся автоматически.\n\n"
        "<i>Один раз открой «Аркадиум» в мини-приложении — иначе запись не сохранится.</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=tournament_flow_reply_kb(),
    )


@router.message(F.text == BTN_BS)
async def tournament_reply_bs(msg: Message, state: FSMContext):
    await tournament_begin_game(msg, state, "brawl_stars")


@router.message(F.text == BTN_CR)
async def tournament_reply_cr(msg: Message, state: FSMContext):
    await tournament_begin_game(msg, state, "clash_royale")


@router.message(F.text == BTN_TOURN_MENU)
async def tournament_open_menu(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer(
        "🏆 <b>Турниры Supercell</b>\n\n"
        "Выбери игру кнопкой ниже — дальше кнопки + одно сообщение с ником в игре.",
        parse_mode=ParseMode.HTML,
        reply_markup=tournament_hub_inline_kb(),
    )


@router.message(F.text == BTN_TAG_HELP)
async def tournament_help_static(msg: Message, state: FSMContext):
    st = await state.get_state()
    if st in ("TournamentState:waiting_tag", "TournamentState:confirming"):
        return
    await msg.answer(
        TAG_HELP_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=tournament_hub_inline_kb(),
    )


@router.callback_query(F.data.in_({"tourn:bs", "tourn:cr"}))
async def tournament_cb_pick_game(query: CallbackQuery, state: FSMContext):
    await query.answer()
    key = (query.data or "").split(":")[-1]
    game = TOURN_GAME_FROM_CB.get(key)
    if not game or not query.message:
        return
    await tournament_begin_game(query.message, state, game)


@router.callback_query(F.data == "tourn:help")
async def tournament_cb_help(query: CallbackQuery):
    await query.answer()
    if query.message:
        await query.message.answer(TAG_HELP_TEXT, parse_mode=ParseMode.HTML)


@router.message(
    TournamentState.waiting_tag,
    F.text == BTN_FLOW_CANCEL,
)
@router.message(
    TournamentState.confirming,
    F.text == BTN_FLOW_CANCEL,
)
async def tournament_flow_cancel(msg: Message, state: FSMContext):
    await state.clear()
    kb = admin_menu_kb() if await is_admin(msg.from_user.id) else main_menu_kb()
    await msg.answer("❌ Запись отменена.", reply_markup=kb)


@router.message(TournamentState.waiting_tag, F.text == BTN_FLOW_HINT)
@router.message(TournamentState.confirming, F.text == BTN_FLOW_HINT)
async def tournament_flow_hint(msg: Message, state: FSMContext):
    await msg.answer(TAG_HELP_TEXT, parse_mode=ParseMode.HTML)


@router.message(TournamentState.waiting_tag, ~Command())
async def tournament_got_game_nick(msg: Message, state: FSMContext):
    if not msg.text:
        return await msg.answer("Пришли ник в игре текстом (от 2 символов).", parse_mode=ParseMode.HTML)
    raw = msg.text.strip()
    if len(raw) < 2:
        return await msg.answer("Слишком коротко — нужен ник минимум из 2 символов.")
    data = await state.get_data()
    game = data.get("game")
    if not game:
        await state.clear()
        return await msg.answer(
            "Сессия сброшена. Нажми <b>🟢 Brawl Stars</b> или <b>👑 Clash Royale</b>.",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_kb(),
        )

    await state.update_data(pending_game_username=raw)
    await state.set_state(TournamentState.confirming)
    title = TOURN_GAME_TITLE.get(game, game)
    safe = raw.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    tid = msg.from_user.id
    tun = msg.from_user.username
    if tun:
        tun_disp = f"@{tun}" if not tun.startswith("@") else tun
    else:
        tun_disp = "<i>нет username в Telegram</i>"
    await msg.answer(
        "📋 <b>Проверь данные</b>\n\n"
        f"Telegram ID: <code>{tid}</code>\n"
        f"Telegram: {tun_disp}\n"
        f"Игра: <b>{title}</b>\n"
        f"Ник в игре: <code>{safe}</code>\n\n"
        "Нажми кнопку под этим сообщением:",
        parse_mode=ParseMode.HTML,
        reply_markup=tournament_confirm_inline_kb(),
    )


@router.callback_query(F.data == "tourn:retry", StateFilter(TournamentState.confirming))
async def tournament_cb_retry(query: CallbackQuery, state: FSMContext):
    await query.answer("Можно ввести ник снова")
    await state.set_state(TournamentState.waiting_tag)
    await state.update_data(pending_game_username=None)
    if query.message:
        await query.message.answer(
            "Пришли ник в игре сообщением ещё раз.",
            reply_markup=tournament_flow_reply_kb(),
        )


@router.callback_query(F.data == "tourn:save", StateFilter(TournamentState.confirming))
async def tournament_cb_save(query: CallbackQuery, state: FSMContext):
    await query.answer()
    data = await state.get_data()
    game = data.get("game")
    raw = data.get("pending_game_username")
    if not game or not raw:
        await state.clear()
        if query.message:
            await query.message.answer(
                "Сессия устарела. Выбери игру кнопкой на клавиатуре.",
                reply_markup=main_menu_kb(),
            )
        return

    tg_id = query.from_user.id
    tg_username = query.from_user.username
    try:
        await api_post(
            "/panel/tournaments/register",
            {
                "telegram_id": tg_id,
                "telegram_username": tg_username,
                "game": game,
                "game_username": raw,
            },
        )
    except httpx.HTTPStatusError as e:
        err = str(e)
        try:
            err = e.response.json().get("detail", err)
        except Exception:
            pass
        if query.message:
            await query.message.answer(f"❌ {err}")
        return
    except Exception as e:
        if query.message:
            await query.message.answer(f"❌ Ошибка: {e}")
        return

    await state.clear()
    title = TOURN_GAME_TITLE.get(game, game)
    kb = admin_menu_kb() if await is_admin(tg_id) else main_menu_kb()
    if query.message:
        await query.message.answer(
            f"✅ Записали на <b>{title}</b>! TG id, @username и ник в игре сохранены.",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )


@router.message(TournamentState.confirming, ~Command())
async def tournament_confirming_extra_text(msg: Message):
    await msg.answer(
        "Сначала нажми кнопки <b>«Да, записать»</b> или <b>«Ввести заново»</b> под предыдущим сообщением.",
        parse_mode=ParseMode.HTML,
    )


@router.message(F.text == "🏆 Турниры: список")
async def cmd_tournament_list(msg: Message):
    if not await is_admin(msg.from_user.id):
        return
    try:
        rows = await api_get("/panel/tournaments?limit=120")
    except Exception as e:
        return await msg.answer(f"❌ {e}")
    if not rows:
        return await msg.answer("Пока никто не зарегистрировался на турниры.")
    lines_bs: list[str] = []
    lines_cr: list[str] = []
    for r in rows:
        tg = r.get("telegram_id")
        tun = r.get("telegram_username") or ""
        if tun and not str(tun).startswith("@"):
            tun = "@" + str(tun)
        elif not tun:
            tun = "—"
        nick = r.get("game_username") or ""
        line = f"• id <code>{tg}</code> {tun} — игра <code>{nick}</code>"
        if r.get("game") == "brawl_stars":
            lines_bs.append(line)
        else:
            lines_cr.append(line)
    chunks: list[str] = []
    head = "🏆 <b>Регистрации</b>\n\n"
    if lines_bs:
        chunks.append("🟢 <b>Brawl Stars</b>\n" + "\n".join(lines_bs))
    if lines_cr:
        chunks.append("👑 <b>Clash Royale</b>\n" + "\n".join(lines_cr))
    text = head + "\n\n".join(chunks)
    if len(text) > 4000:
        text = text[:3990] + "…"
    await msg.answer(text, parse_mode=ParseMode.HTML)


# ── /cancel ───────────────────────────────────────────────────────────────────

@router.message(Command("cancel"))
async def cmd_cancel(msg: Message, state: FSMContext):
    await state.clear()
    if await is_admin(msg.from_user.id):
        kb = admin_menu_kb()
    else:
        kb = main_menu_kb()
    await msg.answer("❌ Отменено.", reply_markup=kb)


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
