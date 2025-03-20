import asyncio
import logging
import time
import os
from datetime import datetime

import pytz
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.exceptions import TelegramNetworkError
from bs4 import BeautifulSoup

from config import TOKEN
from handler import router

# Enable logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Website credentials and settings
URL = os.getenv("URL")
LOGIN_URL = os.getenv("LOGIN_URL")
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
TOKEN = os.getenv("TOKEN")
SESSION_ID = os.getenv("SESSION_ID")

session = requests.Session()  # Persistent session
session.cookies.set("PHPSESSID", SESSION_ID)
last_login_attempt = 0
login_interval = 600  # 10 minutes in seconds

# Define the UTC+5 timezone
UTC_PLUS_5 = pytz.timezone("Asia/Yekaterinburg")

admins = [
    {'id': 1336348253, 'name': '@AlexCole_1', 'expiration_date': datetime(2025, 4, 10)},
    {'id': 7216398031, 'name': '@adam_griggs', 'expiration_date': datetime(2025, 4, 10)},
    {'id': 5015197070, 'name': '@Zach_Progressive', 'expiration_date': datetime(2025, 4, 10)},
    {'id': 1079500211, 'name': '@jaywesttt', 'expiration_date': datetime(2025, 4, 10)},
    {'id': 1018263860, 'name': '@click_onit', 'expiration_date': datetime(2025, 4, 20)},
    {'id': 1392048770, 'name': '@nickprogressivecarriers', 'expiration_date': datetime(2025, 4, 20)},
]

ADMIN_ID = {626105641, 487479968}  # Super admins
sent_load_ids = set()  # Track already sent Load IDs
previous_data = None  # Store last fetched data


def fetch_website_data():
    """Fetch data from the website and handle login if necessary."""
    global last_login_attempt, session

    current_time = time.time()
    if current_time - last_login_attempt < login_interval:
        logging.info("⏳ Skipping login due to rate limiting.")
    else:
        try:
            # Re-login only if needed
            logging.info("🔐 Logging in to the website...")
            login_data = {
                "email": EMAIL,
                "password": PASSWORD,
                "csrf_token": TOKEN,
            }
            login_response = session.post(LOGIN_URL, data=login_data)
            if login_response.text.strip() != "0":
                logging.error("❌ Login failed. Check credentials.")
                return None

            last_login_attempt = current_time
        except Exception as e:
            logging.error(f"❌ Error during login: {e}")
            return None

    try:
        # Fetch data
        response = session.get(URL)
        if "login" in response.url:  # Check if redirected to login page
            logging.info("Session expired. Re-logging in.")
            last_login_attempt = 0  # Force re-login
            return fetch_website_data()

        soup = BeautifulSoup(response.text, "html.parser")
        return str(soup.find('tbody'))
    except Exception as e:
        logging.error(f"❌ Error fetching website data: {e}")
        return None


def format_text_table(data):
    """Extract and format table data from HTML for display."""
    soup = BeautifulSoup(data, "html.parser")
    rows = soup.find_all("tr")
    formatted_data = []

    for row in rows:
        columns = row.find_all("td")
        if len(columns) < 6:
            continue

        load_id = columns[1].strong.text.strip()  # Extract Load ID
        distance = columns[2].text.strip()
        pickup_time = columns[3].text.strip()
        delivery_time = columns[4].text.strip()
        stops = [stop.text.strip() for stop in columns[5].find_all("li")]
        stops_text = "\n".join([f"   {i + 1}. {stop}" for i, stop in enumerate(stops)])

        message = (
            f"🚛 *Load ID:* {load_id}\n"
            f"📏 *Distance:* {distance} miles\n"
            f"⏳ *Pickup Time:* {pickup_time}\n"
            f"⏳ *Delivery Time:* {delivery_time}\n"
            f"📍 *Stops:*\n{stops_text}\n"
            "----------------------------------------"
        )

        formatted_data.append((load_id, message))  # Append tuple (load_id, message)

    return formatted_data


async def monitor_website():
    """Monitor the website every 15 seconds if monitoring is enabled."""
    global previous_data

    while True:
        logging.info("🔍 Checking website for updates...")
        current_data = fetch_website_data()

        if not current_data:
            logging.info("⚠️ No data retrieved from the website.")
        elif current_data != previous_data:
            logging.info("🚨 Website update detected! Sending notifications...")

            new_messages = format_text_table(current_data)
            logging.info(f"Formatted Messages: {new_messages}")

            for item in new_messages:
                if not isinstance(item, tuple) or len(item) != 2:
                    logging.error(f"❌ Unexpected data format: {item}")
                    continue

                load_id, msg = item

                if load_id not in sent_load_ids:
                    for admin in admins:
                        if admin["id"] in ADMIN_ID:
                            continue
                        try:
                            await bot.send_message(chat_id=admin["id"], text=msg, parse_mode="Markdown")
                            logging.info(f"✅ Sent update to admin {admin['id']}")
                        except Exception as e:
                            logging.error(f"❌ Error sending to {admin['id']}: {e}")
                    sent_load_ids.add(load_id)

            previous_data = current_data
        else:
            logging.info("✅ No new updates.")

        await asyncio.sleep(15)


async def set_default_commands(botsetter: Bot):
    """Set the default menu buttons in the Telegram bot."""
    commands = [
        types.BotCommand(command="start", description="Start the bot"),
    ]
    await botsetter.set_my_commands(commands)


async def notify_admins(error_message):
    """Notify all admins about a critical bot error."""
    for admin in admins:
        try:
            await bot.send_message(admin["id"], f"🚨 Bot Error:\n\n{error_message}")
        except Exception as e:
            logging.error(f"❌ Failed to notify admin {admin['id']}: {e}")


async def main():
    """Initialize the bot and start monitoring."""
    await set_default_commands(bot)  # ✅ Set menu here
    dp.include_router(router)

    # Start monitoring the website
    asyncio.create_task(monitor_website())

    while True:
        try:
            await dp.start_polling(bot)
        except TelegramNetworkError as e:
            logging.error(f"⚠️ Network error: {e}")
            await notify_admins(f"⚠️ Network error occurred: {e}")
            await asyncio.sleep(5)  # Wait before retrying
        except Exception as e:
            logging.error(f"❌ Unexpected error: {e}")
            await notify_admins(f"❌ Unexpected error:\n\n{e}")
            await asyncio.sleep(5)  # Wait before retrying


if __name__ == "__main__":
    asyncio.run(main())
