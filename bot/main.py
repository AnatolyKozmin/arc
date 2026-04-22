"""
Arkadium 2026 — Telegram Bot
Турниры и меню — в основном кнопки (reply + inline).
Служебные команды для админов: /stats, /users, /broadcast, /rass_6523, /rass_registration,
/rass_tournament_mk_fifa, /addcoins, /cancel
"""

import asyncio
import html
import logging
import os
from collections import Counter

import httpx
from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import BaseFilter, Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
    MenuButtonWebApp,
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


class TextIsNotCommand(BaseFilter):
    """Сообщение не начинается с /command — чтобы /cancel и др. шли в свои хендлеры."""

    async def __call__(self, message: Message) -> bool:
        if message.text is None:
            return True
        return not message.text.startswith("/")


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


async def _admin_recipient_telegram_ids() -> list[int]:
    """ID для тестовой рассылки: .env + админы из БД."""
    s = set(ADMIN_IDS)
    s.update(await get_db_admins())
    return sorted(s)


async def _in_registration_project_fsm(state: FSMContext) -> bool:
    s = await state.get_state()
    return s is not None and str(s).startswith("RegistrationProjectState")


def _telegram_error_summary(exc: BaseException) -> str:
    """Короткое описание ошибки Telegram API для отчёта."""
    msg = getattr(exc, "message", None) or str(exc) or type(exc).__name__
    return f"{type(exc).__name__}: {msg}"[:400]


def _format_mailing_report(
    *,
    title: str,
    total_recipients: int,
    sent: int,
    failures: list[tuple[int, str]],
    sample_limit: int = 50,
) -> str:
    """Текст отчёта: сколько в списке, успех, ошибки, разбивка по типам, примеры id."""
    failed = len(failures)
    lines = [
        f"✅ <b>{html.escape(title)}</b>",
        "",
        f"📋 Получателей в списке: <b>{total_recipients}</b>",
        f"📤 Успешно отправлено: <b>{sent}</b>",
        f"❌ С ошибкой: <b>{failed}</b>",
    ]
    if not failures:
        return "\n".join(lines)

    lines.extend(["", "<b>Сводка по тексту ошибок:</b>"])
    for err_text, cnt in Counter(m for _, m in failures).most_common(20):
        short = err_text[:180] + ("…" if len(err_text) > 180 else "")
        lines.append(f"• {html.escape(short)} — <b>{cnt}×</b>")

    lines.extend(["", f"<b>Не доставлено (первые {min(sample_limit, len(failures))}):</b>"])
    for tid, err in failures[:sample_limit]:
        e = err.replace("\n", " ")[:150]
        lines.append(f"• <code>{tid}</code> — {html.escape(e)}")
    if len(failures) > sample_limit:
        lines.append(f"… и ещё <b>{len(failures) - sample_limit}</b>.")

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:3990] + "\n…"
    return text


def mini_app_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🎮 Открыть Аркадиум",
            web_app=WebAppInfo(url=MINI_APP_URL),
        )
    ]])


REGPROJ_CALLBACK = "regproj:start"


def registration_invite_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📝 Зарегистрироваться на проект",
                    callback_data=REGPROJ_CALLBACK,
                ),
            ],
        ],
    )


def tournament_mk_fifa_invite_kb() -> InlineKeyboardMarkup:
    """Запись на Mortal Kombat / FIFA (без ника в игре) — к рассылке /rass_tournament_mk_fifa."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🥊 Mortal Kombat", callback_data="tourn2:pick:mk"),
                InlineKeyboardButton(text="⚽ FIFA", callback_data="tourn2:pick:fifa"),
            ],
            [
                InlineKeyboardButton(text="🥊 + ⚽ Обе дисциплины", callback_data="tourn2:pick:both"),
            ],
        ],
    )


def tournament_mk_fifa_confirm_kb(choice: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, записать", callback_data=f"tourn2:yes:{choice}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="tourn2:cancel"),
            ],
        ],
    )


TOURN2_PICK_TITLES = {
    "mk": "Mortal Kombat",
    "fifa": "FIFA",
    "both": "Mortal Kombat и FIFA",
}


def registration_project_reply_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_FLOW_CANCEL)]],
        resize_keyboard=True,
    )


TOURN_GAME_FROM_CB = {"bs": "brawl_stars", "cr": "clash_royale"}
TOURN_GAME_TITLE = {
    "brawl_stars": "Brawl Stars",
    "clash_royale": "Clash Royale",
}

# Тексты кнопок (reply)
BTN_MINI = "🎮 Аркадиум"
BTN_REG_PROJECT = "📝 Регистрация на проект"
BTN_BS = "🟢 Brawl Stars"
BTN_CR = "👑 Clash Royale"
BTN_TOURN_MENU = "🏆 Меню турниров"
BTN_TAG_HELP = "📖 Где взять ник в игре?"
BTN_FLOW_CANCEL = "❌ Отмена"
BTN_FLOW_HINT = "📖 Подсказка по нику"


def main_menu_kb() -> ReplyKeyboardMarkup:
    """Обычные пользователи — по максимуму кнопок, без команд.

    Не используем KeyboardButton(web_app=...): в клиентах Telegram тогда часто
    не передаётся initData для валидации на сервере (см. WebAppInitData в доке).
    Открытие — через кнопку меню чата (MenuButtonWebApp) или inline-кнопку.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_MINI)],
            [KeyboardButton(text=BTN_REG_PROJECT)],
        ],
        resize_keyboard=True,
    )


def admin_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="👥 Пользователи")],
            [KeyboardButton(text="📢 Рассылка"), KeyboardButton(text="💰 Начислить монеты")],
            [KeyboardButton(text="🏆 Турниры: список")],
            [KeyboardButton(text=BTN_REG_PROJECT)],
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


RASS_6523_DEFAULT_TEXT = (
    "<b>Аркадиум</b>\n\n"
    "Открой мини-приложение кнопкой ниже — так Telegram передаст данные для входа."
)


RASS_REGISTRATION_DEFAULT_TEXT = (
    "Тук-тук, на связи <b>Аркаврик</b>.\n"
    "И я с нетерпением жду нашей встречи на Ар-р-ркадиуме!\n\n"
    "<b>23 апреля</b> с <b>17:00 до 21:00</b>\n"
    "<b>4-й Вешняковский проезд, 4</b>\n\n"
    "Живые интерактивы, турниры, невероятная атмосфера, а также призы для самых активных.\n\n"
    "<b>Регистрируйся, чтобы не пропустить!</b>\n\n"
    "До встречи на проекте, твой динозавр 💜"
)

RASS_TOURN_MK_FIFA_DEFAULT_TEXT = (
    "<b>Турниры на Аркадиуме</b>\n\n"
    "Запишись на <b>Mortal Kombat</b>, <b>FIFA</b> или сразу на <b>обе дисциплины</b> — "
    "имя и фамилию мы возьмём из твоей регистрации на мероприятие, ник в игре не нужен.\n\n"
    "Нажми кнопку ниже 👇"
)


TAG_HELP_TEXT = (
    "📖 <b>Ник в игре</b>\n\n"
    "После выбора турнира пришли <b>одним сообщением</b> свой "
    "<b>username / ник в игре</b>, как в профиле Brawl Stars или Clash Royale.\n\n"
    "<b>Telegram ID</b> и <b>@username</b> мы возьмём из Telegram сами; "
    "в сообщении нужен только игровой ник."
)

# Турниры BS/CR: запись закрыта (у части пользователей старая клавиатура в кэше)
TOURNAMENT_ENDED_TEXT = (
    "🏆 <b>Brawl Stars и Clash Royale</b>\n\n"
    "Запись на этот ивент <b>закрыта</b> — мероприятие уже прошло.\n\n"
    "Новости и активности смотри в мини-приложении <b>Аркадиум</b>."
)


async def _reply_tournament_ended(msg: Message) -> None:
    """Заглушка: турниры BS/CR больше не принимают запись (старые кнопки в кэше)."""
    kb = admin_menu_kb() if await is_admin(msg.from_user.id) else main_menu_kb()
    await msg.answer(TOURNAMENT_ENDED_TEXT, parse_mode=ParseMode.HTML, reply_markup=kb)


async def _reply_tournament_ended_callback(query: CallbackQuery) -> None:
    """То же для inline-кнопок старого «Меню турниров»."""
    uid = query.from_user.id if query.from_user else 0
    kb = admin_menu_kb() if await is_admin(uid) else main_menu_kb()
    if query.message:
        await query.message.answer(
            TOURNAMENT_ENDED_TEXT,
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )


# ── FSM States ───────────────────────────────────────────────────────────────

class BroadcastState(StatesGroup):
    waiting_text    = State()
    waiting_confirm = State()


class Rass6523State(StatesGroup):
    """Рассылка с inline web_app (initData), без reply-клавиатуры."""

    waiting_text = State()
    waiting_confirm = State()


class AddCoinsState(StatesGroup):
    waiting_user_id = State()
    waiting_amount  = State()
    waiting_confirm = State()


class TournamentState(StatesGroup):
    waiting_tag = State()
    confirming = State()


class RassRegistrationState(StatesGroup):
    """Рассылка приглашения с кнопкой регистрации на проект (анкета в боте)."""

    waiting_text = State()
    waiting_scope = State()  # тест / все
    waiting_confirm = State()


class RassTournamentMkFifaState(StatesGroup):
    """Рассылка зарегистрированным на мероприятие: запись на MK / FIFA (без ника в игре)."""

    waiting_text = State()
    waiting_scope = State()  # тест / все зарегистрированные
    waiting_confirm = State()


class RegistrationProjectState(StatesGroup):
    """Анкета после нажатия «Зарегистрироваться на проект»."""

    first_name = State()
    last_name = State()
    university = State()
    course = State()
    group = State()
    confirming = State()


# ── /start ───────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(msg: Message):
    name = msg.from_user.first_name or "Герой"
    welcome = (
        f"Привет, {name}! 👋\n\n"
        "Добро пожаловать в <b>Аркадиум 2026</b> — квест на мероприятии.\n\n"
        "Выбирай персонажа, выполняй задания, зарабатывай аркоины и попадай в топ!"
    )

    # Сначала запись в БД (как в мини-аппе), чтобы знать is_registered
    ensured: dict | None = None
    try:
        ensured = await api_post(
            "/panel/users/ensure",
            {
                "telegram_id": msg.from_user.id,
                "username": msg.from_user.username,
                "first_name": msg.from_user.first_name or "",
                "last_name": msg.from_user.last_name,
            },
        )
    except Exception as e:
        log.warning("ensure_user /start: %s", e)

    if await is_admin(msg.from_user.id):
        await msg.answer(welcome, parse_mode=ParseMode.HTML, reply_markup=admin_menu_kb())
    else:
        await msg.answer(welcome, parse_mode=ParseMode.HTML, reply_markup=main_menu_kb())

    # Новички без регистрации в приложении — предлагаем ту же анкету, что и в рассылке
    if ensured and not ensured.get("is_registered"):
        await msg.answer(
            "📝 <b>Регистрация на проект</b>\n\n"
            "Заполни анкету: имя, фамилию, вуз, курс и группу — "
            "так мы учтём тебя в программе мероприятия.\n\n"
            "Можно нажать кнопку <b>ниже</b> или в любой момент — "
            f"<b>{html.escape(BTN_REG_PROJECT)}</b> на клавиатуре под полем ввода.",
            parse_mode=ParseMode.HTML,
            reply_markup=registration_invite_kb(),
        )


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
        reg = await api_get("/panel/stats/registrations")
    except Exception as e:
        return await msg.answer(f"❌ Ошибка: {e}")

    text = (
        "📊 <b>Статистика Аркадиум</b>\n\n"
        f"👤 Всего пользователей: <b>{data['total_users']}</b>\n"
        f"✅ Зарегистрировано (анкета): <b>{data['registered_users']}</b>\n"
        f"🛍 Товаров в магазине: <b>{data['total_products']}</b>\n"
        f"📢 Объявлений: <b>{data['total_announcements']}</b>\n"
        f"🏅 Достижений: <b>{data['total_achievements']}</b>"
    )
    await msg.answer(text, parse_mode=ParseMode.HTML)

    # Детализация по зарегистрированным (вуз / курс)
    total_r = reg.get("registered_total", 0)
    if total_r == 0:
        await msg.answer(
            "📋 <b>Зарегистрированные:</b> пока <b>0</b> — разбивки по вузам и курсам нет.",
            parse_mode=ParseMode.HTML,
        )
        return

    lines = [
        "📋 <b>Зарегистрированные участники</b>",
        f"Всего в анкете: <b>{total_r}</b> чел.",
        "",
        "<b>По вузам</b> (по убыванию числа человек):",
    ]
    uni = reg.get("by_university") or []
    max_uni = 40
    for row in uni[:max_uni]:
        lab = html.escape(str(row.get("label", "—")))
        lines.append(f"• {lab} — <b>{row.get('count', 0)}</b>")
    if len(uni) > max_uni:
        lines.append(f"… всего разных вузов в базе: <b>{len(uni)}</b>")

    lines.extend(["", "<b>По курсу:</b>"])
    for row in reg.get("by_course") or []:
        lab = html.escape(str(row.get("label", "—")))
        lines.append(f"• {lab} — <b>{row.get('count', 0)}</b>")

    text2 = "\n".join(lines)
    if len(text2) > 4000:
        text2 = text2[:3990] + "…"
    await msg.answer(text2, parse_mode=ParseMode.HTML)


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
    failures: list[tuple[int, str]] = []
    kb = main_menu_kb()
    targets = [u for u in users if u.get("telegram_id")]
    total_recipients = len(targets)

    for u in targets:
        tg_id = u["telegram_id"]
        try:
            await bot.send_message(tg_id, text, parse_mode=ParseMode.HTML, reply_markup=kb)
            sent += 1
            await asyncio.sleep(0.05)  # Telegram rate limit ~20 msg/s
        except Exception as ex:
            failures.append((tg_id, _telegram_error_summary(ex)))
            log.warning("broadcast send to %s: %s", tg_id, ex)

    report = _format_mailing_report(
        title="Рассылка (reply-клавиатура)",
        total_recipients=total_recipients,
        sent=sent,
        failures=failures,
    )
    await status_msg.edit_text(report, parse_mode=ParseMode.HTML)
    await msg.answer("⌨️ Меню админа:", reply_markup=admin_menu_kb())


# ── /rass_6523 — рассылка с inline web_app (нормальная кнопка входа) ────────────

@router.message(Command("rass_6523"))
async def cmd_rass_6523_start(msg: Message, state: FSMContext):
    if not await is_admin(msg.from_user.id):
        return
    await state.set_state(Rass6523State.waiting_text)
    await msg.answer(
        "✍️ <b>Рассылка с кнопкой «Открыть Аркадиум»</b> (inline web_app, с initData).\n\n"
        "Пришли текст сообщения в <b>HTML</b> или отправь <code>/default</code> — подставлю шаблон.\n\n"
        "/cancel — отмена.",
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(Rass6523State.waiting_text, Command("cancel"))
@router.message(Rass6523State.waiting_confirm, Command("cancel"))
async def rass_6523_cancel(msg: Message, state: FSMContext):
    await state.clear()
    kb = admin_menu_kb() if await is_admin(msg.from_user.id) else main_menu_kb()
    await msg.answer("❌ Отменено.", reply_markup=kb)


@router.message(Rass6523State.waiting_text)
async def rass_6523_got_text(msg: Message, state: FSMContext):
    if not await is_admin(msg.from_user.id):
        await state.clear()
        return
    if msg.text and msg.text.strip().lower() in ("/default", "default"):
        text = RASS_6523_DEFAULT_TEXT
    else:
        text = msg.html_text or msg.text or ""
        if not text.strip():
            return await msg.answer("Пустой текст. Пришли HTML или <code>/default</code>.", parse_mode=ParseMode.HTML)
    await state.update_data(text=text)
    await state.set_state(Rass6523State.waiting_confirm)
    await msg.answer(
        f"📋 Сообщение:\n\n{text}\n\n"
        "➕ К нему будет добавлена одна inline-кнопка открытия мини-аппа.\n\n"
        "Разослать всем из базы (кто хоть раз нажал /start)? <b>да / нет</b>",
        parse_mode=ParseMode.HTML,
    )


@router.message(Rass6523State.waiting_confirm)
async def rass_6523_confirm(msg: Message, state: FSMContext, bot: Bot):
    if not await is_admin(msg.from_user.id):
        await state.clear()
        return
    if msg.text is None or msg.text.lower() not in ("да", "yes", "y", "д"):
        await state.clear()
        await msg.answer("❌ Отменено.", reply_markup=admin_menu_kb())
        return

    data = await state.get_data()
    text = data["text"]
    await state.clear()

    status_msg = await msg.answer("⏳ Рассылка с кнопкой web_app…")

    try:
        users_data = await api_get("/panel/users?limit=10000")
        users = users_data.get("items", users_data) if isinstance(users_data, dict) else users_data
    except Exception as e:
        return await status_msg.edit_text(f"❌ Не удалось получить пользователей: {e}")

    kb = mini_app_kb()
    sent = 0
    failures: list[tuple[int, str]] = []
    targets = [u for u in users if u.get("telegram_id")]
    total_recipients = len(targets)

    for u in targets:
        tg_id = u["telegram_id"]
        try:
            await bot.send_message(
                tg_id,
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
            )
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as ex:
            failures.append((tg_id, _telegram_error_summary(ex)))
            log.warning("rass_6523 send to %s: %s", tg_id, ex)

    report = _format_mailing_report(
        title="Рассылка /rass_6523 (inline web_app)",
        total_recipients=total_recipients,
        sent=sent,
        failures=failures,
    )
    await status_msg.edit_text(report, parse_mode=ParseMode.HTML)
    await msg.answer("⌨️ Меню админа:", reply_markup=admin_menu_kb())


# ── /rass_registration — рассылка + кнопка анкеты регистрации на проект ───────

@router.message(Command("rass_registration"))
async def cmd_rass_registration_start(msg: Message, state: FSMContext):
    if not await is_admin(msg.from_user.id):
        return
    await state.set_state(RassRegistrationState.waiting_text)
    await msg.answer(
        "✍️ <b>Рассылка с регистрацией на проект</b>\n\n"
        "К сообщению будет добавлена кнопка «Зарегистрироваться на проект» — "
        "после нажатия человек заполнит в боте: имя, фамилию, вуз, курс, группу "
        "(а @username возьмём из Telegram).\n\n"
        "Пришли текст в <b>HTML</b> или <code>/default</code> — подставлю шаблон Аркаврика.\n\n"
        "/cancel — отмена.",
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(RassRegistrationState.waiting_text, Command("cancel"))
@router.message(RassRegistrationState.waiting_scope, Command("cancel"))
@router.message(RassRegistrationState.waiting_confirm, Command("cancel"))
async def rass_registration_cancel_cmd(msg: Message, state: FSMContext):
    await state.clear()
    kb = admin_menu_kb() if await is_admin(msg.from_user.id) else main_menu_kb()
    await msg.answer("❌ Отменено.", reply_markup=kb)


@router.message(RassRegistrationState.waiting_text)
async def rass_registration_got_text(msg: Message, state: FSMContext):
    if not await is_admin(msg.from_user.id):
        await state.clear()
        return
    if msg.text and msg.text.strip().lower() in ("/default", "default"):
        text = RASS_REGISTRATION_DEFAULT_TEXT
    else:
        text = msg.html_text or msg.text or ""
        if not text.strip():
            return await msg.answer("Пустой текст. Пришли HTML или <code>/default</code>.", parse_mode=ParseMode.HTML)
    await state.update_data(mail_text=text)
    await state.set_state(RassRegistrationState.waiting_scope)
    await msg.answer(
        "📬 <b>Кому отправить?</b>\n\n"
        "• <code>тест</code> — только <b>админам</b> (ADMIN_TELEGRAM_IDS + список из веб-панели)\n"
        "• <code>все</code> — всем из базы (кто хоть раз нажал /start)\n\n"
        "Напиши одно слово: <b>тест</b> или <b>все</b>.",
        parse_mode=ParseMode.HTML,
    )


@router.message(RassRegistrationState.waiting_scope)
async def rass_registration_got_scope(msg: Message, state: FSMContext):
    if not await is_admin(msg.from_user.id):
        await state.clear()
        return
    if not msg.text:
        return await msg.answer("Напиши <b>тест</b> или <b>все</b>.", parse_mode=ParseMode.HTML)
    raw = msg.text.strip().lower()
    if raw in ("тест", "test", "t"):
        scope = "test"
        scope_human = "только админы (тест)"
    elif raw in ("все", "всё", "all", "a"):
        scope = "all"
        scope_human = "все из базы"
    else:
        return await msg.answer("Нужно слово <b>тест</b> или <b>все</b>.", parse_mode=ParseMode.HTML)

    await state.update_data(scope=scope)
    await state.set_state(RassRegistrationState.waiting_confirm)
    data = await state.get_data()
    text = data["mail_text"]
    await msg.answer(
        f"📋 <b>Предпросмотр</b> ({scope_human})\n\n{text}\n\n"
        "➕ К сообщению будет inline-кнопка регистрации.\n\n"
        "Отправить? <b>да / нет</b>",
        parse_mode=ParseMode.HTML,
    )


@router.message(RassRegistrationState.waiting_confirm)
async def rass_registration_confirm(msg: Message, state: FSMContext, bot: Bot):
    if not await is_admin(msg.from_user.id):
        await state.clear()
        return
    if msg.text is None or msg.text.lower() not in ("да", "yes", "y", "д"):
        await state.clear()
        await msg.answer("❌ Отменено.", reply_markup=admin_menu_kb())
        return

    data = await state.get_data()
    text = data["mail_text"]
    test_only = data.get("scope") == "test"
    await state.clear()

    status_msg = await msg.answer("⏳ Рассылка…")

    kb = registration_invite_kb()
    sent = 0
    failures: list[tuple[int, str]] = []

    if test_only:
        targets = await _admin_recipient_telegram_ids()
        total_recipients = len(targets)
        for tg_id in targets:
            try:
                await bot.send_message(tg_id, text, parse_mode=ParseMode.HTML, reply_markup=kb)
                sent += 1
                await asyncio.sleep(0.05)
            except Exception as ex:
                failures.append((tg_id, _telegram_error_summary(ex)))
                log.warning("rass_registration test send to %s: %s", tg_id, ex)
        title = "Рассылка /rass_registration (тест — только админы)"
    else:
        try:
            users_data = await api_get("/panel/users?limit=10000")
            users = users_data.get("items", users_data) if isinstance(users_data, dict) else users_data
        except Exception as e:
            return await status_msg.edit_text(f"❌ Не удалось получить пользователей: {e}")
        targets_list = [u for u in users if u.get("telegram_id")]
        total_recipients = len(targets_list)
        for u in targets_list:
            tg_id = u["telegram_id"]
            try:
                await bot.send_message(tg_id, text, parse_mode=ParseMode.HTML, reply_markup=kb)
                sent += 1
                await asyncio.sleep(0.05)
            except Exception as ex:
                failures.append((tg_id, _telegram_error_summary(ex)))
                log.warning("rass_registration send to %s: %s", tg_id, ex)
        title = "Рассылка /rass_registration (все из базы)"

    report = _format_mailing_report(
        title=title,
        total_recipients=total_recipients,
        sent=sent,
        failures=failures,
    )
    await status_msg.edit_text(report, parse_mode=ParseMode.HTML)
    await msg.answer("⌨️ Меню админа:", reply_markup=admin_menu_kb())


# ── /rass_tournament_mk_fifa — рассылка зарегистрированным: MK / FIFA (без ника) ─

@router.message(Command("rass_tournament_mk_fifa"))
async def cmd_rass_tournament_mk_fifa_start(msg: Message, state: FSMContext):
    if not await is_admin(msg.from_user.id):
        return
    await state.set_state(RassTournamentMkFifaState.waiting_text)
    await msg.answer(
        "✍️ <b>Рассылка: турниры Mortal Kombat / FIFA</b>\n\n"
        "Получатели с заполненной <b>регистрацией на мероприятие</b> (анкета в боте или мини-аппе).\n"
        "К сообщению добавятся кнопки: <b>MK</b>, <b>FIFA</b> или <b>обе</b> — "
        "ник в игре не спрашиваем, имя и фамилию берём из профиля Аркадиума.\n\n"
        "Пришли текст в <b>HTML</b> или <code>/default</code> — подставлю шаблон.\n\n"
        "/cancel — отмена.",
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(RassTournamentMkFifaState.waiting_text, Command("cancel"))
@router.message(RassTournamentMkFifaState.waiting_scope, Command("cancel"))
@router.message(RassTournamentMkFifaState.waiting_confirm, Command("cancel"))
async def rass_tournament_mk_fifa_cancel_cmd(msg: Message, state: FSMContext):
    await state.clear()
    kb = admin_menu_kb() if await is_admin(msg.from_user.id) else main_menu_kb()
    await msg.answer("❌ Отменено.", reply_markup=kb)


@router.message(RassTournamentMkFifaState.waiting_text)
async def rass_tournament_mk_fifa_got_text(msg: Message, state: FSMContext):
    if not await is_admin(msg.from_user.id):
        await state.clear()
        return
    if msg.text and msg.text.strip().lower() in ("/default", "default"):
        text = RASS_TOURN_MK_FIFA_DEFAULT_TEXT
    else:
        text = msg.html_text or msg.text or ""
        if not text.strip():
            return await msg.answer("Пустой текст. Пришли HTML или <code>/default</code>.", parse_mode=ParseMode.HTML)
    await state.update_data(mail_text=text)
    await state.set_state(RassTournamentMkFifaState.waiting_scope)
    await msg.answer(
        "📬 <b>Кому отправить?</b>\n\n"
        "• <code>тест</code> — только <b>админам</b> (для проверки кнопок)\n"
        "• <code>все</code> — всем с анкетой на мероприятие (<b>зарегистрированным</b>)\n\n"
        "Напиши одно слово: <b>тест</b> или <b>все</b>.",
        parse_mode=ParseMode.HTML,
    )


@router.message(RassTournamentMkFifaState.waiting_scope)
async def rass_tournament_mk_fifa_got_scope(msg: Message, state: FSMContext):
    if not await is_admin(msg.from_user.id):
        await state.clear()
        return
    if not msg.text:
        return await msg.answer("Напиши <b>тест</b> или <b>все</b>.", parse_mode=ParseMode.HTML)
    raw = msg.text.strip().lower()
    if raw in ("тест", "test", "t"):
        scope = "test"
        scope_human = "только админы (тест)"
    elif raw in ("все", "всё", "all", "a"):
        scope = "registered"
        scope_human = "все зарегистрированные на мероприятие"
    else:
        return await msg.answer("Нужно слово <b>тест</b> или <b>все</b>.", parse_mode=ParseMode.HTML)

    await state.update_data(scope=scope)
    await state.set_state(RassTournamentMkFifaState.waiting_confirm)
    data = await state.get_data()
    text = data["mail_text"]
    await msg.answer(
        f"📋 <b>Предпросмотр</b> ({scope_human})\n\n{text}\n\n"
        "➕ К сообщению будут кнопки записи на MK / FIFA.\n\n"
        "Отправить? <b>да / нет</b>",
        parse_mode=ParseMode.HTML,
    )


@router.message(RassTournamentMkFifaState.waiting_confirm)
async def rass_tournament_mk_fifa_confirm(msg: Message, state: FSMContext, bot: Bot):
    if not await is_admin(msg.from_user.id):
        await state.clear()
        return
    if msg.text is None or msg.text.lower() not in ("да", "yes", "y", "д"):
        await state.clear()
        await msg.answer("❌ Отменено.", reply_markup=admin_menu_kb())
        return

    data = await state.get_data()
    text = data["mail_text"]
    test_only = data.get("scope") == "test"
    await state.clear()

    status_msg = await msg.answer("⏳ Рассылка…")

    kb = tournament_mk_fifa_invite_kb()
    sent = 0
    failures: list[tuple[int, str]] = []

    if test_only:
        targets = await _admin_recipient_telegram_ids()
        total_recipients = len(targets)
        for tg_id in targets:
            try:
                await bot.send_message(tg_id, text, parse_mode=ParseMode.HTML, reply_markup=kb)
                sent += 1
                await asyncio.sleep(0.05)
            except Exception as ex:
                failures.append((tg_id, _telegram_error_summary(ex)))
                log.warning("rass_tournament_mk_fifa test send to %s: %s", tg_id, ex)
        title = "Рассылка /rass_tournament_mk_fifa (тест — только админы)"
    else:
        try:
            users_data = await api_get("/panel/users?registered_only=true&limit=10000")
            users = users_data.get("items", users_data) if isinstance(users_data, dict) else users_data
        except Exception as e:
            return await status_msg.edit_text(f"❌ Не удалось получить пользователей: {e}")
        targets_list = [u for u in users if u.get("telegram_id")]
        total_recipients = len(targets_list)
        for u in targets_list:
            tg_id = u["telegram_id"]
            try:
                await bot.send_message(tg_id, text, parse_mode=ParseMode.HTML, reply_markup=kb)
                sent += 1
                await asyncio.sleep(0.05)
            except Exception as ex:
                failures.append((tg_id, _telegram_error_summary(ex)))
                log.warning("rass_tournament_mk_fifa send to %s: %s", tg_id, ex)
        title = "Рассылка /rass_tournament_mk_fifa (зарегистрированные на мероприятие)"

    report = _format_mailing_report(
        title=title,
        total_recipients=total_recipients,
        sent=sent,
        failures=failures,
    )
    await status_msg.edit_text(report, parse_mode=ParseMode.HTML)
    await msg.answer("⌨️ Меню админа:", reply_markup=admin_menu_kb())


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

@router.message(F.text == BTN_MINI)
async def open_mini_from_main_menu(msg: Message, state: FSMContext):
    if await _in_registration_project_fsm(state):
        return await msg.answer(
            "⏳ Сначала завершите регистрацию на проект или нажми /cancel.",
            parse_mode=ParseMode.HTML,
        )
    await msg.answer("Открой мини-приложение кнопкой ниже — так Telegram передаёт данные для входа.", reply_markup=mini_app_kb())


@router.message(F.text == "🎮 Открыть мини-апп")
async def open_mini_app(msg: Message, state: FSMContext):
    if await _in_registration_project_fsm(state):
        return await msg.answer(
            "⏳ Сначала завершите регистрацию на проект или нажми /cancel.",
            parse_mode=ParseMode.HTML,
        )
    await msg.answer("Открывай:", reply_markup=mini_app_kb())


# ── Tournament MK / FIFA (без ника в игре, имя/фамилия из профиля) ─────────────

TOURN2_GAMES = {
    "mk": ["mortal_kombat"],
    "fifa": ["fifa"],
    "both": ["mortal_kombat", "fifa"],
}


@router.callback_query(F.data.startswith("tourn2:pick:"))
async def tourn2_cb_pick(query: CallbackQuery, state: FSMContext):
    if not query.from_user or not query.message:
        return await query.answer()
    if await _in_registration_project_fsm(state):
        await query.answer("Сначала заверши анкету на проект или /cancel", show_alert=True)
        return
    parts = (query.data or "").split(":")
    choice = parts[-1] if len(parts) >= 3 else ""
    if choice not in TOURN2_PICK_TITLES:
        return await query.answer("Неизвестный вариант", show_alert=True)
    await query.answer()
    title = TOURN2_PICK_TITLES[choice]
    await query.message.answer(
        "🎮 <b>Запись на турнир</b>: "
        f"{html.escape(title)}\n\n"
        "Имя и фамилию возьмём из твоей <b>регистрации на мероприятие</b> в Аркадиуме. "
        "Ник в игре <b>не нужен</b>.\n\n"
        "Подтверждаешь?",
        parse_mode=ParseMode.HTML,
        reply_markup=tournament_mk_fifa_confirm_kb(choice),
    )


@router.callback_query(F.data.startswith("tourn2:yes:"))
async def tourn2_cb_yes(query: CallbackQuery, state: FSMContext):
    if not query.from_user or not query.message:
        return await query.answer()
    if await _in_registration_project_fsm(state):
        await query.answer("Сначала заверши анкету на проект или /cancel", show_alert=True)
        return
    parts = (query.data or "").split(":")
    choice = parts[-1] if len(parts) >= 3 else ""
    games = TOURN2_GAMES.get(choice)
    if not games:
        return await query.answer("Неизвестный вариант", show_alert=True)

    uid = query.from_user.id
    tun = query.from_user.username
    errs: list[str] = []
    for g in games:
        try:
            await api_post(
                "/panel/tournaments/register",
                {
                    "telegram_id": uid,
                    "telegram_username": tun,
                    "game": g,
                    "game_username": None,
                },
            )
        except httpx.HTTPStatusError as e:
            detail = str(e)
            try:
                body = e.response.json()
                if isinstance(body.get("detail"), str):
                    detail = body["detail"]
            except Exception:
                pass
            errs.append(f"{g}: {detail}")

    try:
        await query.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    if errs:
        await query.answer("Часть записей не удалась", show_alert=True)
        err_text = "\n".join(html.escape(x) for x in errs[:5])
        await query.message.answer(
            "❌ <b>Не удалось записать</b>\n\n" + err_text,
            parse_mode=ParseMode.HTML,
        )
        return

    await query.answer("Записано!")
    done_title = TOURN2_PICK_TITLES.get(choice, choice)
    await query.message.answer(
        f"✅ Ты в списке: <b>{html.escape(done_title)}</b>. Удачи на турнире!",
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "tourn2:cancel")
async def tourn2_cb_cancel(query: CallbackQuery, state: FSMContext):
    await query.answer("Ок")
    if await _in_registration_project_fsm(state):
        return
    if query.message:
        try:
            await query.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await query.message.answer("Запись отменена.")


# ── Tournament registration (Brawl Stars / Clash Royale) — только заглушка ────
# У части пользователей в кэше остались старые кнопки; запись на ивент закрыта.


@router.message(F.text == BTN_BS)
async def tournament_reply_bs(msg: Message, state: FSMContext):
    if await _in_registration_project_fsm(state):
        return await msg.answer(
            "⏳ Сначала завершите регистрацию на проект или нажми /cancel.",
            parse_mode=ParseMode.HTML,
        )
    await state.clear()
    await _reply_tournament_ended(msg)


@router.message(F.text == BTN_CR)
async def tournament_reply_cr(msg: Message, state: FSMContext):
    if await _in_registration_project_fsm(state):
        return await msg.answer(
            "⏳ Сначала завершите регистрацию на проект или нажми /cancel.",
            parse_mode=ParseMode.HTML,
        )
    await state.clear()
    await _reply_tournament_ended(msg)


@router.message(F.text == BTN_TOURN_MENU)
async def tournament_open_menu(msg: Message, state: FSMContext):
    if await _in_registration_project_fsm(state):
        return await msg.answer(
            "⏳ Сначала завершите регистрацию на проект или нажми /cancel.",
            parse_mode=ParseMode.HTML,
        )
    await state.clear()
    await _reply_tournament_ended(msg)


@router.message(F.text == BTN_TAG_HELP)
async def tournament_help_static(msg: Message, state: FSMContext):
    await state.clear()
    await _reply_tournament_ended(msg)


@router.callback_query(F.data.in_({"tourn:bs", "tourn:cr"}))
async def tournament_cb_pick_game(query: CallbackQuery, state: FSMContext):
    await query.answer("Ивент уже прошёл", show_alert=True)
    if await _in_registration_project_fsm(state):
        return
    await state.clear()
    await _reply_tournament_ended_callback(query)


@router.callback_query(F.data == "tourn:help")
async def tournament_cb_help(query: CallbackQuery):
    await query.answer()
    await _reply_tournament_ended_callback(query)


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
    await _reply_tournament_ended(msg)


@router.message(TournamentState.waiting_tag, F.text == BTN_FLOW_HINT)
@router.message(TournamentState.confirming, F.text == BTN_FLOW_HINT)
async def tournament_flow_hint(msg: Message, state: FSMContext):
    await state.clear()
    await _reply_tournament_ended(msg)


@router.message(TournamentState.waiting_tag, TextIsNotCommand())
async def tournament_got_game_nick(msg: Message, state: FSMContext):
    """Старая сессия записи на турнир — ивент закрыт, сбрасываем FSM."""
    await state.clear()
    await _reply_tournament_ended(msg)


@router.callback_query(F.data == "tourn:retry", StateFilter(TournamentState.confirming))
async def tournament_cb_retry(query: CallbackQuery, state: FSMContext):
    await query.answer("Ивент уже прошёл", show_alert=True)
    await state.clear()
    await _reply_tournament_ended_callback(query)


@router.callback_query(F.data == "tourn:save", StateFilter(TournamentState.confirming))
async def tournament_cb_save(query: CallbackQuery, state: FSMContext):
    await query.answer("Ивент уже прошёл", show_alert=True)
    await state.clear()
    await _reply_tournament_ended_callback(query)


@router.message(TournamentState.confirming, TextIsNotCommand())
async def tournament_confirming_extra_text(msg: Message, state: FSMContext):
    """Любой текст вместо кнопок подтверждения — закрываем сессию и показываем заглушку."""
    await state.clear()
    await _reply_tournament_ended(msg)


# ── Регистрация на проект (рассылка /start / reply-кнопка) ────────────────────


async def _begin_registration_project_flow(message: Message, state: FSMContext, from_user) -> None:
    """Старт анкеты: имя → … → подтверждение (общий код для inline и reply-кнопки)."""
    await state.clear()
    await state.set_state(RegistrationProjectState.first_name)
    tun = from_user.username
    un_disp = f"@{tun}" if tun else "(нет публичного @username)"
    await message.answer(
        "📝 <b>Регистрация на проект «Аркадиум»</b>\n\n"
        f"Твой Telegram: {html.escape(un_disp)}\n\n"
        "Введи <b>имя</b>.\n"
        "/cancel — выйти из анкеты.",
        parse_mode=ParseMode.HTML,
        reply_markup=registration_project_reply_kb(),
    )


@router.message(F.text == BTN_REG_PROJECT)
async def regproj_from_menu_button(msg: Message, state: FSMContext):
    """Постоянная клавиатура — если не было рассылки, человек всё равно может зарегистрироваться."""
    if await _in_registration_project_fsm(state):
        return await msg.answer(
            "Сначала заверши анкету или нажми /cancel.",
            parse_mode=ParseMode.HTML,
        )
    ensured: dict | None = None
    try:
        ensured = await api_post(
            "/panel/users/ensure",
            {
                "telegram_id": msg.from_user.id,
                "username": msg.from_user.username,
                "first_name": msg.from_user.first_name or "",
                "last_name": msg.from_user.last_name,
            },
        )
    except Exception as e:
        log.warning("ensure_user reg button: %s", e)
        return await msg.answer("❌ Не удалось связаться с сервером. Попробуй позже.")

    if ensured.get("is_registered"):
        return await msg.answer(
            "✅ Ты уже зарегистрирован(а) в проекте. При необходимости измени данные в мини-приложении.",
            parse_mode=ParseMode.HTML,
        )
    await _begin_registration_project_flow(msg, state, msg.from_user)


@router.callback_query(F.data == REGPROJ_CALLBACK)
async def regproj_cb_start(query: CallbackQuery, state: FSMContext):
    await query.answer()
    if not query.from_user or not query.message:
        return
    await _begin_registration_project_flow(query.message, state, query.from_user)


@router.message(
    StateFilter(
        RegistrationProjectState.first_name,
        RegistrationProjectState.last_name,
        RegistrationProjectState.university,
        RegistrationProjectState.course,
        RegistrationProjectState.group,
    ),
    F.text == BTN_FLOW_CANCEL,
)
async def regproj_flow_cancel_btn(msg: Message, state: FSMContext):
    await state.clear()
    kb = admin_menu_kb() if await is_admin(msg.from_user.id) else main_menu_kb()
    await msg.answer("❌ Регистрация отменена.", reply_markup=kb)


@router.message(RegistrationProjectState.first_name, TextIsNotCommand())
async def regproj_got_first_name(msg: Message, state: FSMContext):
    raw = (msg.text or "").strip()
    if len(raw) < 1:
        return await msg.answer("Введи имя текстом.")
    await state.update_data(first_name=raw)
    await state.set_state(RegistrationProjectState.last_name)
    await msg.answer(
        "Фамилия:",
        parse_mode=ParseMode.HTML,
        reply_markup=registration_project_reply_kb(),
    )


@router.message(RegistrationProjectState.last_name, TextIsNotCommand())
async def regproj_got_last_name(msg: Message, state: FSMContext):
    raw = (msg.text or "").strip()
    if len(raw) < 1:
        return await msg.answer("Введи фамилию (можно через дефис, если двойная).")
    await state.update_data(last_name=raw)
    await state.set_state(RegistrationProjectState.university)
    await msg.answer(
        "ВУЗ (полное или краткое название):",
        reply_markup=registration_project_reply_kb(),
    )


@router.message(RegistrationProjectState.university, TextIsNotCommand())
async def regproj_got_university(msg: Message, state: FSMContext):
    raw = (msg.text or "").strip()
    if len(raw) < 2:
        return await msg.answer("Слишком коротко — укажи название вуза.")
    await state.update_data(university=raw)
    await state.set_state(RegistrationProjectState.course)
    await msg.answer(
        "Курс (число от 1 до 12):",
        reply_markup=registration_project_reply_kb(),
    )


@router.message(RegistrationProjectState.course, TextIsNotCommand())
async def regproj_got_course(msg: Message, state: FSMContext):
    try:
        c = int((msg.text or "").strip())
    except ValueError:
        return await msg.answer("Нужно целое число, например <code>2</code>.", parse_mode=ParseMode.HTML)
    if c < 1 or c > 12:
        return await msg.answer("Курс от 1 до 12.")
    await state.update_data(course=c)
    await state.set_state(RegistrationProjectState.group)
    await msg.answer(
        "Группа (например <code>БИ-101</code>):",
        parse_mode=ParseMode.HTML,
        reply_markup=registration_project_reply_kb(),
    )


@router.message(RegistrationProjectState.group, TextIsNotCommand())
async def regproj_got_group(msg: Message, state: FSMContext):
    raw = (msg.text or "").strip()
    if len(raw) < 1 or len(raw) > 50:
        return await msg.answer("Группа: от 1 до 50 символов.")
    await state.update_data(group=raw)
    data = await state.get_data()
    fn = data["first_name"]
    ln = data["last_name"]
    uni = html.escape(data["university"])
    gr = html.escape(data["group"])
    tun = msg.from_user.username
    tun_disp = f"@{tun}" if tun else "—"
    await state.set_state(RegistrationProjectState.confirming)
    await msg.answer(
        "📋 <b>Проверь данные</b>\n\n"
        f"Telegram: {html.escape(tun_disp)}\n"
        f"Имя: <b>{html.escape(fn)}</b>\n"
        f"Фамилия: <b>{html.escape(ln)}</b>\n"
        f"ВУЗ: {uni}\n"
        f"Курс: <b>{data['course']}</b>\n"
        f"Группа: <code>{gr}</code>\n\n"
        "Отправить в систему? <b>да / нет</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(RegistrationProjectState.confirming)
async def regproj_confirm_save(msg: Message, state: FSMContext):
    if not msg.text:
        return await msg.answer("Ответь <b>да</b> или <b>нет</b>.", parse_mode=ParseMode.HTML)
    t = msg.text.strip().lower()
    if t in ("нет", "no", "n"):
        await state.clear()
        kb = admin_menu_kb() if await is_admin(msg.from_user.id) else main_menu_kb()
        return await msg.answer(
            "Ок. Можно снова нажать кнопку в сообщении с рассылкой.",
            reply_markup=kb,
        )
    if t not in ("да", "yes", "y", "д"):
        return await msg.answer("Напиши <b>да</b> или <b>нет</b>.", parse_mode=ParseMode.HTML)

    data = await state.get_data()
    await state.clear()
    tg_id = msg.from_user.id
    tg_username = msg.from_user.username
    full_name = f"{data['first_name']} {data['last_name']}".strip()
    payload = {
        "telegram_id": tg_id,
        "username": tg_username,
        "first_name": data["first_name"],
        "last_name": data["last_name"],
        "full_name": full_name,
        "university": data["university"],
        "course": data["course"],
        "group": data["group"],
    }
    kb = admin_menu_kb() if await is_admin(tg_id) else main_menu_kb()
    try:
        await api_post("/panel/users/register-by-telegram", payload)
    except httpx.HTTPStatusError as e:
        err = str(e)
        try:
            err = e.response.json().get("detail", err)
        except Exception:
            pass
        return await msg.answer(
            f"❌ {err}\n\nЕсли «не найден» — сначала нажми /start у бота.",
            reply_markup=kb,
        )
    except Exception as e:
        return await msg.answer(f"❌ Ошибка: {e}", reply_markup=kb)

    await msg.answer(
        "✅ <b>Регистрация сохранена!</b> Можно открыть мини-приложение «Аркадиум» из меню.",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
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
    lines_mk: list[str] = []
    lines_fifa: list[str] = []

    def _at_username(r: dict) -> str:
        u = r.get("username") or r.get("telegram_username") or ""
        u = str(u).strip()
        if not u or u == "—":
            return "—"
        if not u.startswith("@"):
            u = "@" + u
        return u

    for r in rows:
        tg = r.get("telegram_id")
        tun = _at_username(r)
        game = r.get("game") or ""
        nick = (r.get("game_username") or "").strip()

        if game in ("mortal_kombat", "fifa"):
            fn = (r.get("first_name") or "").strip()
            ln = (r.get("last_name") or "").strip()
            name_disp = (fn + " " + ln).strip() or (r.get("full_name") or "").strip() or "—"
            line = f"• {html.escape(tun)} — <b>{html.escape(name_disp)}</b> <code>(tg {tg})</code>"
            if game == "mortal_kombat":
                lines_mk.append(line)
            else:
                lines_fifa.append(line)
            continue

        nick_esc = html.escape(nick) if nick else "—"
        line = f"• id <code>{tg}</code> {html.escape(tun)} — ник <code>{nick_esc}</code>"
        if game == "brawl_stars":
            lines_bs.append(line)
        elif game == "clash_royale":
            lines_cr.append(line)
        else:
            lines_cr.append(line)

    chunks: list[str] = []
    head = "🏆 <b>Регистрации</b>\n\n"
    if lines_bs:
        chunks.append("🟢 <b>Brawl Stars</b>\n" + "\n".join(lines_bs))
    if lines_cr:
        chunks.append("👑 <b>Clash Royale</b>\n" + "\n".join(lines_cr))
    if lines_mk:
        chunks.append("🥊 <b>Mortal Kombat</b>\n" + "\n".join(lines_mk))
    if lines_fifa:
        chunks.append("⚽ <b>FIFA</b>\n" + "\n".join(lines_fifa))
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

    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="🎮 Аркадиум",
            web_app=WebAppInfo(url=MINI_APP_URL),
        ),
    )
    log.info("MenuButtonWebApp set → %s", MINI_APP_URL)

    log.info("Bot started (polling)")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
