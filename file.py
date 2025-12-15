import logging
import random
import re
import string
import sqlite3
from datetime import datetime, timedelta

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ================== BASIC CONFIG ==================

BOT_TOKEN = "8018642785:AAGUEf60ryq5Q2fFzHVNrMIFaD6MEzf33es"   # <--- yaha apna token daal
BOT_USERNAME = "OGfilesharebot"      # without @

OWNER_ID = 6432580068
DB_PATH = "files.db"

DEFAULT_FREE_FILE_LIMIT = 5

# FORCE JOIN SETTINGS
FORCE_JOIN_CHAT_ID = -1002148143676   # <--- @hosthunter ka real chat id (integer)
FORCE_JOIN_LINK = "https://t.me/hosthunterback"

FORCE_JOIN_TEXT = (
    "🔐 *Access Locked*\n\n"
    "This bot is only available for members of our official channel.\n\n"
    "👉 *Step 1:* Tap *Join Channel* and join @hosthunter.\n"
    "👉 *Step 2:* Come back here and tap *✅ I’ve joined, verify me*.\n\n"
    "Without joining, you won't be able to host or download any files."
)

START_BANNER = (
    "⚡️ 𝗛𝗼𝘀𝘁𝗛𝘂𝗻𝘁𝗲𝗿 • 𝗙𝗶𝗹𝗲 𝗛𝗼𝘀𝘁𝗶𝗻𝗴 𝗕𝗼𝘁\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "📦 Host Telegram bots, ZIPs, configs, media & more.\n"
    "🔗 Get a sharable link for every file.\n"
    "🛡 Files are stored securely inside Telegram.\n"
)

HELP_TEXT = (
    "📘 *How to use this bot*\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "1️⃣ *Upload File*\n"
    "   • Just send any file (ZIP, bot file, document, photo, video, etc.).\n"
    "   • The bot will host it and give you a unique link.\n\n"
    "2️⃣ *Share & Download*\n"
    "   • Share the link with anyone.\n"
    "   • When they open the link, this bot will send them the file.\n\n"
    "3️⃣ *Manage Your Files*\n"
    "   • Use the *📁 MANAGE FILES* button to see your recent uploads.\n"
    "   • Use `/delete <code>` to remove a hosted file.\n\n"
    "💎 *Premium System*\n"
    "   • Free users: limited number of hosted files.\n"
    "   • Premium users: higher file limit & more flexibility.\n"
    "   • Users activate keys: `/redeem HOSTHUNTER-XXXX-XXXX`\n\n"
    "👨‍💻 *Useful Commands*\n"
    "   • `/start` – Welcome / open file from link\n"
    "   • `/help` – Show this help menu\n"
    "   • `/myinfo` or `/status` – Your plan & limits\n"
    "   • `/redeem` – Redeem your premium key\n"
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ================== USER KEYBOARD ==================

USER_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("📤 UPLOAD FILE"), KeyboardButton("📁 MANAGE FILES")],
        [KeyboardButton("🔑 REDEEM KEY"), KeyboardButton("💎 BUY SUBSCRIPTION")],
        [KeyboardButton("👤 MY INFO"), KeyboardButton("📊 STATUS")],
    ],
    resize_keyboard=True,
)

# ================== DB ==================

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            file_type TEXT,
            file_id TEXT,
            caption TEXT,
            uploader_id INTEGER,
            created_at TEXT,
            downloads INTEGER DEFAULT 0
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            status TEXT,
            expires_at TEXT,
            file_limit INTEGER,
            created_at TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS redeem_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            days INTEGER,
            file_limit INTEGER,
            created_at TEXT,
            used_by INTEGER,
            used_at TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS banned_users (
            user_id INTEGER PRIMARY KEY
        )
        """
    )

    conn.commit()
    conn.close()

# ================== HELPERS ==================

def now_utc() -> datetime:
    return datetime.utcnow()

def generate_random_code(length: int = 8) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))

def generate_redeem_code() -> str:
    chars = string.ascii_uppercase + string.digits
    def seg():
        return "".join(random.choice(chars) for _ in range(4))
    return f"HOSTHUNTER-{seg()}-{seg()}"

def save_file_to_db(file_type: str, file_id: str, caption: str, uploader_id: int) -> str:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    code = generate_random_code()
    created_at = now_utc().isoformat()
    cur.execute(
        """
        INSERT INTO files (code, file_type, file_id, caption, uploader_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (code, file_type, file_id, caption, uploader_id, created_at),
    )
    conn.commit()
    conn.close()
    return code

def get_file_by_code(code: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, code, file_type, file_id, caption, uploader_id, created_at, downloads
        FROM files
        WHERE code = ?
        """,
        (code,),
    )
    row = cur.fetchone()
    conn.close()
    return row

def increment_download(file_db_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE files SET downloads = downloads + 1 WHERE id = ?", (file_db_id,))
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), COALESCE(SUM(downloads),0) FROM files")
    total_files, total_downloads = cur.fetchone()
    conn.close()
    return total_files or 0, total_downloads or 0

def count_user_files(user_id: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM files WHERE uploader_id = ?", (user_id,))
    (count,) = cur.fetchone()
    conn.close()
    return count or 0

def get_user_files(user_id: int, limit: int = 10):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT code, file_type, caption, created_at, downloads
        FROM files
        WHERE uploader_id = ?
        ORDER BY datetime(created_at) DESC
        LIMIT ?
        """,
        (user_id, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def ensure_user(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, status, expires_at, file_limit, created_at FROM users WHERE user_id = ?",
        (user_id,),
    )
    row = cur.fetchone()
    if not row:
        created_at = now_utc().isoformat()
        cur.execute(
            """
            INSERT INTO users (user_id, status, expires_at, file_limit, created_at)
            VALUES (?, 'free', NULL, ?, ?)
            """,
            (user_id, DEFAULT_FREE_FILE_LIMIT, created_at),
        )
        conn.commit()
        cur.execute(
            "SELECT user_id, status, expires_at, file_limit, created_at FROM users WHERE user_id = ?",
            (user_id,),
        )
        row = cur.fetchone()
    conn.close()
    return row

def get_user(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, status, expires_at, file_limit, created_at FROM users WHERE user_id = ?",
        (user_id,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return ensure_user(user_id)
    return row

def is_premium(user_row) -> bool:
    expires_at = user_row[2]
    if not expires_at:
        return False
    try:
        exp = datetime.fromisoformat(expires_at)
    except Exception:
        return False
    return exp > now_utc()

def get_days_left(user_row) -> int:
    expires_at = user_row[2]
    if not expires_at:
        return 0
    try:
        exp = datetime.fromisoformat(expires_at)
    except Exception:
        return 0
    return max((exp - now_utc()).days, 0)

def update_user_subscription(user_id: int, days: int, file_limit: int):
    base = now_utc()
    expires_at = (base + timedelta(days=days)).isoformat()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO users (user_id, status, expires_at, file_limit, created_at)
        VALUES (?, 'premium', ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            status='premium',
            expires_at=excluded.expires_at,
            file_limit=excluded.file_limit
        """,
        (user_id, expires_at, file_limit, base.isoformat()),
    )
    conn.commit()
    conn.close()

def create_redeem_key(days: int, file_limit: int) -> str:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    while True:
        code = generate_redeem_code()
        try:
            cur.execute(
                """
                INSERT INTO redeem_keys (code, days, file_limit, created_at, used_by, used_at)
                VALUES (?, ?, ?, ?, NULL, NULL)
                """,
                (code, days, file_limit, now_utc().isoformat()),
            )
            conn.commit()
            break
        except sqlite3.IntegrityError:
            continue
    conn.close()
    return code

def get_redeem_key(code: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, code, days, file_limit, created_at, used_by, used_at
        FROM redeem_keys WHERE code = ?
        """,
        (code,),
    )
    row = cur.fetchone()
    conn.close()
    return row

def use_redeem_key(code: str, user_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE redeem_keys
        SET used_by = ?, used_at = ?
        WHERE code = ? AND used_by IS NULL
        """,
        (user_id, now_utc().isoformat(), code),
    )
    changed = cur.rowcount
    conn.commit()
    conn.close()
    return changed > 0

# ---- BAN HELPERS ----

def is_banned_user(user_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM banned_users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row is not None

def ban_user(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO banned_users (user_id) VALUES (?)",
        (user_id,),
    )
    conn.commit()
    conn.close()

def unban_user(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM banned_users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# ================== FORCE JOIN + VERIFY ==================

async def check_force_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not user or user.is_bot:
        return True

    if user.id == OWNER_ID:
        return True

    if is_banned_user(user.id):
        if update.message:
            await update.message.reply_text("⛔ You are banned from using this bot.")
        return False

    if not FORCE_JOIN_CHAT_ID:
        return True

    joined = False
    try:
        member = await context.bot.get_chat_member(FORCE_JOIN_CHAT_ID, user.id)
        if member.status in ("member", "administrator", "creator"):
            joined = True
    except Exception as e:
        logger.warning("Force-join check error: %s", e)
        joined = False

    if joined:
        return True

    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", url=FORCE_JOIN_LINK)],
        [InlineKeyboardButton("✅ I’ve joined, verify me", callback_data="verify_join")],
    ]
    markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(
            FORCE_JOIN_TEXT,
            reply_markup=markup,
            parse_mode="Markdown",
        )

    return False

async def verify_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()

    joined = False
    try:
        member = await context.bot.get_chat_member(FORCE_JOIN_CHAT_ID, user.id)
        if member.status in ("member", "administrator", "creator"):
            joined = True
    except Exception as e:
        logger.warning("Verify-click check error: %s", e)
        joined = False

    if joined:
        text = (
            "✅ *Verification successful!*\n\n"
            "You have joined the channel.\n"
            "Now you can use all bot features.\n\n"
            "➡ Send /start to continue."
        )
    else:
        text = (
            "❌ *You have not joined the channel yet.*\n\n"
            "Please join the channel first, then tap *Verify* again."
        )

    try:
        await query.edit_message_text(text, parse_mode="Markdown")
    except Exception:
        await context.bot.send_message(chat_id=user.id, text=text, parse_mode="Markdown")

# ================== OWNER / ADMIN COMMANDS ==================

async def adminhelp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ You are not allowed.")
        return
    msg = (
        "👑 *OWNER COMMANDS PANEL*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🔹 /adminhelp - Show this help\n"
        "🔹 /stats - Bot stats (files, downloads)\n"
        "🔹 /users - User stats & file overview\n"
        "🔹 /genkey <days> <limit> - Create premium key\n"
        "🔹 /remove_sub <user_id> - Remove user's subscription\n"
        "🔹 /manage - List recent hosted files\n"
        "🔹 /delete <code> - Delete a hosted file\n"
        "🔹 /broadcast <text> - Send message to all users\n"
        "🔹 /ban <user_id> - Ban a user\n"
        "🔹 /unban <user_id> - Unban a user\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ Owner only.")
        return
    total_files, total_downloads = get_stats()
    msg = (
        "📊 *Bot Statistics*\n\n"
        f"Total hosted files: *{total_files}*\n"
        f"Total downloads: *{total_downloads}*"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def users_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ Owner only.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM users WHERE status='premium'")
    premium_users = cur.fetchone()[0] or 0

    free_users = total_users - premium_users

    msg = [
        "👑 *OWNER USER PANEL*",
        "━━━━━━━━━━━━━━━━━━━━",
        f"👥 Total users: *{total_users}*",
        f"💎 Premium users: *{premium_users}*",
        f"🆓 Free users: *{free_users}*",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    cur.execute(
        "SELECT user_id, expires_at, file_limit FROM users "
        "WHERE status='premium' ORDER BY datetime(expires_at) DESC"
    )
    premium_rows = cur.fetchall()

    msg.append("💎 *Premium user IDs:*")
    if premium_rows:
        for uid, expires_at, file_limit in premium_rows:
            days_left = 0
            if expires_at:
                try:
                    exp = datetime.fromisoformat(expires_at)
                    days_left = max((exp - now_utc()).days, 0)
                except Exception:
                    days_left = 0
            msg.append(
                f"• `{uid}`  |  limit: *{file_limit}*  |  days left: *{days_left}*"
            )
    else:
        msg.append("• None")

    msg.append("━━━━━━━━━━━━━━━━━━━━")
    msg.append("📊 *User Upload Summary:*")

    cur.execute("""
        SELECT uploader_id, COUNT(*)
        FROM files
        GROUP BY uploader_id
        ORDER BY COUNT(*) DESC
    """)
    rows = cur.fetchall()

    if rows:
        for uid, count in rows:
            msg.append(f"• `{uid}` → *{count} files*")
    else:
        msg.append("No files hosted yet.")

    conn.close()
    await update.message.reply_text("\n".join(msg), parse_mode="Markdown")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ Owner only.")
        return
    if not context.args:
        await update.message.reply_text(
            "Usage:\n`/broadcast Your message here`",
            parse_mode="Markdown",
        )
        return
    text = " ".join(context.args)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users")
    rows = cur.fetchall()
    conn.close()

    sent = 0
    failed = 0
    for (uid,) in rows:
        try:
            await context.bot.send_message(chat_id=uid, text=text)
            sent += 1
        except Exception:
            failed += 1

    await update.message.reply_text(
        f"📢 Broadcast finished.\n"
        f"✅ Sent to: *{sent}* users\n"
        f"❌ Failed: *{failed}*",
        parse_mode="Markdown",
    )

async def genkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ Owner only.")
        return
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: `/genkey <days> <file_limit>`\nExample: `/genkey 30 999`",
            parse_mode="Markdown",
        )
        return
    try:
        days = int(context.args[0])
        limit = int(context.args[1])
    except ValueError:
        await update.message.reply_text("Both <days> and <file_limit> must be numbers.")
        return
    if days <= 0 or limit <= 0:
        await update.message.reply_text("Values must be greater than 0.")
        return

    code = create_redeem_key(days, limit)
    msg = (
        "✅ *New Subscription Key Created*\n\n"
        f"🔑 Key: `{code}`\n"
        f"📆 Validity: *{days}* days\n"
        f"📁 File limit: *{limit}*\n\n"
        "Share this key with your user. It can be used *only once*."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def remove_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ Owner only.")
        return

    if not context.args:
        await update.message.reply_text(
            "Usage:\n`/remove_sub <user_id>`",
            parse_mode="Markdown",
        )
        return

    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT status FROM users WHERE user_id = ?", (uid,))
    row = cur.fetchone()

    if not row:
        conn.close()
        await update.message.reply_text(
            f"❌ No record found for user `{uid}`.\n"
            "User has probably never used the bot or never had a subscription.",
            parse_mode="Markdown",
        )
        return

    old_status = row[0]

    cur.execute(
        "UPDATE users SET status='free', expires_at=NULL, file_limit=? WHERE user_id=?",
        (DEFAULT_FREE_FILE_LIMIT, uid),
    )
    conn.commit()
    conn.close()

    if old_status != "premium":
        await update.message.reply_text(
            f"ℹ️ User `{uid}` is already FREE.\n"
            "Status set to free and file limit reset.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            f"✔️ Premium subscription removed for user `{uid}`.\n"
            "Status: *FREE* | File limit reset.",
            parse_mode="Markdown",
        )

async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ Owner only.")
        return
    if not context.args:
        await update.message.reply_text("Usage:\n`/ban <user_id>`", parse_mode="Markdown")
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")
        return
    ban_user(uid)
    await update.message.reply_text(f"🚫 Banned user `{uid}`", parse_mode="Markdown")

async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ Owner only.")
        return
    if not context.args:
        await update.message.reply_text("Usage:\n`/unban <user_id>`", parse_mode="Markdown")
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")
        return
    unban_user(uid)
    await update.message.reply_text(f"✅ Unbanned user `{uid}`", parse_mode="Markdown")

# ================== USER COMMANDS ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_force_join(update, context):
        return

    user = update.effective_user
    ensure_user(user.id)
    args = context.args

    if args:
        code = args[0]
        row = get_file_by_code(code)
        if not row:
            await update.message.reply_text("❌ Invalid or expired file link.", reply_markup=USER_KEYBOARD)
            return
        file_db_id, _, file_type, file_id, caption, *_ = row

        if file_type == "document":
            await update.message.reply_document(file_id, caption=caption or "")
        elif file_type == "photo":
            await update.message.reply_photo(file_id, caption=caption or "")
        elif file_type == "video":
            await update.message.reply_video(file_id, caption=caption or "")
        elif file_type == "audio":
            await update.message.reply_audio(file_id, caption=caption or "")
        elif file_type == "voice":
            await update.message.reply_voice(file_id, caption=caption or "")
        elif file_type == "animation":
            await update.message.reply_animation(file_id, caption=caption or "")
        else:
            await update.message.reply_text("⚠️ This file type is not supported yet for sending.")
        increment_download(file_db_id)
        return

    text = START_BANNER + "\n" + HELP_TEXT

    if user.id == OWNER_ID:
        text += "\n\n👑 Use /adminhelp for owner commands."
        await update.message.reply_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=USER_KEYBOARD)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_force_join(update, context):
        return
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown", reply_markup=USER_KEYBOARD)

async def myinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_force_join(update, context):
        return
    user = update.effective_user
    row = get_user(user.id)
    premium = is_premium(row)
    days_left = get_days_left(row)
    file_limit = row[3]
    total_files = count_user_files(user.id)

    status_text = "💎 PREMIUM" if premium else "🆓 FREE"
    if premium:
        sub_text = f"\n⏳ Days left: *{days_left}*"
    else:
        sub_text = "\n💡 Upgrade to premium using a redeem key."

    msg = (
        "👤 *Your Account*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: `{user.id}`\n"
        f"👨‍💻 Name: {user.full_name}\n"
        f"🎯 Status: {status_text}{sub_text}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📁 File limit: *{file_limit}*\n"
        f"📊 Hosted files: *{total_files}*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Tip: Use *📁 MANAGE FILES* to see your uploads."
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=USER_KEYBOARD)

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await myinfo(update, context)

async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_force_join(update, context):
        return
    user = update.effective_user
    if not context.args:
        await update.message.reply_text(
            "Format: `/redeem HOSTHUNTER-XXXX-XXXX`\nExample: `/redeem HOSTHUNTER-A1B2-C3D4`",
            parse_mode="Markdown",
            reply_markup=USER_KEYBOARD,
        )
        return
    code = context.args[0].strip().upper()
    if not re.fullmatch(r"HOSTHUNTER-[A-Z0-9]{4}-[A-Z0-9]{4}", code):
        await update.message.reply_text(
            "❌ *Invalid key format!*\nUse: `HOSTHUNTER-XXXX-XXXX`",
            parse_mode="Markdown",
            reply_markup=USER_KEYBOARD,
        )
        return

    row = get_redeem_key(code)
    if not row:
        await update.message.reply_text("❌ This key does not exist or is invalid.", reply_markup=USER_KEYBOARD)
        return
    _, _, days, file_limit, _, used_by, _ = row
    if used_by is not None:
        await update.message.reply_text("❌ This key has already been used.", reply_markup=USER_KEYBOARD)
        return
    if not use_redeem_key(code, user.id):
        await update.message.reply_text("❌ This key has already been used.", reply_markup=USER_KEYBOARD)
        return

    update_user_subscription(user.id, days, file_limit)
    start_time = now_utc()
    expires = start_time + timedelta(days=days)

    msg = (
        "✅ *SUBSCRIPTION ACTIVATED SUCCESSFULLY!*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🔑 *Subscription Details:*\n"
        f"• Key used: `{code}`\n"
        f"• Validity: *{days} days*\n"
        f"• Start date: `{start_time.strftime('%Y-%m-%d %H:%M:%S')}`\n"
        f"• Expiry date: `{expires.strftime('%Y-%m-%d %H:%M:%S')}`\n"
        f"• Duration: *{days} days*\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=USER_KEYBOARD)

# ================== FILE MANAGEMENT ==================

async def manage_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_force_join(update, context):
        return
    user = update.effective_user

    if user.id == OWNER_ID:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT code, file_type, caption, created_at, downloads, uploader_id
            FROM files
            ORDER BY datetime(created_at) DESC
            LIMIT 10
            """
        )
        rows = cur.fetchall()
        conn.close()
        if not rows:
            await update.message.reply_text("📂 No hosted files yet.")
            return
        lines = ["📂 *Recent hosted files (GLOBAL):*"]
        for i, (code, ftype, caption, created_at, downloads, uid) in enumerate(rows, start=1):
            cshort = (caption[:25] + "…") if caption and len(caption) > 25 else (caption or "No caption")
            lines.append(
                f"{i}. `{code}` · {ftype} · {downloads} dl · user `{uid}`\n   {cshort}"
            )
        lines.append("\nTo delete a file, use:\n`/delete <code>`")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    else:
        files = get_user_files(user.id, limit=10)
        if not files:
            await update.message.reply_text(
                "📂 You don't have any hosted files yet.\n\n"
                "Use *UPLOAD FILE* button or just send a file to host it.",
                parse_mode="Markdown",
                reply_markup=USER_KEYBOARD,
            )
            return
        lines = ["📂 *Your recent hosted files:*"]
        for i, (code, ftype, caption, created_at, downloads) in enumerate(files, start=1):
            caption_short = (caption[:25] + "…") if caption and len(caption) > 25 else (caption or "No caption")
            lines.append(
                f"{i}. `{code}` · {ftype} · {downloads} dl\n   {caption_short}"
            )
        lines.append("\nTo delete a file, send:\n`/delete <code>`")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=USER_KEYBOARD)

async def delete_file_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_force_join(update, context):
        return
    user = update.effective_user
    if not context.args:
        await update.message.reply_text(
            "Usage:\n`/delete <code>`\n\nYou can see codes in *MANAGE FILES*.",
            parse_mode="Markdown",
            reply_markup=USER_KEYBOARD,
        )
        return
    raw = context.args[0]
    code = raw.strip().strip("`").strip()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    if user.id == OWNER_ID:
        cur.execute("DELETE FROM files WHERE code = ?", (code,))
    else:
        cur.execute("DELETE FROM files WHERE code = ? AND uploader_id = ?", (code, user.id))
    deleted = cur.rowcount
    conn.commit()
    conn.close()

    if deleted:
        await update.message.reply_text(
            f"🗑️ File `{code}` deleted.",
            parse_mode="Markdown",
            reply_markup=USER_KEYBOARD,
        )
    else:
        await update.message.reply_text(
            "❌ File not found or you are not the owner of this file.",
            reply_markup=USER_KEYBOARD,
        )

# ================== FILE UPLOAD HANDLER ==================

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_force_join(update, context):
        return
    message = update.message
    user = update.effective_user

    user_row = ensure_user(user.id)
    file_limit = user_row[3]
    total_files = count_user_files(user.id)
    if total_files >= file_limit:
        if is_premium(user_row):
            txt = (
                f"⚠️ You reached your premium file limit (*{file_limit}* hosted files).\n"
                "Please remove some files before hosting new ones."
            )
        else:
            txt = (
                f"⚠️ You reached the free file limit (*{file_limit}* hosted files).\n"
                "Ask the owner @oceanhenter for a premium key and use `/redeem` to upgrade."
            )
        await message.reply_text(txt, reply_markup=USER_KEYBOARD)
        return

    file_type = None
    file_id = None
    if message.document:
        file_type = "document"
        file_id = message.document.file_id
    elif message.photo:
        file_type = "photo"
        file_id = message.photo[-1].file_id
    elif message.video:
        file_type = "video"
        file_id = message.video.file_id
    elif message.audio:
        file_type = "audio"
        file_id = message.audio.file_id
    elif message.voice:
        file_type = "voice"
        file_id = message.voice.file_id
    elif message.animation:
        file_type = "animation"
        file_id = message.animation.file_id

    if not file_type or not file_id:
        await message.reply_text("⚠️ This file type is not supported yet.", reply_markup=USER_KEYBOARD)
        return

    caption = message.caption or ""
    code = save_file_to_db(file_type, file_id, caption, user.id)
    share_link = f"https://t.me/{BOT_USERNAME}?start={code}"

    reply_text = (
        "✅ *Your file has been hosted successfully!*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 *Share Link:*\n`{share_link}`\n\n"
        "📥 Anyone with this link can open this bot and download the file.\n"
        "🗂 You can manage your hosted files from *📁 MANAGE FILES*."
    )
    await message.reply_text(reply_text, parse_mode="Markdown", reply_markup=USER_KEYBOARD)

# ================== TEXT BUTTON HANDLER ==================

async def handle_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_force_join(update, context):
        return
    user = update.effective_user
    if user.id == OWNER_ID:
        await update.message.reply_text("Owner ke liye buttons disabled hain. Use /adminhelp.")
        return

    text = (update.message.text or "").strip().lower()
    if "upload file" in text:
        await update.message.reply_text(
            "📤 Send the file you want to host.",
            reply_markup=USER_KEYBOARD,
        )
    elif "manage files" in text:
        await manage_files(update, context)
    elif "redeem key" in text:
        await update.message.reply_text(
            "Send your key like this:\n`/redeem HOSTHUNTER-XXXX-XXXX`",
            parse_mode="Markdown",
            reply_markup=USER_KEYBOARD,
        )
    elif "buy subscription" in text:
        await update.message.reply_text(
            "💎 To buy subscription, contact the owner @oceanhenter. \n"
            "You will receive a *HOSTHUNTER-XXXX-XXXX* key.\n"
            "Redeem it using `/redeem KEY_HERE`.",
            parse_mode="Markdown",
            reply_markup=USER_KEYBOARD,
        )
    elif "my info" in text:
        await myinfo(update, context)
    elif "status" in text:
        await status_cmd(update, context)
    else:
        await update.message.reply_text(
            "Use the buttons below or commands like /help, /myinfo.",
            reply_markup=USER_KEYBOARD,
        )

# ================== MAIN ==================

def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("myinfo", myinfo))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("redeem", redeem))

    app.add_handler(CommandHandler("adminhelp", adminhelp))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("users", users_stats))
    app.add_handler(CommandHandler("genkey", genkey))
    app.add_handler(CommandHandler("remove_sub", remove_sub))
    app.add_handler(CommandHandler("manage", manage_files))
    app.add_handler(CommandHandler("delete", delete_file_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("ban", ban_cmd))
    app.add_handler(CommandHandler("unban", unban_cmd))

    app.add_handler(CallbackQueryHandler(verify_join_callback, pattern="^verify_join$"))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_menu_buttons,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.Document.ALL
            | filters.PHOTO
            | filters.VIDEO
            | filters.AUDIO
            | filters.VOICE
            | filters.ANIMATION,
            handle_file,
        )
    )

    logger.info("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()