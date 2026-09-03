import os
import time
from threading import Lock

import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ==================================================
# CONFIGURATION
# ==================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is missing")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

BOT_USERNAME = "MineNovbot"

MINING_REWARD = 10
MINING_COOLDOWN = 24 * 60 * 60  # 24 hours


# ==================================================
# TEMPORARY USER STORAGE
# ==================================================
# This is only for testing.
# We will replace it with a real database later.

users = {}
users_lock = Lock()


# ==================================================
# TELEGRAM API
# ==================================================

def telegram(method, data=None):
    response = requests.post(
        f"{TELEGRAM_API}/{method}",
        json=data or {},
        timeout=15
    )

    response.raise_for_status()
    return response.json()


def send_message(chat_id, text, keyboard=None):

    data = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        data["reply_markup"] = {
            "keyboard": keyboard,
            "resize_keyboard": True
        }

    return telegram("sendMessage", data)


# ==================================================
# KEYBOARD
# ==================================================

def main_keyboard():

    return [
        ["⛏️ Mine", "💰 Balance"],
        ["👥 Referral", "📊 Statistics"]
    ]


# ==================================================
# USER MANAGEMENT
# ==================================================

def get_user(telegram_id, username=None):

    with users_lock:

        if telegram_id not in users:

            users[telegram_id] = {
                "telegram_id": telegram_id,
                "username": username or "",
                "balance": 0,
                "last_mine": 0,
                "referrals": 0
            }

        elif username:

            users[telegram_id]["username"] = username

        return users[telegram_id]


# ==================================================
# /START
# ==================================================

def handle_start(message):

    user = message["from"]

    telegram_id = user["id"]
    username = user.get("username", "")

    account = get_user(
        telegram_id,
        username
    )

    chat_id = message["chat"]["id"]

    send_message(
        chat_id,

        "🚀 Welcome to MineNova!\n\n"

        "⛏️ Earn points through eligible activities.\n\n"

        f"💰 Your balance: {account['balance']} points\n\n"

        "Choose an option below:",

        main_keyboard()
    )


# ==================================================
# MINING
# ==================================================

def handle_mine(message):

    user = message["from"]

    telegram_id = user["id"]
    username = user.get("username", "")

    account = get_user(
        telegram_id,
        username
    )

    chat_id = message["chat"]["id"]

    current_time = time.time()

    elapsed = current_time - account["last_mine"]

    # Check 24-hour cooldown

    if elapsed < MINING_COOLDOWN:

        remaining = int(
            MINING_COOLDOWN - elapsed
        )

        hours = remaining // 3600

        minutes = (remaining % 3600) // 60

        send_message(
            chat_id,

            "⏳ You have already mined today.\n\n"

            f"Try again in approximately "
            f"{hours}h {minutes}m."
        )

        return

    # Add reward

    with users_lock:

        account["balance"] += MINING_REWARD

        account["last_mine"] = current_time

        new_balance = account["balance"]

    send_message(
        chat_id,

        "⛏️ Mining complete!\n\n"

        f"🎁 Reward: +{MINING_REWARD} points\n\n"

        f"💰 New balance: {new_balance} points"
    )


# ==================================================
# BALANCE
# ==================================================

def handle_balance(message):

    user = message["from"]

    telegram_id = user["id"]
    username = user.get("username", "")

    account = get_user(
        telegram_id,
        username
    )

    send_message(
        message["chat"]["id"],

        "💰 MineNova Balance\n\n"

        f"⭐ {account['balance']} points"
    )


# ==================================================
# REFERRAL
# ==================================================

def handle_referral(message):

    user = message["from"]

    telegram_id = user["id"]
    username = user.get("username", "")

    account = get_user(
        telegram_id,
        username
    )

    referral_link = (
        f"https://t.me/{BOT_USERNAME}"
        f"?start={telegram_id}"
    )

    send_message(
        message["chat"]["id"],

        "👥 MineNova Referral\n\n"

        "Invite your friends using your personal link:\n\n"

        f"{referral_link}\n\n"

        f"👤 Referrals: {account['referrals']}\n\n"

        "Referral rewards will be activated "
        "when we add the permanent database system."
    )


# ==================================================
# STATISTICS
# ==================================================

def handle_statistics(message):

    user = message["from"]

    telegram_id = user["id"]
    username = user.get("username", "")

    account = get_user(
        telegram_id,
        username
    )

    with users_lock:

        total_users = len(users)

    send_message(
        message["chat"]["id"],

        "📊 MineNova Statistics\n\n"

        f"💰 Balance: {account['balance']} points\n"

        f"👥 Your referrals: {account['referrals']}\n"

        f"🌎 Total users: {total_users}"
    )


# ==================================================
# MESSAGE HANDLER
# ==================================================

def process_message(message):

    text = message.get(
        "text",
        ""
    ).strip()

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

            "Please choose an option "
            "from the MineNova menu.",

            main_keyboard()
        )


# ==================================================
# HOME PAGE
# ==================================================

@app.get("/")
def home():

    return jsonify({
        "status": "online",
        "bot": "MineNova",
        "telegram_username": BOT_USERNAME
    })


# ==================================================
# TELEGRAM WEBHOOK
# ==================================================

@app.post("/webhook")
def webhook():

    update = request.get_json(
        silent=True
    )

    if not update:

        return jsonify({
            "ok": True
        })

    try:

        message = update.get(
            "message"
        )

        if message:

            process_message(message)

    except Exception as error:

        print(
            f"Update processing error: {error}"
        )

    return jsonify({
        "ok": True
    })


# ==================================================
# LOCAL DEVELOPMENT
# ==================================================

if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            "8080"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
