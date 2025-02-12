import asyncio
import logging

import pytz
import requests
from aiogram.filters import Command
from aiogram import Bot, Dispatcher, types
from aiogram.exceptions import TelegramNetworkError
from aiogram.types import Message
from bs4 import BeautifulSoup

from config import TOKEN
from database import get_all_admins, init_db
from handler import router

# Enable logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Website URL to monitor
URL = "https://logistics-edi.azurewebsites.net"
LOGIN_URL = URL + "/php/login.php"
EMAIL = "rrood@mercer-trans.com"
PASSWORD = "Dispatch24!"
TOKEN = "eXh4OHFjaThuOTlaakM2WHpyUDJPeVlUM0lKMy1zNjJnYzd0TkpHS0VEWXxJVmQ2NFVxNnhNTXwxNzM5MzY1MjI2"
SESSION_ID = "5d4f7f2b3b9d9d23fa544aef2fb6f7bc"

# Define the UTC+5 timezone
UTC = pytz.utc
UTC_PLUS_5 = pytz.timezone("Asia/Yekaterinburg")  # Example for UTC+5

# Set to track already sent Load IDs
sent_load_ids = set()
previous_data = None
ADMIN_ID = {626105641, 487479968}


def fetch_website_data():
    """Fetch the latest data from the website."""
    session = requests.Session()
    session.cookies.set("PHPSESSID", SESSION_ID)

    login_data = {
        "email": EMAIL,
        "password": PASSWORD,
        "csrf_token": "",
    }

    response = session.post(LOGIN_URL, data=login_data)

    if response.text.strip() == "0":
        protected_response = session.get(URL)
        soup = BeautifulSoup(protected_response.text, "html.parser")
        return str(soup.find('tbody'))
    else:
        page = session.get(URL + '/login')
        soup = BeautifulSoup(page.text, "html.parser")
        token = soup.find('meta', {'name': 'csrf_token'}).get('content', '')
        login_data["csrf_token"] = token
        response = session.post(LOGIN_URL, data=login_data)

        if response.text.strip() == "0":
            protected_response = session.get(URL)
            soup = BeautifulSoup(protected_response.text, "html.parser")
            return str(soup.find('tbody'))
        else:
            logging.error("Login failed. Check credentials or session ID.")
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

            admins = await get_all_admins()
            admin_ids = [admin['id'] for admin in admins]

            new_messages = format_text_table(current_data)
            logging.info(f"Formatted Messages: {new_messages}")

            for item in new_messages:
                if not isinstance(item, tuple) or len(item) != 2:
                    logging.error(f"❌ Unexpected data format: {item}")
                    continue

                load_id, msg = item
                # logging.info(f"Processing Load ID: {load_id}")

                if load_id not in sent_load_ids:
                    for admin_id in admin_ids:
                        if admin_id in ADMIN_ID:
                            continue
                        try:
                            await bot.send_message(chat_id=admin_id, text=msg, parse_mode="Markdown")
                            logging.info(f"✅ Sent update to admin {admin_id}")
                        except Exception as e:
                            logging.error(f"❌ Error sending to {admin_id}: {e}")
                    sent_load_ids.add(load_id)

            previous_data = current_data
        else:
            logging.info("✅ No new updates.")

        await asyncio.sleep(15)


async def set_default_commands(botsetter: Bot):
    """Set the default menu buttons in the Telegram bot."""
    commands = [
        types.BotCommand(command="start", description="Start the bot"),
        # types.BotCommand(command="stop", description="Stop the bot"),
        # types.BotCommand(command="startmonitoring", description="Start the monitoring site"),
        # types.BotCommand(command="stopmonitoring", description="Stop the monitoring site"),
    ]
    await botsetter.set_my_commands(commands)


async def notify_admins(error_message):
    """Notify all admins about a critical bot error."""
    admins = await get_all_admins()
    admin_ids = [admin['id'] for admin in admins]

    for admin_id in admin_ids:
        try:
            await bot.send_message(admin_id, f"🚨 Bot Error:\n\n{error_message}")
        except Exception as e:
            logging.error(f"❌ Failed to notify admin {admin_id}: {e}")


# async def scheduled_admin_check():
#     while True:
#         await check_expired_admins(bot)
#         await asyncio.sleep(86400)  # 24 hours


# def exit_program():
#     print("Exiting the program...")
#     sys.exit(0)


# @router.message(Command("clear"))
# async def remove_admin_handler(message: Message):
#     """Handles the /clear command."""
#     if message.from_user.id not in ADMIN_ID:
#         await message.answer("You are not authorized to use this command.")
#         return
#
#     sent_load_ids = set()


async def main():
    """Initialize the bot, database, and start monitoring."""
    await init_db()
    await set_default_commands(bot)  # ✅ Set menu here
    dp.include_router(router)

    # asyncio.create_task(scheduled_admin_check())  # Start expiration checks

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
