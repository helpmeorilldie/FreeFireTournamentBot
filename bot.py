"""
Free Fire Tournament Bot  -  Hosted By Erebus | Owner Haze @Noxmirage
Same UI kit as Erebus Spy Bot (small-caps font, blockquote headers, coloured buttons).
aiogram >= 3.25
"""
import asyncio
import csv
import html
import io
import logging
import os
import re
import shutil
import sqlite3
import tempfile
import time as _time
#Only for tha flask and web if removing web then remove import too and from requirements.txt the module instalation
from flask import Flask, send_from_directory
from threading import Thread

from contextlib import closing, contextmanager
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv
from aiogram import BaseMiddleware, Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatMemberStatus, ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile,
)

try:
    import qrcode  # pip install "qrcode[pil]"
except ImportError:
    qrcode = None
logging.disable(logging.CRITICAL)
#remove this if u want terminal logs
 
#For Render 24/7 host a web page 
app = Flask(__name__)
@app.route("/")
def home():
    return send_from_directory(
        os.path.dirname(os.path.abspath(__file__)),
        "index.html"
    )

@app.route("/health")
def health():
    return "OK", 200

def run():
    app.run(host="0.0.0.0", port=10000)

def keep_alive():
    server = Thread(target=run, daemon=True)
    server.start()
keep_alive()

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
ADMINS = {OWNER_ID} | {int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x}
REQUIRED_CHATS = [c.strip() for c in os.getenv("REQUIRED_CHATS", "@ecochamber").split(",") if c.strip()]
STORAGE_CHANNEL_ID = int(os.getenv("STORAGE_CHANNEL_ID", "0") or 0)   # private channel, bot = admin
UPI_ID = os.getenv("UPI_ID", "Ahmadammar@fam")
UPI_NAME = os.getenv("UPI_NAME", "Erebus Tournament")
DEFAULT_FEE = int(os.getenv("DEFAULT_FEE", "49"))
MIN_LEVEL = 25
DB_PATH = Path(os.getenv("DB_PATH", "data/erebus_ff.sqlite3"))
BACKUP_DIR = Path(os.getenv("BACKUP_DIR", "backups"))
SAVE_DIR = Path(os.getenv("SAVE_DIR", "saved_media"))
BACKUP_EVERY_HOURS = int(os.getenv("BACKUP_EVERY_HOURS", "6"))
DEV_HANDLE = "@Noxmirage"
USE_CUSTOM_EMOJI = os.getenv("USE_CUSTOM_EMOJI", "1") == "1"

if not BOT_TOKEN or not OWNER_ID:
    raise RuntimeError("Set BOT_TOKEN and OWNER_ID in your .env file")

for _d in (DB_PATH.parent, BACKUP_DIR, SAVE_DIR):
    _d.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler("bot.log", encoding="utf-8"), logging.StreamHandler()],
    force=True,
)

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


# ----------------------------------------------------------------------------
# UI kit (same as Erebus Spy Bot): font, emojis, panels, buttons, auto-cleaning
# ----------------------------------------------------------------------------
_SMALL_CAPS = str.maketrans(
    "abcdefghijklmnopqrstuvwxyz",
    "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ",
)


def sc(text):
    """Bot font: 'free plan' -> 'Fʀᴇᴇ Pʟᴀɴ'. First letter of each word is a capital;
    ACRONYMS, numbers, @names and /commands stay untouched."""
    def word(w):
        if any(c.isdigit() or c in "@/₹_<>&" for c in w) or (w.isupper() and len(w) > 1):
            return w
        m = re.search(r"[A-Za-z]", w)
        if not m:
            return w
        i = m.end()
        return w[:i - 1] + w[i - 1].upper() + w[i:].translate(_SMALL_CAPS)
    return "".join(p if p.isspace() else word(p) for p in re.split(r"(\s+)", text))


EMOJI = {
    "title": "✨", "star": "⭐", "camera": "📸", "bolt": "⚡", "user": "👤", "id": "🆔",
    "bot": "👾", "dev": "👨‍💻", "ok": "✅", "err": "❌", "warn": "⚠️", "time": "⏱",
    "pay": "💳", "box": "📦", "money": "💰", "calendar": "📅", "bell": "🔔", "ban": "🚫",
    "admin": "🛠", "mail": "✉️", "link": "🔗", "channel": "📢", "group": "👥",
    "stats": "📊", "lock": "🔒", "ghost": "👻", "home": "🏠", "bank": "🏦",
    "party": "🎉", "pin": "📝", "spin": "🌀",
    # extra names used by the tournament bot
    "new": "🆕", "web": "🌐", "chat": "💬", "trash": "🗑️", "dot": "🔹", "dot2": "🔸",
    "radio": "🔘", "host": "🏛️", "earth": "🌍", "wait": "⏳", "cat": "🐈‍⬛",
    "trophy": "🏆", "game": "🎮", "reply": "↩️", "backup": "💾", "restore": "♻️",
    "csv": "📄", "info": "ℹ️", "plus": "➕", "list": "📋",
}
EMOJI_IDS = {}
if USE_CUSTOM_EMOJI:
    EMOJI_IDS.update({
        # from the Erebus Spy Bot
        "title": "5424972470023104089", "star": "5438496463044752972", "bolt": "5224607267797606837",
        "ok": "5206607081334906820", "err": "5210952531676504517", "time": "5440621591387980068",
        "box": "6046233639644042899", "money": "5278467510604160626", "calendar": "5413879192267805083",
        "bell": "5458603043203327669", "ban": "5260293700088511294", "admin": "5341715473882955310",
        "mail": "5253742260054409879", "link": "5271604874419647061", "channel": "5424818078833715060",
        "group": "5332724926216428039", "stats": "5231200819986047254", "lock": "5296369303661067030",
        "ghost": "5431609822288033666", "bank": "5332455502917949981", "party": "5276032951342088188",
        "pin": "5397782960512444700", "spin": "5375338737028841420",
        # premium emojis for this bot
        "new": "5386367538735104399", "warn": "4915853119839011973", "pay": "5039623284056917259",
        "web": "5039895103947146186", "chat": "5040042498634810056", "trash": "5042329873662609701",
        "dot": "5039753786638205957", "dot2": "5042020176455795565", "radio": "5042097984083330584",
        "host": "5343636681473935403", "earth": "5042176294222037888", "wait": "5039579582764680065",
        "user": "6237927637906364256", "cat": "5039653765439816618",
    })


def E(name):
    fallback = EMOJI.get(name, "•")
    cid = EMOJI_IDS.get(name)
    return f'<tg-emoji emoji-id="{cid}">{fallback}</tg-emoji>' if cid else fallback


_BTN_FIELDS = InlineKeyboardButton.model_fields
HAS_ICON = "icon_custom_emoji_id" in _BTN_FIELDS   # needs aiogram >= 3.25
HAS_STYLE = "style" in _BTN_FIELDS


def btn(text, emoji=None, style=None, **kw):
    """Inline button in the bot font with an icon.
    style: 'primary' (blue) / 'success' (green) / 'danger' (red)."""
    label = sc(text)
    extra = {}
    cid = EMOJI_IDS.get(emoji) if emoji else None
    if cid and HAS_ICON:
        extra["icon_custom_emoji_id"] = cid
    elif emoji:
        label = f"{EMOJI.get(emoji, '')} {label}"
    if style and HAS_STYLE:
        extra["style"] = style
    return InlineKeyboardButton(text=label, **extra, **kw)


SEP = "──────────────────"


def bq(text):
    return f"<blockquote>{text}</blockquote>"


def head(emoji, title, tail=""):
    return f"{E(emoji)} <b>{sc(title)}</b>{tail}"


def row(emoji, label, value):
    return f"{E(emoji)} <b>{sc(label)}</b> ➛ {value}"


def esc(value):
    return html.escape(str(value if value is not None else ""))


_TRASH = {}     # chat_id -> ids of temporary messages (prompts, QR pictures ...)
_PANEL = {}     # chat_id -> id of the current main-menu message
_TASKS = set()  # keeps background tasks alive


async def _delete(chat_id, message_id):
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass


def remember(message):
    if message:
        _TRASH.setdefault(message.chat.id, []).append(message.message_id)
    return message


async def sweep(chat_id, keep=None):
    for mid in _TRASH.pop(chat_id, []):
        if mid != keep:
            await _delete(chat_id, mid)


async def tidy(message):
    await _delete(message.chat.id, message.message_id)


async def _delete_later(chat_id, message_id, ttl):
    await asyncio.sleep(ttl)
    await _delete(chat_id, message_id)


def spawn(coro):
    task = asyncio.create_task(coro)
    _TASKS.add(task)
    task.add_done_callback(_TASKS.discard)
    return task


async def notice(chat_id, text, ttl=8, **kw):
    try:
        msg = await bot.send_message(chat_id, text, **kw)
    except Exception:
        logging.exception("notice to %s failed", chat_id)
        return None
    spawn(_delete_later(chat_id, msg.message_id, ttl))
    return msg


async def ask(chat_id, text):
    """Send a prompt that sweep() removes when the step is done."""
    return remember(await bot.send_message(chat_id, text))


async def show_panel(chat_id, text, markup):
    old = _PANEL.pop(chat_id, None)
    if old:
        await _delete(chat_id, old)
    msg = await bot.send_message(chat_id, text, reply_markup=markup)
    _PANEL[chat_id] = msg.message_id
    return msg


async def safe_edit(callback: CallbackQuery, text, reply_markup=None, parse_mode="HTML"):
    msg = callback.message
    if getattr(msg, "photo", None):
        await _delete(msg.chat.id, msg.message_id)
        sent = await bot.send_message(msg.chat.id, text, reply_markup=reply_markup, parse_mode=parse_mode)
        _PANEL[msg.chat.id] = sent.message_id
        return
    try:
        await msg.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise


# ----------------------------------------------------------------------------
# Database
# ----------------------------------------------------------------------------
@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def q_all(sql, args=()):
    with db() as con:
        return con.execute(sql, args).fetchall()


def q_one(sql, args=()):
    with db() as con:
        return con.execute(sql, args).fetchone()


def run(sql, args=()):
    with db() as con:
        return con.execute(sql, args).lastrowid


def count(sql, args=()):
    return q_one(sql, args)[0]


def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
            joined_at TEXT NOT NULL, last_seen TEXT NOT NULL, banned INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS tournaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, mode TEXT, start_time TEXT,
            fee INTEGER NOT NULL, prize TEXT, slots INTEGER NOT NULL, rules TEXT,
            status TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, tournament_id INTEGER NOT NULL,
            team_name TEXT NOT NULL, uids TEXT NOT NULL, screenshot_file_id TEXT,
            status TEXT NOT NULL DEFAULT 'pending',   -- pending / query / approved / rejected
            reason TEXT, created_at TEXT NOT NULL, reviewed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS thread (
            id INTEGER PRIMARY KEY AUTOINCREMENT, reg_id INTEGER NOT NULL, sender TEXT NOT NULL,
            body TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT, body TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS broadcasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, admin_id INTEGER NOT NULL, kind TEXT,
            sent_count INTEGER NOT NULL, failed_count INTEGER NOT NULL, created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_reg_user ON registrations(user_id, status);
        CREATE INDEX IF NOT EXISTS idx_reg_tour ON registrations(tournament_id, status);
        """)


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def is_admin(uid):
    return uid in ADMINS


def upsert_user(user):
    stamp = now_iso()
    run("""INSERT INTO users(user_id, username, first_name, joined_at, last_seen) VALUES(?,?,?,?,?)
           ON CONFLICT(user_id) DO UPDATE SET username=excluded.username,
           first_name=excluded.first_name, last_seen=excluded.last_seen""",
        (user.id, user.username, user.first_name, stamp, stamp))


def is_banned(uid):
    r = q_one("SELECT banned FROM users WHERE user_id=?", (uid,))
    return bool(r and r["banned"])


def get_tour(tid):
    return q_one("SELECT * FROM tournaments WHERE id=?", (tid,))


def get_reg(rid):
    return q_one("SELECT * FROM registrations WHERE id=?", (rid,))


def get_user(uid):
    return q_one("SELECT * FROM users WHERE user_id=?", (uid,))


def used_slots(tid):
    return count("SELECT COUNT(*) FROM registrations WHERE tournament_id=? AND status!='rejected'", (tid,))


def log_thread(rid, sender, body):
    run("INSERT INTO thread(reg_id, sender, body, created_at) VALUES(?,?,?,?)", (rid, sender, body, now_iso()))


STATUS_LABEL = {"pending": "Pending", "query": "Awaiting Team Reply", "approved": "Approved", "rejected": "Rejected"}
STATUS_ICON = {"pending": "⏳", "query": "💬", "approved": "✅", "rejected": "❌"}


# ----------------------------------------------------------------------------
# Storage channel, backups
# ----------------------------------------------------------------------------
async def log_channel(text=None, photo=None, document=None):
    if not STORAGE_CHANNEL_ID:
        return
    try:
        if photo:
            await bot.send_photo(STORAGE_CHANNEL_ID, photo, caption=text)
        elif document:
            await bot.send_document(STORAGE_CHANNEL_ID, document, caption=text)
        else:
            await bot.send_message(STORAGE_CHANNEL_ID, text)
    except Exception:
        logging.exception("storage channel send failed")


async def archive_copy(message: Message):
    """Copy any message (media included) into the private storage channel."""
    if not STORAGE_CHANNEL_ID:
        return
    try:
        await bot.copy_message(STORAGE_CHANNEL_ID, message.chat.id, message.message_id)
    except Exception:
        logging.exception("archive copy failed")


async def backup_now(reason="manual"):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = BACKUP_DIR / f"erebus_ff_{stamp}.db"

    def _copy():
        with closing(sqlite3.connect(DB_PATH)) as src, closing(sqlite3.connect(path)) as dst:
            src.backup(dst)
    await asyncio.to_thread(_copy)
    for old in sorted(BACKUP_DIR.glob("erebus_ff_*.db"))[:-20]:
        old.unlink(missing_ok=True)
    caption = f"{E('backup')} <b>{sc('Database backup')}</b> ({esc(reason)})\n{stamp}"
    await log_channel(caption, document=BufferedInputFile(path.read_bytes(), filename=path.name))
    return path


async def backup_loop():
    while True:
        await asyncio.sleep(BACKUP_EVERY_HOURS * 3600)
        try:
            await backup_now("auto")
        except Exception:
            logging.exception("auto backup failed")


# ----------------------------------------------------------------------------
# Keyboards
# ----------------------------------------------------------------------------
def home_keyboard(admin=False):
    rows = [
        [btn("Tournaments", "trophy", style="primary", callback_data="tournaments")],
        [btn("My Registrations", "box", callback_data="myregs"),
         btn("Updates", "bell", callback_data="updates")],
        [btn("How To Register", "pin", callback_data="howto"),
         btn("Rules", "lock", callback_data="rules")],
        [btn("Developer & Host", "dev", callback_data="about")],
    ]
    if admin:
        rows.append([btn("Admin Panel", "admin", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_keyboard(*top_rows):
    return InlineKeyboardMarkup(inline_keyboard=[*top_rows, [btn("Main Menu", "home", callback_data="home")]])


def join_keyboard():
    rows = [[btn(f"Join {c}", "channel", url=f"https://t.me/{c.lstrip('@')}")] for c in REQUIRED_CHATS]
    rows.append([btn("I've Joined", "ok", style="success", callback_data="checkjoin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("Pending", "wait", style="primary", callback_data="alist:pending"),
         btn("All Registrations", "list", callback_data="alist:all")],
        [btn("Add Tournament", "plus", style="success", callback_data="aaddt"),
         btn("Manage Tournaments", "trophy", callback_data="atours")],
        [btn("Set Prize", "star", callback_data="aprize"),
         btn("Post Update", "bell", callback_data="aupd")],
        [btn("Broadcast", "channel", callback_data="abc"),
         btn("Message A Team", "mail", callback_data="amsg")],
        [btn("Statistics", "stats", callback_data="astats"),
         btn("Users", "user", callback_data="ausers")],
        [btn("Export CSV", "csv", callback_data="acsv"),
         btn("Backup Now", "backup", callback_data="abackup")],
        [btn("Restore Backup", "restore", style="danger", callback_data="arestore")],
        [btn("Main Menu", "home", callback_data="home")],
    ])


def admin_back(*top_rows):
    return InlineKeyboardMarkup(inline_keyboard=[*top_rows, [btn("Admin Panel", "admin", callback_data="admin")]])


def team_reply_kb(rid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("Reply To Admin", "reply", style="primary", callback_data=f"treply:{rid}")]])


def admin_reply_kb(rid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("Reply To Team", "mail", style="primary", callback_data=f"rmsg:{rid}")],
        [btn("Open Registration", "box", callback_data=f"areg:{rid}")]])


def reg_admin_kb(rid, status):
    rows = []
    if status in ("pending", "query"):
        rows.append([btn("Approve", "ok", style="success", callback_data=f"rok:{rid}"),
                     btn("Reject", "err", style="danger", callback_data=f"rno:{rid}")])
    rows.append([btn("Message Team", "mail", style="primary", callback_data=f"rmsg:{rid}")])
    rows.append([btn("Back", "list", callback_data="alist:pending")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ----------------------------------------------------------------------------
# Screens (text)
# ----------------------------------------------------------------------------
def home_text(name):
    open_n = count("SELECT COUNT(*) FROM tournaments WHERE status='open'")
    return "\n".join([
        bq(f"{E('user')} {sc('Welcome')}, {esc(name or 'friend')}"),
        head("title", "Free Fire Tournaments", " ❗️"),
        "",
        row("trophy", "Open Tournaments", open_n),
        row("pay", "Entry Fee", f"₹51 {sc('per team')}"),
        row("warn", "Min Level", MIN_LEVEL),
        SEP,
        f"{E('bolt')} {sc('Tap Tournaments to register your team.')}",
    ])


def howto_text():
    return "\n".join([
        bq(f"{E('pin')} {sc('How to register')}"),
        "",
        row("dot", "Step 1", sc("Open Tournaments and pick one")),
        row("dot", "Step 2", sc("Tap Register & Pay")),
        row("dot", "Step 3", sc("Send your team name")),
        row("dot", "Step 4", sc("Send 4 player UIDs, one per line")),
        row("dot", "Step 5", f"{sc('Confirm every player is Level')} {MIN_LEVEL}+"),
        row("pay", "Step 6", sc("Scan the QR and pay the entry fee")),
        row("camera", "Step 7", sc("Send the payment screenshot")),
        row("wait", "Step 8", sc("Wait for admin approval")),
        SEP,
        f"{E('bell')} {sc('You get a message here when you are approved or rejected.')}",
        f"{E('mail')} {sc('If admin finds a problem he will message you here. Just tap Reply.')}",
    ])


def rules_text():
    return "\n".join([
        bq(f"{E('lock')} {sc('Rules & info')}"),
        "",
        row("dot2", "Team", sc("4 players unless stated otherwise")),
        row("dot2", "Level", f"{sc('Every player must be Level')} {MIN_LEVEL}+"),
        row("dot2", "UIDs", sc("Use your real in-game UIDs only")),
        row("dot2", "Fair Play", sc("No hacks, panels or teaming")),
        row("dot2", "Timing", sc("Join the room on time")),
        row("dot2", "Fee", f"₹{DEFAULT_FEE} {sc('per team, non refundable after approval')}"),
        row("dot2", "Room", sc("Room ID and password are sent here before the match")),
        row("dot2", "Decision", sc("Admin decision is final")),
        SEP,
        f"{E('trophy')} {sc('Prizes are announced with each tournament.')}",
    ])


def about_text():
    return "\n".join([
        bq(f"{E('host')} {sc('Developer & host')}"),
        "",
        row("dev", "Developer", f"Haze {DEV_HANDLE}"),
        row("host", "Hosted By", sc("Erebus")),
        row("group", "Community", " ".join(REQUIRED_CHATS)),
        SEP,
        f"{E('mail')} {sc('Need help? Message the developer.')}",
    ])


def about_keyboard():
    rows = [[btn("Developer", "dev", url=f"https://t.me/{DEV_HANDLE.lstrip('@')}")]]
    for c in REQUIRED_CHATS:
        rows.append([btn(f"Community {c}", "group", url=f"https://t.me/{c.lstrip('@')}")])
    return back_keyboard(*rows)


def join_text(first_visit=True):
    title = "Join To Unlock" if first_visit else "Not Joined Yet"
    return "\n".join([
        bq(f"{E('lock')} {sc('Access locked')}"),
        head("channel", title, " ❗️"),
        "",
        sc(f"Join {', '.join(REQUIRED_CHATS)} then tap I've Joined."),
    ])


def tour_text(t):
    lines = [
        bq(f"{E('trophy')} {sc('Tournament')} #{t['id']}"),
        f"{E('title')} <b>{esc(t['title'])}</b>",
        "",
        row("game", "Mode", esc(t["mode"])),
        row("calendar", "Starts", esc(t["start_time"])),
        row("pay", "Entry Fee", f"₹{t['fee']} {sc('per team')}"),
        row("star", "Prize", esc(t["prize"]) if t["prize"] else sc("To be announced")),
        row("group", "Slots", f"{used_slots(t['id'])} / {t['slots']}"),
        row("warn", "Min Level", MIN_LEVEL),
    ]
    if t["rules"]:
        lines.append(row("pin", "Notes", esc(t["rules"])))
    lines.append(row("time", "Status", sc("Open" if t["status"] == "open" else "Closed")))
    return "\n".join(lines)


def uid_lines(uids):
    return "\n".join(f"{E('dot')} {i + 1}. <code>{esc(x)}</code>" for i, x in enumerate(uids.split(",")))


def reg_caption(r):
    t = get_tour(r["tournament_id"])
    u = get_user(r["user_id"])
    handle = f"@{u['username']}" if u and u["username"] else "no username"
    lines = [
        bq(f"{E('pay')} {sc('Registration')} #{r['id']}"),
        "",
        row("trophy", "Tournament", esc(t["title"] if t else "?")),
        row("group", "Team", esc(r["team_name"])),
        row("user", "User", f"{esc(u['first_name'] if u else '')} ({esc(handle)})"),
        row("id", "ID", f"<code>{r['user_id']}</code>"),
        row("money", "Fee", f"₹{t['fee'] if t else '?'}"),
        uid_lines(r["uids"]),
        SEP,
        row("time", "Status", sc(STATUS_LABEL.get(r["status"], r["status"]))),
    ]
    if r["reason"]:
        lines.append(row("warn", "Note", esc(r["reason"])))
    return "\n".join(lines)


def myreg_text(r):
    t = get_tour(r["tournament_id"])
    lines = [
        bq(f"{E('box')} {sc('Registration')} #{r['id']}"),
        "",
        row("trophy", "Tournament", esc(t["title"] if t else "?")),
        row("group", "Team", esc(r["team_name"])),
        uid_lines(r["uids"]),
        SEP,
        row("time", "Status", sc(STATUS_LABEL.get(r["status"], r["status"]))),
    ]
    if r["reason"]:
        lines.append(row("warn", "Note", esc(r["reason"])))
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# UPI QR (same style as the Erebus premium payments)
# ----------------------------------------------------------------------------
def upi_link(price, note):
    return f"upi://pay?pa={UPI_ID}&pn={quote(UPI_NAME)}&am={price}&cu=INR&tn={quote(note)}"


def make_qr(data):
    if qrcode is None:
        logging.warning('qrcode library missing: pip install "qrcode[pil]"')
        return None
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    buf = BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buf)
    return BufferedInputFile(buf.getvalue(), filename="upi_qr.png")


# ----------------------------------------------------------------------------
# States
# ----------------------------------------------------------------------------
class RegFlow(StatesGroup):
    team = State()
    uids = State()
    level = State()
    screenshot = State()


class ReplyFlow(StatesGroup):
    text = State()


class AddT(StatesGroup):
    title = State()
    mode = State()
    time = State()
    fee = State()
    slots = State()
    prize = State()
    rules = State()


class AdminFlow(StatesGroup):
    broadcast = State()
    dm_target = State()
    dm_text = State()
    reject_reason = State()
    prize = State()
    update = State()
    restore = State()


async def admin_only(callback: CallbackQuery):
    if callback.from_user.id not in ADMINS:
        await callback.answer("Not allowed.", show_alert=True)
        return False
    return True


# ----------------------------------------------------------------------------
# Membership gate + private-chat-only middleware
# ----------------------------------------------------------------------------
_JOINED = {}


async def membership_ok(user_id):
    ts = _JOINED.get(user_id)
    if ts and _time.time() - ts < 120:
        return True
    for chat in REQUIRED_CHATS:
        try:
            member = await bot.get_chat_member(chat_id=chat, user_id=user_id)
            if member.status in (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED):
                return False
        except Exception:
            logging.exception("Membership check failed for %s", chat)
            return False
    _JOINED[user_id] = _time.time()
    return True


class Gate(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = event.from_user
        chat = event.chat if isinstance(event, Message) else (event.message.chat if event.message else None)
        if user is None or chat is None or chat.type != "private":
            return None                       # the bot only works in private chats
        upsert_user(user)
        if user.id in ADMINS:
            return await handler(event, data)
        if is_banned(user.id):
            if isinstance(event, CallbackQuery):
                await event.answer("Access disabled.", show_alert=True)
            else:
                await notice(chat.id, f"{E('ban')} {sc('Your access has been disabled.')}", ttl=10)
            return None
        if isinstance(event, CallbackQuery) and event.data == "checkjoin":
            return await handler(event, data)
        if await membership_ok(user.id):
            return await handler(event, data)
        if isinstance(event, CallbackQuery):
            await safe_edit(event, join_text(), join_keyboard())
            await event.answer()
        else:
            await tidy(event)
            await sweep(chat.id)
            await show_panel(chat.id, join_text(), join_keyboard())
        return None


dp.message.outer_middleware(Gate())
dp.callback_query.outer_middleware(Gate())


# ----------------------------------------------------------------------------
# Commands (registered first so they win over state handlers)
# ----------------------------------------------------------------------------
async def go_home(chat, user):
    await show_panel(chat, home_text(user.first_name), home_keyboard(is_admin(user.id)))


@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await tidy(message)
    await sweep(message.chat.id)
    await go_home(message.chat.id, message.from_user)


@dp.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await tidy(message)
    await sweep(message.chat.id)
    await notice(message.chat.id, f"{E('err')} {sc('Cancelled.')}", ttl=5)
    await go_home(message.chat.id, message.from_user)


@dp.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await tidy(message)
    await sweep(message.chat.id)
    await show_panel(message.chat.id, admin_text(), admin_keyboard())


@dp.message(Command("addtournament"))
async def cmd_addt(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await tidy(message)
    await begin_add_tournament(message.chat.id, state)


@dp.message(Command("backup"))
async def cmd_backup(message: Message):
    if not is_admin(message.from_user.id):
        return
    await tidy(message)
    path = await backup_now("manual")
    await bot.send_document(message.chat.id, BufferedInputFile(path.read_bytes(), filename=path.name),
                            caption=f"{E('backup')} {sc('Backup saved on host')}: <code>{esc(path)}</code>")


@dp.message(Command("restore"))
async def cmd_restore(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await tidy(message)
    await state.set_state(AdminFlow.restore)
    await ask(message.chat.id, f"{E('restore')} {sc('Send the .db backup file to restore.')}\n{sc('Send /cancel to stop.')}")


@dp.message(Command("export"))
async def cmd_export(message: Message):
    if not is_admin(message.from_user.id):
        return
    await tidy(message)
    await bot.send_document(message.chat.id, make_csv(), caption=f"{E('csv')} {sc('Registrations export')}")


@dp.message(Command("ban"))
@dp.message(Command("unban"))
async def cmd_ban(message: Message):
    if not is_admin(message.from_user.id):
        return
    await tidy(message)
    parts = (message.text or "").split()
    ban = parts[0].lstrip("/").split("@")[0].lower() == "ban"
    if len(parts) != 2:
        return await notice(message.chat.id, "Usage: <code>/ban @username</code> or <code>/ban 123456</code>", ttl=10)
    tok = parts[1]
    if tok.isdigit():
        u = get_user(int(tok))
    else:
        u = q_one("SELECT * FROM users WHERE lower(username)=?", (tok.lstrip("@").lower(),))
    if not u:
        return await notice(message.chat.id, f"{E('warn')} {sc('User not found. They must have started the bot.')}")
    run("UPDATE users SET banned=? WHERE user_id=?", (1 if ban else 0, u["user_id"]))
    await notice(message.chat.id, f"{E('ok')} {sc('Banned' if ban else 'Unbanned')} <code>{u['user_id']}</code>", ttl=8)


# ----------------------------------------------------------------------------
# User: menus
# ----------------------------------------------------------------------------
@dp.callback_query(F.data == "checkjoin")
async def check_join(callback: CallbackQuery):
    _JOINED.pop(callback.from_user.id, None)
    if await membership_ok(callback.from_user.id):
        await safe_edit(callback, home_text(callback.from_user.first_name), home_keyboard(is_admin(callback.from_user.id)))
        await callback.answer("Verified!")
    else:
        await callback.answer("You must join first.", show_alert=True)


@dp.callback_query(F.data == "home")
async def home(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await sweep(callback.message.chat.id, keep=callback.message.message_id)
    await safe_edit(callback, home_text(callback.from_user.first_name), home_keyboard(is_admin(callback.from_user.id)))
    await callback.answer()


@dp.callback_query(F.data == "howto")
async def howto(callback: CallbackQuery):
    await safe_edit(callback, howto_text(), back_keyboard())
    await callback.answer()


@dp.callback_query(F.data == "rules")
async def rules(callback: CallbackQuery):
    await safe_edit(callback, rules_text(), back_keyboard())
    await callback.answer()


@dp.callback_query(F.data == "about")
async def about(callback: CallbackQuery):
    await safe_edit(callback, about_text(), about_keyboard())
    await callback.answer()


@dp.callback_query(F.data == "updates")
async def updates(callback: CallbackQuery):
    ups = q_all("SELECT * FROM updates ORDER BY id DESC LIMIT 6")
    lines = [bq(f"{E('bell')} {sc('Latest updates')}"), ""]
    if ups:
        for u in ups:
            lines.append(f"{E('dot2')} {esc(u['body'])}  <i>({u['created_at'][:10]})</i>")
    else:
        lines.append(sc("No updates yet."))
    await safe_edit(callback, "\n".join(lines),
                    back_keyboard([btn("Tournaments", "trophy", style="primary", callback_data="tournaments")]))
    await callback.answer()


# ----------------------------------------------------------------------------
# User: tournaments page
# ----------------------------------------------------------------------------
@dp.callback_query(F.data == "tournaments")
async def tournaments(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await sweep(callback.message.chat.id, keep=callback.message.message_id)
    rows = q_all("SELECT * FROM tournaments WHERE status='open' ORDER BY id DESC LIMIT 10")
    lines = [bq(f"{E('trophy')} {sc('Tournaments')}"), ""]
    kb = []
    if rows:
        for t in rows:
            lines.append(f"{E('dot')} <b>{esc(t['title'])}</b> ➛ ₹{t['fee']} | {used_slots(t['id'])}/{t['slots']}")
            kb.append([btn(f"{t['title']} — ₹{t['fee']}", "trophy", style="primary", callback_data=f"t:{t['id']}")])
        lines += [SEP, f"{E('bolt')} {sc('Tap a tournament to see details and register.')}"]
    else:
        lines.append(sc("No tournaments are open right now. Check Updates later."))
    await safe_edit(callback, "\n".join(lines), back_keyboard(*kb))
    await callback.answer()


@dp.callback_query(F.data.startswith("t:"))
async def tournament_detail(callback: CallbackQuery):
    t = get_tour(int(callback.data.split(":")[1]))
    if not t:
        return await callback.answer("Tournament not found.", show_alert=True)
    kb = []
    text = tour_text(t)
    full = used_slots(t["id"]) >= t["slots"]
    if t["status"] == "open" and not full:
        kb.append([btn("Register & Pay", "pay", style="success", callback_data=f"reg:{t['id']}")])
    else:
        text += f"\n{E('warn')} {sc('Registration is closed.' if t['status'] != 'open' else 'All slots are full.')}"
    kb.append([btn("All Tournaments", "trophy", callback_data="tournaments")])
    await safe_edit(callback, text, back_keyboard(*kb))
    await callback.answer()


# ----------------------------------------------------------------------------
# User: registration + payment
# ----------------------------------------------------------------------------
@dp.callback_query(F.data.startswith("reg:"))
async def reg_start(callback: CallbackQuery, state: FSMContext):
    tid = int(callback.data.split(":")[1])
    t = get_tour(tid)
    uid = callback.from_user.id
    if not t or t["status"] != "open":
        return await callback.answer("Registration is closed.", show_alert=True)
    if used_slots(tid) >= t["slots"]:
        return await callback.answer("All slots are full.", show_alert=True)
    if count("SELECT COUNT(*) FROM registrations WHERE user_id=? AND tournament_id=? "
             "AND status IN ('pending','query','approved')", (uid, tid)):
        return await callback.answer("You already registered for this tournament.", show_alert=True)
    await state.clear()
    await sweep(callback.message.chat.id, keep=callback.message.message_id)
    await state.set_state(RegFlow.team)
    await state.update_data(tid=tid)
    await ask(callback.message.chat.id,
              f"{E('pin')} {sc('Send your team name (max 30 characters).')}\n{sc('Send /cancel to stop.')}")
    await callback.answer()


@dp.message(RegFlow.team)
async def reg_team(message: Message, state: FSMContext):
    chat = message.chat.id
    await tidy(message)
    name = (message.text or "").strip()
    if not name or len(name) > 30:
        return await notice(chat, f"{E('warn')} {sc('Send a valid team name (max 30 characters).')}", ttl=6)
    await sweep(chat)
    await state.update_data(team=name)
    await state.set_state(RegFlow.uids)
    await ask(chat, f"{E('pin')} {sc('Send the 4 player UIDs, one per line (leader first).')}")


@dp.message(RegFlow.uids)
async def reg_uids(message: Message, state: FSMContext):
    chat = message.chat.id
    await tidy(message)
    uids = [x.strip() for x in re.split(r"[\n,]+", message.text or "") if x.strip()]
    if len(uids) != 4 or len(set(uids)) != 4 or not all(re.fullmatch(r"\d{6,14}", x) for x in uids):
        return await notice(chat, f"{E('warn')} {sc('Send exactly 4 different numeric UIDs, one per line.')}", ttl=7)
    await sweep(chat)
    await state.update_data(uids=",".join(uids))
    await state.set_state(RegFlow.level)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [btn(f"All Players Are Level {MIN_LEVEL}+", "ok", style="success", callback_data="lvl:ok")],
        [btn("Cancel", "err", style="danger", callback_data="home")]])
    remember(await bot.send_message(
        chat, "\n".join([bq(f"{E('warn')} {sc('Level check')}"), "",
                         f"{sc('Every player must be Level')} <b>{MIN_LEVEL}+</b>.",
                         sc("Wrong info means disqualification.")]), reply_markup=kb))


@dp.callback_query(RegFlow.level, F.data == "lvl:ok")
async def reg_level(callback: CallbackQuery, state: FSMContext):
    chat = callback.message.chat.id
    data = await state.get_data()
    t = get_tour(data["tid"])
    await sweep(chat)
    await state.set_state(RegFlow.screenshot)
    caption = "\n".join([
        bq(f"{E('pay')} {sc('Pay')} ₹{t['fee']} ➛ {esc(t['title'])}"),
        "",
        row("bank", "UPI ID", f"<code>{esc(UPI_ID)}</code>"),
        row("money", "Amount", f"₹{t['fee']}"),
        SEP,
        f"1️⃣ {sc('Scan this QR with any UPI app')}",
        f"2️⃣ {sc('Pay the exact amount')}",
        f"3️⃣ {sc('Send the payment screenshot here as a photo')}",
        "",
        sc("Send /cancel to stop."),
    ])
    qr = make_qr(upi_link(t["fee"], f"FF Tournament {t['id']}"))
    if qr:
        remember(await bot.send_photo(chat, qr, caption=caption))
    else:
        remember(await bot.send_message(
            chat, caption + f"\n\n{E('warn')} {sc('QR is unavailable, please pay to the UPI ID above.')}"))
    await callback.answer()


@dp.message(RegFlow.screenshot, F.photo)
async def reg_screenshot(message: Message, state: FSMContext):
    chat = message.chat.id
    data = await state.get_data()
    t = get_tour(data["tid"])
    if not t or t["status"] != "open" or used_slots(t["id"]) >= t["slots"]:
        await state.clear()
        await sweep(chat)
        return await notice(chat, f"{E('warn')} {sc('Sorry, this tournament just closed or filled up.')}", ttl=10)
    user = message.from_user
    file_id = message.photo[-1].file_id
    rid = run("INSERT INTO registrations(user_id, tournament_id, team_name, uids, screenshot_file_id, status, created_at) "
              "VALUES (?,?,?,?,?, 'pending', ?)",
              (user.id, t["id"], data["team"], data["uids"], file_id, now_iso()))
    await state.clear()
    try:   # keep a copy of the payment screenshot on the host
        await bot.download(message.photo[-1], destination=SAVE_DIR / f"reg_{rid}.jpg")
    except Exception:
        logging.exception("could not save screenshot for #%s", rid)

    r = get_reg(rid)
    caption = reg_caption(r)
    forwarded = False
    for admin in ADMINS:
        try:
            await bot.send_photo(admin, file_id, caption=caption, reply_markup=reg_admin_kb(rid, "pending"))
            forwarded = True
        except Exception:
            logging.exception("could not notify admin %s", admin)
    await log_channel(caption, photo=file_id)

    await sweep(chat)
    if forwarded:
        await tidy(message)
    await bot.send_message(chat, "\n".join([
        bq(f"{E('ok')} {sc('Screenshot received')}"),
        "",
        row("pin", "Registration", f"#{rid}"),
        row("wait", "Status", sc("Waiting for approval")),
        SEP,
        f"{E('bell')} {sc('You will get a message here as soon as admin reviews it.')}",
    ]), reply_markup=back_keyboard())


@dp.message(RegFlow.screenshot)
async def reg_need_photo(message: Message):
    await tidy(message)
    await notice(message.chat.id, f"{E('warn')} {sc('Please send the screenshot as a photo, or /cancel to stop.')}", ttl=6)


# ---- my registrations -------------------------------------------------------
@dp.callback_query(F.data == "myregs")
async def my_regs(callback: CallbackQuery):
    rows = q_all("SELECT r.*, t.title FROM registrations r LEFT JOIN tournaments t ON t.id=r.tournament_id "
                 "WHERE r.user_id=? ORDER BY r.id DESC LIMIT 10", (callback.from_user.id,))
    lines = [bq(f"{E('box')} {sc('My registrations')}"), ""]
    kb = []
    if not rows:
        lines.append(sc("You have no registrations yet."))
    for r in rows:
        lines.append(f"{STATUS_ICON[r['status']]} <b>#{r['id']}</b> {esc(r['team_name'])} ➛ {sc(STATUS_LABEL[r['status']])}")
        kb.append([btn(f"#{r['id']} {r['team_name'][:20]}", "box", callback_data=f"myreg:{r['id']}")])
    await safe_edit(callback, "\n".join(lines), back_keyboard(*kb))
    await callback.answer()


@dp.callback_query(F.data.startswith("myreg:"))
async def my_reg_detail(callback: CallbackQuery):
    r = get_reg(int(callback.data.split(":")[1]))
    if not r or r["user_id"] != callback.from_user.id:
        return await callback.answer("Not found.", show_alert=True)
    await safe_edit(callback, myreg_text(r), back_keyboard(
        [btn("Message Admin", "mail", style="primary", callback_data=f"treply:{r['id']}")],
        [btn("My Registrations", "box", callback_data="myregs")]))
    await callback.answer()


# ----------------------------------------------------------------------------
# Two-way messages: admin <-> team
# ----------------------------------------------------------------------------
async def relay(src: Message, chat_id, header, kb=None):
    """Deliver any kind of message (text, photo, file ...) with a header and a button."""
    try:
        if src.text:
            await bot.send_message(chat_id, f"{header}\n\n{esc(src.text)}", reply_markup=kb)
        else:
            await bot.send_message(chat_id, header)
            await bot.copy_message(chat_id, src.chat.id, src.message_id, reply_markup=kb)
        return True
    except Exception:
        logging.exception("relay to %s failed", chat_id)
        return False


def body_of(message: Message):
    return message.text or message.caption or f"[{message.content_type}]"


@dp.callback_query(F.data.startswith("rmsg:"))
async def admin_msg_team(callback: CallbackQuery, state: FSMContext):
    if not await admin_only(callback):
        return
    r = get_reg(int(callback.data.split(":")[1]))
    if not r:
        return await callback.answer("Not found.", show_alert=True)
    await state.clear()
    await state.set_state(AdminFlow.dm_text)
    await state.update_data(rid=r["id"])
    await ask(callback.message.chat.id,
              f"{E('mail')} {sc('Send your message for team')} <b>{esc(r['team_name'])}</b> (#{r['id']}).\n"
              f"{sc('Text, photo or any file works. They can reply to you.')}\n{sc('Send /cancel to stop.')}")
    await callback.answer()


@dp.callback_query(F.data == "amsg")
async def admin_msg_prompt(callback: CallbackQuery, state: FSMContext):
    if not await admin_only(callback):
        return
    await state.clear()
    await state.set_state(AdminFlow.dm_target)
    await ask(callback.message.chat.id,
              f"{E('mail')} {sc('Send the registration number (example 12) of the team.')}\n{sc('Send /cancel to stop.')}")
    await callback.answer()


@dp.message(AdminFlow.dm_target)
async def admin_msg_target(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    chat = message.chat.id
    await tidy(message)
    txt = (message.text or "").strip().lstrip("#")
    r = get_reg(int(txt)) if txt.isdigit() else None
    if not r:
        return await notice(chat, f"{E('warn')} {sc('Registration not found. Try again or /cancel.')}", ttl=6)
    await sweep(chat)
    await state.set_state(AdminFlow.dm_text)
    await state.update_data(rid=r["id"])
    await ask(chat, f"{E('pin')} {sc('Now send the message for team')} <b>{esc(r['team_name'])}</b>.")


@dp.message(AdminFlow.dm_text)
async def admin_msg_send(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    chat = message.chat.id
    rid = (await state.get_data())["rid"]
    r = get_reg(rid)
    header = "\n".join([
        bq(f"{E('mail')} {sc('Message from admin')}"),
        row("pin", "Registration", f"#{rid} · {esc(r['team_name'])}"),
    ])
    ok = await relay(message, r["user_id"], header, team_reply_kb(rid))
    await state.clear()
    await sweep(chat)
    if ok:
        run("UPDATE registrations SET status='query' WHERE id=? AND status='pending'", (rid,))
        log_thread(rid, "admin", body_of(message))
        await log_channel(f"{E('mail')} Admin ➛ team #{rid}")
        await archive_copy(message)
    await tidy(message)
    await notice(chat, f"{E('ok')} {sc('Delivered to team')} #{rid}" if ok
                 else f"{E('err')} {sc('Could not deliver (user may have blocked the bot).')}", ttl=8)


@dp.callback_query(F.data.startswith("treply:"))
async def team_reply_start(callback: CallbackQuery, state: FSMContext):
    r = get_reg(int(callback.data.split(":")[1]))
    if not r or r["user_id"] != callback.from_user.id:
        return await callback.answer("Not found.", show_alert=True)
    await state.clear()
    await state.set_state(ReplyFlow.text)
    await state.update_data(rid=r["id"])
    await ask(callback.message.chat.id,
              f"{E('reply')} {sc('Send your message for admin about registration')} #{r['id']}.\n"
              f"{sc('Text or photo works.')}\n{sc('Send /cancel to stop.')}")
    await callback.answer()


@dp.message(ReplyFlow.text)
async def team_reply_send(message: Message, state: FSMContext):
    chat = message.chat.id
    rid = (await state.get_data())["rid"]
    r = get_reg(rid)
    u = message.from_user
    handle = f"@{u.username}" if u.username else "no username"
    header = "\n".join([
        bq(f"{E('mail')} {sc('Reply from team')}"),
        row("pin", "Registration", f"#{rid} · {esc(r['team_name'])}"),
        row("user", "User", f"{esc(u.full_name)} ({esc(handle)})"),
    ])
    delivered = False
    for admin in ADMINS:
        delivered = await relay(message, admin, header, admin_reply_kb(rid)) or delivered
    await state.clear()
    await sweep(chat)
    if delivered:
        run("UPDATE registrations SET status='pending' WHERE id=? AND status='query'", (rid,))
        log_thread(rid, "team", body_of(message))
        await log_channel(f"{E('mail')} Team ➛ admin #{rid}")
        await archive_copy(message)
    await tidy(message)
    await bot.send_message(chat, f"{E('ok')} {sc('Message sent to admin.')}" if delivered
                           else f"{E('err')} {sc('Could not reach admin, please try again later.')}",
                           reply_markup=back_keyboard())


# ----------------------------------------------------------------------------
# Admin panel
# ----------------------------------------------------------------------------
def admin_text():
    return "\n".join([
        bq(f"{E('admin')} {sc('Admin panel')}"),
        "",
        row("wait", "Pending Teams", count("SELECT COUNT(*) FROM registrations WHERE status IN ('pending','query')")),
        row("trophy", "Open Tournaments", count("SELECT COUNT(*) FROM tournaments WHERE status='open'")),
        row("group", "Users", count("SELECT COUNT(*) FROM users")),
    ])


@dp.callback_query(F.data == "admin")
async def admin_panel(callback: CallbackQuery, state: FSMContext):
    if not await admin_only(callback):
        return
    await state.clear()
    await sweep(callback.message.chat.id, keep=callback.message.message_id)
    await safe_edit(callback, admin_text(), admin_keyboard())
    await callback.answer()


@dp.callback_query(F.data.startswith("alist:"))
async def admin_list(callback: CallbackQuery):
    if not await admin_only(callback):
        return
    mode = callback.data.split(":")[1]
    where = "WHERE status IN ('pending','query') " if mode == "pending" else ""
    rows = q_all(f"SELECT * FROM registrations {where}ORDER BY id DESC LIMIT 25")
    lines = [bq(f"{E('list')} {sc('Pending teams' if mode == 'pending' else 'Latest registrations')}"), ""]
    kb = []
    if not rows:
        lines.append(sc("Nothing here."))
    for r in rows:
        lines.append(f"{STATUS_ICON[r['status']]} #{r['id']} {esc(r['team_name'])}")
        kb.append([btn(f"#{r['id']} {r['team_name'][:20]}", "box", callback_data=f"areg:{r['id']}")])
    await safe_edit(callback, "\n".join(lines), admin_back(*kb))
    await callback.answer()


@dp.callback_query(F.data.startswith("areg:"))
async def admin_reg_view(callback: CallbackQuery):
    if not await admin_only(callback):
        return
    r = get_reg(int(callback.data.split(":")[1]))
    if not r:
        return await callback.answer("Not found.", show_alert=True)
    chat = callback.message.chat.id
    await _delete(chat, callback.message.message_id)
    kb = reg_admin_kb(r["id"], r["status"])
    try:
        await bot.send_photo(chat, r["screenshot_file_id"], caption=reg_caption(r), reply_markup=kb)
    except Exception:
        await bot.send_message(chat, reg_caption(r), reply_markup=kb)
    await callback.answer()


async def _edit_admin_card(callback: CallbackQuery, verdict, rid, status):
    try:
        await callback.message.edit_caption(
            caption=f"{callback.message.html_text}\n\n{verdict}", reply_markup=reg_admin_kb(rid, status))
    except TelegramBadRequest:
        pass


@dp.callback_query(F.data.startswith("rok:"))
async def reg_approve(callback: CallbackQuery):
    if not await admin_only(callback):
        return
    rid = int(callback.data.split(":")[1])
    done = run("UPDATE registrations SET status='approved', reason=NULL, reviewed_at=? "
               "WHERE id=? AND status IN ('pending','query')", (now_iso(), rid))
    r = get_reg(rid)
    if not r or r["status"] != "approved":
        return await callback.answer("Already reviewed.", show_alert=True)
    t = get_tour(r["tournament_id"])
    notified = True
    try:
        await bot.send_message(r["user_id"], "\n".join([
            bq(f"{E('party')} {sc('Registration approved')}"),
            head("ok", "You Are In", " ❗️"),
            "",
            row("group", "Team", esc(r["team_name"])),
            row("trophy", "Tournament", esc(t["title"])),
            row("calendar", "Starts", esc(t["start_time"])),
            SEP,
            f"{E('bell')} {sc('Room ID and password will be sent here before the match.')}",
        ]), reply_markup=back_keyboard(
            [btn("Message Admin", "mail", callback_data=f"treply:{rid}")]))
    except Exception:
        notified = False
        logging.exception("could not notify %s", r["user_id"])
    verdict = f"{E('ok')} <b>{sc('Approved')}</b>" + ("" if notified else f"\n{E('warn')} {sc('User could not be notified.')}")
    await _edit_admin_card(callback, verdict, rid, "approved")
    await log_channel(f"{E('ok')} Registration #{rid} APPROVED by {callback.from_user.id}")
    spawn(backup_now("approval"))
    await callback.answer("Approved.")


@dp.callback_query(F.data.startswith("rno:"))
async def reg_reject_start(callback: CallbackQuery, state: FSMContext):
    if not await admin_only(callback):
        return
    rid = int(callback.data.split(":")[1])
    r = get_reg(rid)
    if not r or r["status"] not in ("pending", "query"):
        return await callback.answer("Already reviewed.", show_alert=True)
    await state.clear()
    await state.set_state(AdminFlow.reject_reason)
    await state.update_data(rid=rid)
    await ask(callback.message.chat.id,
              f"{E('err')} {sc('Send the rejection reason for')} #{rid} ({sc('or send - for none')}).\n{sc('Send /cancel to stop.')}")
    await callback.answer()


@dp.message(AdminFlow.reject_reason)
async def reg_reject_do(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    chat = message.chat.id
    rid = (await state.get_data())["rid"]
    reason = None if (message.text or "-").strip() == "-" else message.text.strip()
    run("UPDATE registrations SET status='rejected', reason=?, reviewed_at=? "
        "WHERE id=? AND status IN ('pending','query')", (reason, now_iso(), rid))
    r = get_reg(rid)
    await state.clear()
    await tidy(message)
    await sweep(chat)
    notified = True
    try:
        await bot.send_message(r["user_id"], "\n".join([
            bq(f"{E('err')} {sc('Registration rejected')}"),
            "",
            row("group", "Team", esc(r["team_name"])),
            *([row("warn", "Reason", esc(reason))] if reason else []),
            SEP,
            sc("You may register again with correct details, or message admin."),
        ]), reply_markup=back_keyboard([btn("Message Admin", "mail", callback_data=f"treply:{rid}")]))
    except Exception:
        notified = False
    await log_channel(f"{E('err')} Registration #{rid} REJECTED by {message.from_user.id} | {esc(reason)}")
    await notice(chat, f"{E('ok')} {sc('Rejected')} #{rid}" + ("" if notified else f"\n{E('warn')} {sc('User could not be notified.')}"), ttl=8)


# ---- tournaments: add / manage -------------------------------------------------
async def begin_add_tournament(chat, state: FSMContext):
    await state.clear()
    await sweep(chat)
    await state.set_state(AddT.title)
    await ask(chat, f"{E('plus')} {sc('New tournament · step 1/7')}\n{sc('Send the tournament name.')}\n{sc('Send /cancel to stop.')}")


@dp.callback_query(F.data == "aaddt")
async def add_t_button(callback: CallbackQuery, state: FSMContext):
    if not await admin_only(callback):
        return
    await begin_add_tournament(callback.message.chat.id, state)
    await callback.answer()


async def _step(message: Message, state: FSMContext, key, next_state, prompt, value=None):
    chat = message.chat.id
    await tidy(message)
    await sweep(chat)
    await state.update_data(**{key: value if value is not None else (message.text or "").strip()})
    await state.set_state(next_state)
    await ask(chat, prompt)


@dp.message(AddT.title)
async def add_t_title(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id) or not message.text:
        return
    await _step(message, state, "title", AddT.mode,
                f"{E('game')} {sc('Step 2/7 · mode? Example: Squad, Duo, Solo, CS')}")


@dp.message(AddT.mode)
async def add_t_mode(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id) or not message.text:
        return
    await _step(message, state, "mode", AddT.time,
                f"{E('calendar')} {sc('Step 3/7 · date and time? Example: 2 Nov, 8:00 PM')}")


@dp.message(AddT.time)
async def add_t_time(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id) or not message.text:
        return
    await _step(message, state, "time", AddT.fee,
                f"{E('pay')} {sc('Step 4/7 · entry fee in ₹? Send a number, or skip for')} ₹{DEFAULT_FEE}")


@dp.message(AddT.fee)
async def add_t_fee(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id) or not message.text:
        return
    txt = message.text.strip().lower()
    if txt != "skip" and not txt.isdigit():
        await tidy(message)
        return await notice(message.chat.id, f"{E('warn')} {sc('Send a number or skip.')}", ttl=5)
    await _step(message, state, "fee", AddT.slots,
                f"{E('group')} {sc('Step 5/7 · total team slots? Send a number.')}",
                value=DEFAULT_FEE if txt == "skip" else int(txt))


@dp.message(AddT.slots)
async def add_t_slots(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id) or not message.text:
        return
    txt = message.text.strip()
    if not txt.isdigit() or int(txt) < 1:
        await tidy(message)
        return await notice(message.chat.id, f"{E('warn')} {sc('Send a number.')}", ttl=5)
    await _step(message, state, "slots", AddT.prize,
                f"{E('star')} {sc('Step 6/7 · prize details? Example: 1st ₹500, 2nd ₹300. Or skip.')}", value=int(txt))


@dp.message(AddT.prize)
async def add_t_prize(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id) or not message.text:
        return
    txt = message.text.strip()
    await _step(message, state, "prize", AddT.rules,
                f"{E('pin')} {sc('Step 7/7 · extra notes for players? Or skip.')}",
                value="" if txt.lower() == "skip" else txt)


@dp.message(AddT.rules)
async def add_t_rules(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id) or not message.text:
        return
    chat = message.chat.id
    txt = message.text.strip()
    d = await state.get_data()
    await state.clear()
    await tidy(message)
    await sweep(chat)
    tid = run("INSERT INTO tournaments(title, mode, start_time, fee, prize, slots, rules, status, created_at) "
              "VALUES (?,?,?,?,?,?,?, 'open', ?)",
              (d["title"], d["mode"], d["time"], d["fee"], d["prize"] or None, d["slots"],
               None if txt.lower() == "skip" else txt, now_iso()))
    t = get_tour(tid)
    await log_channel(f"{E('new')} Tournament created\n{tour_text(t)}")
    await bot.send_message(chat, f"{tour_text(t)}\n{SEP}\n{E('ok')} {sc('Tournament is live.')}", reply_markup=admin_back(
        [btn("Announce To All Users", "channel", style="primary", callback_data=f"tann:{tid}")],
        [btn("Add Another", "plus", style="success", callback_data="aaddt")]))


@dp.callback_query(F.data == "atours")
async def admin_tours(callback: CallbackQuery):
    if not await admin_only(callback):
        return
    rows = q_all("SELECT * FROM tournaments ORDER BY id DESC LIMIT 15")
    lines = [bq(f"{E('trophy')} {sc('Manage tournaments')}"), ""]
    kb = []
    if not rows:
        lines.append(sc("None yet. Use Add Tournament."))
    for t in rows:
        lines.append(f"{E('dot')} #{t['id']} <b>{esc(t['title'])}</b> ➛ {sc(t['status'])} | {used_slots(t['id'])}/{t['slots']}")
        kb.append([btn(f"#{t['id']} {t['title'][:22]}", "trophy", callback_data=f"tm:{t['id']}")])
    await safe_edit(callback, "\n".join(lines), admin_back(*kb))
    await callback.answer()


def tm_keyboard(t):
    return admin_back(
        [btn("Announce To All", "channel", style="primary", callback_data=f"tann:{t['id']}"),
         btn("Set Prize", "star", callback_data=f"tprize:{t['id']}")],
        [btn("Message Approved Teams", "mail", callback_data=f"tmsg:{t['id']}")],
        [btn("Close" if t["status"] == "open" else "Reopen", "lock", callback_data=f"ttog:{t['id']}"),
         btn("Delete", "trash", style="danger", callback_data=f"tdel:{t['id']}")],
        [btn("All Tournaments", "trophy", callback_data="atours")])


@dp.callback_query(F.data.startswith("tm:"))
async def tour_manage(callback: CallbackQuery):
    if not await admin_only(callback):
        return
    t = get_tour(int(callback.data.split(":")[1]))
    if not t:
        return await callback.answer("Not found.", show_alert=True)
    await safe_edit(callback, tour_text(t), tm_keyboard(t))
    await callback.answer()


@dp.callback_query(F.data.startswith("ttog:"))
async def tour_toggle(callback: CallbackQuery):
    if not await admin_only(callback):
        return
    t = get_tour(int(callback.data.split(":")[1]))
    run("UPDATE tournaments SET status=? WHERE id=?", ("closed" if t["status"] == "open" else "open", t["id"]))
    t = get_tour(t["id"])
    await safe_edit(callback, tour_text(t), tm_keyboard(t))
    await callback.answer("Updated.")


@dp.callback_query(F.data.startswith("tdel:"))
async def tour_delete_ask(callback: CallbackQuery):
    if not await admin_only(callback):
        return
    tid = int(callback.data.split(":")[1])
    n = count("SELECT COUNT(*) FROM registrations WHERE tournament_id=?", (tid,))
    await safe_edit(callback, "\n".join([
        bq(f"{E('trash')} {sc('Delete tournament')} #{tid}"), "",
        f"{E('warn')} {sc('This also hides its')} {n} {sc('registrations from lists. Continue?')}"]),
        admin_back([btn("Yes, Delete", "trash", style="danger", callback_data=f"tdelok:{tid}")],
                   [btn("Cancel", "err", callback_data=f"tm:{tid}")]))
    await callback.answer()


@dp.callback_query(F.data.startswith("tdelok:"))
async def tour_delete(callback: CallbackQuery):
    if not await admin_only(callback):
        return
    tid = int(callback.data.split(":")[1])
    run("DELETE FROM tournaments WHERE id=?", (tid,))
    await safe_edit(callback, f"{E('ok')} {sc('Tournament deleted.')}", admin_back())
    await callback.answer()


@dp.callback_query(F.data == "aprize")
async def prize_pick(callback: CallbackQuery):
    if not await admin_only(callback):
        return
    rows = q_all("SELECT * FROM tournaments ORDER BY id DESC LIMIT 15")
    kb = [[btn(f"#{t['id']} {t['title'][:24]}", "star", callback_data=f"tprize:{t['id']}")] for t in rows]
    text = "\n".join([bq(f"{E('star')} {sc('Set prize')}"), "",
                      sc("Choose a tournament:") if rows else sc("No tournaments yet.")])
    await safe_edit(callback, text, admin_back(*kb))
    await callback.answer()


@dp.callback_query(F.data.startswith("tprize:"))
async def prize_ask(callback: CallbackQuery, state: FSMContext):
    if not await admin_only(callback):
        return
    tid = int(callback.data.split(":")[1])
    await state.clear()
    await state.set_state(AdminFlow.prize)
    await state.update_data(tid=tid)
    await ask(callback.message.chat.id, f"{E('star')} {sc('Send the prize details for tournament')} #{tid}.\n"
                                        f"{sc('Example: 1st ₹500, 2nd ₹300, 3rd ₹100')}\n{sc('Send /cancel to stop.')}")
    await callback.answer()


@dp.message(AdminFlow.prize)
async def prize_save(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id) or not message.text:
        return
    tid = (await state.get_data())["tid"]
    run("UPDATE tournaments SET prize=? WHERE id=?", (message.text.strip(), tid))
    await state.clear()
    await tidy(message)
    await sweep(message.chat.id)
    await notice(message.chat.id, f"{E('ok')} {sc('Prize updated for')} #{tid}", ttl=6)


# ---- broadcasts / updates -------------------------------------------------------
async def send_all(user_ids, text=None, src: Message = None):
    sent = failed = 0
    for uid in user_ids:
        try:
            if src:
                await bot.copy_message(uid, src.chat.id, src.message_id)
            else:
                await bot.send_message(uid, text)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.04)
    return sent, failed


def all_user_ids():
    return [r["user_id"] for r in q_all("SELECT user_id FROM users WHERE banned=0")]


async def run_broadcast(chat, ids, kind, text=None, src=None):
    status = await bot.send_message(chat, f"{E('spin')} {sc('Sending to')} {len(ids)} {sc('users...')}")
    sent, failed = await send_all(ids, text=text, src=src)
    run("INSERT INTO broadcasts(admin_id, kind, sent_count, failed_count, created_at) VALUES(?,?,?,?,?)",
        (chat, kind, sent, failed, now_iso()))
    await status.edit_text("\n".join([head("ok", "Broadcast Finished", " ❗️"), "",
                                      row("ok", "Delivered", sent), row("err", "Failed", failed)]))
    spawn(_delete_later(chat, status.message_id, 60))
    await log_channel(f"{E('channel')} Broadcast ({esc(kind)}) ✅ {sent} ❌ {failed}")


@dp.callback_query(F.data == "abc")
async def bc_prompt(callback: CallbackQuery, state: FSMContext):
    if not await admin_only(callback):
        return
    await state.clear()
    await state.set_state(AdminFlow.broadcast)
    await state.update_data(tid=None)
    await ask(callback.message.chat.id, f"{E('channel')} {sc('Send the broadcast for all users. Text, photo or any media works.')}\n{sc('Send /cancel to stop.')}")
    await callback.answer()


@dp.callback_query(F.data.startswith("tmsg:"))
async def bc_teams_prompt(callback: CallbackQuery, state: FSMContext):
    if not await admin_only(callback):
        return
    tid = int(callback.data.split(":")[1])
    await state.clear()
    await state.set_state(AdminFlow.broadcast)
    await state.update_data(tid=tid)
    await ask(callback.message.chat.id, f"{E('mail')} {sc('Send the message for all approved teams of tournament')} #{tid}.\n"
                                        f"{sc('Good for room ID and password.')}\n{sc('Send /cancel to stop.')}")
    await callback.answer()


@dp.message(AdminFlow.broadcast)
async def bc_send(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    chat = message.chat.id
    tid = (await state.get_data()).get("tid")
    await state.clear()
    await sweep(chat)
    if tid:
        ids = [r["user_id"] for r in q_all(
            "SELECT DISTINCT user_id FROM registrations WHERE tournament_id=? AND status='approved'", (tid,))]
        kind = f"teams of #{tid}"
    else:
        ids, kind = all_user_ids(), "all users"
    await archive_copy(message)
    await run_broadcast(chat, ids, kind, src=message)   # message is deleted only after it was copied
    await tidy(message)


@dp.callback_query(F.data.startswith("tann:"))
async def announce(callback: CallbackQuery):
    if not await admin_only(callback):
        return
    t = get_tour(int(callback.data.split(":")[1]))
    text = f"{tour_text(t)}\n{SEP}\n{E('bolt')} {sc('Open the bot and tap Tournaments to register.')}"
    await callback.answer("Sending...")
    await run_broadcast(callback.message.chat.id, all_user_ids(), f"announce #{t['id']}", text=text)


@dp.callback_query(F.data == "aupd")
async def update_prompt(callback: CallbackQuery, state: FSMContext):
    if not await admin_only(callback):
        return
    await state.clear()
    await state.set_state(AdminFlow.update)
    await ask(callback.message.chat.id, f"{E('bell')} {sc('Send the update text. It is saved under Updates and sent to all users.')}\n{sc('Send /cancel to stop.')}")
    await callback.answer()


@dp.message(AdminFlow.update)
async def update_save(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id) or not message.text:
        return
    chat = message.chat.id
    run("INSERT INTO updates(body, created_at) VALUES(?,?)", (message.text.strip(), now_iso()))
    await state.clear()
    await tidy(message)
    await sweep(chat)
    text = "\n".join([bq(f"{E('bell')} {sc('New update')}"), "", esc(message.text.strip())])
    await run_broadcast(chat, all_user_ids(), "update", text=text)


# ---- stats / users / csv / backup / restore --------------------------------------
@dp.callback_query(F.data == "astats")
async def admin_stats(callback: CallbackQuery):
    if not await admin_only(callback):
        return
    c = lambda s, a=(): count(s, a)
    text = "\n".join([
        bq(f"{E('stats')} {sc('Statistics')}"), "",
        row("group", "Users", c("SELECT COUNT(*) FROM users")),
        row("ban", "Banned", c("SELECT COUNT(*) FROM users WHERE banned=1")),
        row("trophy", "Tournaments", c("SELECT COUNT(*) FROM tournaments")),
        row("wait", "Pending", c("SELECT COUNT(*) FROM registrations WHERE status IN ('pending','query')")),
        row("ok", "Approved", c("SELECT COUNT(*) FROM registrations WHERE status='approved'")),
        row("err", "Rejected", c("SELECT COUNT(*) FROM registrations WHERE status='rejected'")),
        row("money", "Fees Collected", f"₹{c('SELECT COALESCE(SUM(t.fee),0) FROM registrations r JOIN tournaments t ON t.id=r.tournament_id WHERE r.status=?', ('approved',))}"),
    ])
    await safe_edit(callback, text, admin_back())
    await callback.answer()


@dp.callback_query(F.data == "ausers")
async def admin_users(callback: CallbackQuery):
    if not await admin_only(callback):
        return
    rows = q_all("SELECT user_id, username, first_name FROM users ORDER BY joined_at DESC LIMIT 25")
    lines = [bq(f"{E('group')} {sc('Latest 25 users')}"), ""]
    for r in rows:
        label = f"@{r['username']}" if r["username"] else (r["first_name"] or "unknown")
        lines.append(f"{E('user')} {esc(label)} ➛ <code>{r['user_id']}</code>")
    await safe_edit(callback, "\n".join(lines), admin_back())
    await callback.answer()


def make_csv():
    rows = q_all("""SELECT r.id, t.title AS tournament, r.team_name, r.uids, r.user_id, u.username, r.status,
                    r.reason, r.created_at, r.reviewed_at FROM registrations r
                    LEFT JOIN tournaments t ON t.id=r.tournament_id LEFT JOIN users u ON u.user_id=r.user_id
                    ORDER BY r.id""")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "tournament", "team_name", "uids", "user_id", "username", "status", "reason", "created_at", "reviewed_at"])
    for r in rows:
        w.writerow(list(r))
    return BufferedInputFile(buf.getvalue().encode("utf-8-sig"), filename=f"registrations_{datetime.now():%Y%m%d_%H%M}.csv")


@dp.callback_query(F.data == "acsv")
async def admin_csv(callback: CallbackQuery):
    if not await admin_only(callback):
        return
    await bot.send_document(callback.message.chat.id, make_csv(), caption=f"{E('csv')} {sc('Registrations export')}")
    await callback.answer()


@dp.callback_query(F.data == "abackup")
async def admin_backup(callback: CallbackQuery):
    if not await admin_only(callback):
        return
    await callback.answer("Creating backup...")
    path = await backup_now("manual")
    await bot.send_document(callback.message.chat.id, BufferedInputFile(path.read_bytes(), filename=path.name),
                            caption=f"{E('backup')} {sc('Backup saved on host')}: <code>{esc(path)}</code>")


@dp.callback_query(F.data == "arestore")
async def admin_restore_prompt(callback: CallbackQuery, state: FSMContext):
    if not await admin_only(callback):
        return
    await state.clear()
    await state.set_state(AdminFlow.restore)
    await ask(callback.message.chat.id, f"{E('restore')} {sc('Send the .db backup file to restore.')}\n"
                                        f"{sc('Current data is backed up first.')}\n{sc('Send /cancel to stop.')}")
    await callback.answer()


@dp.message(AdminFlow.restore)
async def admin_restore_do(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    chat = message.chat.id
    if not message.document:
        await tidy(message)
        return await notice(chat, f"{E('warn')} {sc('Send the .db file as a document.')}", ttl=6)
    tmp = Path(tempfile.gettempdir()) / f"restore_{message.document.file_unique_id}.db"
    await bot.download(message.document, destination=tmp)
    try:
        with closing(sqlite3.connect(tmp)) as c:
            names = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"users", "registrations", "tournaments"} <= names:
            raise ValueError("missing tables")
    except Exception:
        tmp.unlink(missing_ok=True)
        await state.clear()
        await sweep(chat)
        return await notice(chat, f"{E('err')} {sc('That is not a valid backup file.')}", ttl=8)
    await backup_now("pre-restore")
    shutil.copyfile(tmp, DB_PATH)
    tmp.unlink(missing_ok=True)
    init_db()
    await state.clear()
    await sweep(chat)
    await tidy(message)
    await log_channel(f"{E('restore')} Database restored by {message.from_user.id}")
    await notice(chat, f"{E('ok')} {sc('Database restored successfully.')}", ttl=10)


# ----------------------------------------------------------------------------
# Run
# ----------------------------------------------------------------------------
async def main():
    init_db()
    spawn(backup_loop())
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Bot running - Hosted By Erebus")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
