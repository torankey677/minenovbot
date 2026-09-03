import os
import time
from threading import Lock

import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# --------------------------------------------------
# Configuration
# --------------------------------------------------

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is missing")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

MINING_REWARD = 10
MINING_COOLDOWN = 24 * 60 * 60  # 24 hours

# Temporary storage.
# We will replace this with a database later.
users = {}
users_lock = Lock()


# --------------------------------------------------
# Telegram helpers
# --------------------------------------------------

def telegram(method, data=None):
    """Send a request to the Telegram Bot API."""
    response = requests.post(
        f"{TELEGRAM_API}/{method}",
        json=data or {},
        timeout=15
    )

    response.raise_for_status()
    return response.json()


def send_message(chat_id, text, keyboard=None):
    """Send a Telegram message."""
    data = {
        "chat_id": chat_id,
        "text": text,
    }

    if keyboard:
        data["reply_markup"] = {
            "keyboard": keyboard,
            "resize_keyboard": True
        }

    return telegram("sendMessage", data)


# --------------------------------------------------
# User management
# --------------------------------------------------

def get_user(telegram_id, username=None):
    """Create or retrieve a MineNova user."""
    with users_lock:
        if telegram_id not in users:
            users[telegram_id] = {
                "telegram_id": telegram_id,
                "username": username or "",
                "balance": 0,
                "last_mine": 0,
            }

        elif username:
            users[telegram_id]["username"] = username

        return users[telegram_id]


def main_keyboard():
    return [
        ["⛏️ Mine", "💰 Balance"],
        ["👥 Referral", "📊 Statistics"],
    ]


# --------------------------------------------------
# Bot commands
# --------------------------------------------------

def handle_start(message):
    user = message["from"]

    telegram_id = user["id"]
    username = user.get("username", "")

    get_user(telegram_id, username)

    send_message(
        message["chat"]["id"],
        "🚀 Welcome to MineNova!\n\n"
        "Earn points by completing eligible activities.\n\n"
        "Choose an option below:",
        main_keyboard()
    )


def handle_mine(message):
    user = message["from"]

    telegram_id = user["id"]
    username = user.get("username", "")

    account = get_user(telegram_id, username)

    now = time.time()
    elapsed = now - account["last_mine"]

    if elapsed < MINING_COOLDOWN:
        remaining = int(MINING_COOLDOWN - elapsed)

        hours = remaining // 3600
        minutes = (remaining % 3600) // 60

        send_message(
            message["chat"]["id"],
            f"⏳ You have already mined today.\n\n"
            f"Try again in approximately {hours}h {minutes}m."
        )
        return

    with users_lock:
        account["balance"] += MINING_REWARD
        account["last_mine"] = now
        new_balance = account["balance"]

    send_message(
        message["chat"]["id"],
        f"⛏️ Mining complete!\n\n"
        f"🎁 Reward: +{MINING_REWARD} points\n"
        f"💰 Balance: {new_balance} points"
    )


def handle_balance(message):
    user = message["from"]

    telegram_id = user["id"]
    username = user.get("username", "")

    account = get_user(telegram_id, username)

    send_message(
        message["chat"]["id"],
        f"💰 Your MineNova balance\n\n"
        f"⭐ {account['balance']} points"
    )


def handle_referral(message):
    user = message["from"]

    telegram_id = user["id"]
    username = user.get("username", "")

    get_user(telegram_id, username)

    # Replace YOUR_BOT_USERNAME after creating the bot.
    referral_link = f"https://t.me/YOUR_BOT_USERNAME?start={telegram_id}"

    send_message(
        message["chat"]["id"],
        "👥 Invite friends to MineNova.\n\n"
        "Your referral link:\n"
        f"{referral_link}\n\n"
        "Referral rewards will be added when we build the database-backed referral system."
    )


def handle_statistics(message):
    user = message["from"]

    telegram_id = user["id"]
    username = user.get("username", "")

    account = get_user(telegram_id, username)

    with users_lock:
        total_users = len(users)

    send_message(
        message["chat"]["id"],
        f"📊 Your Statistics\n\n"
        f"💰 Balance: {account['balance']} points\n"
        f"👤 Total users: {total_users}"
    )


# --------------------------------------------------
# Message router
# --------------------------------------------------

def process_message(message):
    text = message.get("text", "").strip()

    if text.startswith("/start"):
        handle_start(message)

    elif text == "/mine" or text == "⛏️ Mine":
        handle_mine(message)

    elif text == "/balance" or text == "💰 Balance":
        handle_balance(message)

    elif text == "/referral" or text == "👥 Referral":
        handle_referral(message)

    elif text == "/stats" or text == "📊 Statistics":
        handle_statistics(message)

    else:
        send_message(
            message["chat"]["id"],
            "Please choose an option from the MineNova menu.",
            main_keyboard()
        )


# --------------------------------------------------
# Web routes
# --------------------------------------------------

@app.get("/")
def home():
    return jsonify({
        "status": "online",
        "bot": "MineNova"
    })


@app.post("/webhook")
def webhook():
    update = request.get_json(silent=True)

    if not update:
        return jsonify({"ok": True})

    try:
        message = update.get("message")

        if message:
            process_message(message)

    except Exception as error:
        # Log the error without exposing sensitive information.
        print(f"Update processing error: {error}")

    return jsonify({"ok": True})


# --------------------------------------------------
# Local development
# --------------------------------------------------

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
