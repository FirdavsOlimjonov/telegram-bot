import asyncio
import logging
from datetime import datetime

import pytz
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.exceptions import TelegramNetworkError
from aiogram.filters import Command
from aiogram.types import Message
from bs4 import BeautifulSoup

from config import TOKEN
from database import get_all_admins, init_db, is_admin, check_expired_admins
from handler import router

# Enable logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Website URL to monitor
URL = "https://truckmind.com/LoadBoard?type=load"

# Define the UTC+5 timezone
UTC = pytz.utc
UTC_PLUS_5 = pytz.timezone("Asia/Yekaterinburg")  # Example for UTC+5

# Set to track already sent Load IDs
sent_load_ids = set()
previous_data = None


async def fetch_website_data():
    """Fetch the latest data from the website."""
    try:
        response = requests.get(URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table")
        return str(table)
    except Exception as e:
        logging.error(f"Error fetching website data: {e}")
        return None


def format_text_table(data):
    """Extract and format table data into a readable format with UTC+5 conversion."""
    soup = BeautifulSoup(data, "html.parser")
    rows = soup.select("#tbl_loadboard tr")
    messages = []

    for row in rows:
        columns = row.find_all("td")
        if columns:
            load_id = columns[0].text.strip()
            tender_id = columns[1].text.strip()
            if load_id in sent_load_ids:
                continue  # Skip already sent loads

            from_location = columns[2].text.strip()
            to_location = columns[3].text.strip()
            date = columns[4].text.strip()
            time = columns[5].text.strip()
            expiration_td = columns[6]  # The expiration column
            status = columns[7].text.strip()

            # Extract expiration time from `data-date` attribute
            expiration_utc = expiration_td.get("data-date", "").strip()

            # Convert expiration time to UTC+5
            if expiration_utc:
                try:
                    exp_datetime = datetime.strptime(expiration_utc, "%Y-%m-%dT%H:%M:%S")  # Parse ISO format
                    exp_datetime = UTC.localize(exp_datetime).astimezone(UTC_PLUS_5)  # Convert timezone
                    expiration = exp_datetime.strftime("%Y-%m-%d %H:%M:%S")  # Format
                except ValueError:
                    expiration = "Invalid Date Format"
            else:
                expiration = "N/A"

            # Extract the "Place Bid" link
            link_tag = row.find("a", class_="btn btn-primary btn-sm")
            load_link = link_tag["href"] if link_tag else "#"

            full_url = f"https://truckmind.com/{load_link}"

            message = (
                f"*Load ID:* [{load_id}]\n"
                f"*Ternder ID:* {tender_id}\n"
                f"*From:* {from_location}\n"
                f"*To:* {to_location}\n"
                f"*Date:* {date}\n"
                f"*Time:* {time}\n"
                f"*Expiration (UTC+5):* {expiration}\n"
                f"*Status:* {status}\n"
                # f"🔗 [View Load]({full_url})\n"
                f"---------------------"
            )
            messages.append((load_id, message))

    return messages


monitoring_task = None  # Global variable to store the task


async def monitor_website():
    """Monitor the website every 10 seconds if monitoring is enabled."""
    global previous_data

    while True:
        logging.info("🔍 Checking website for updates...")
        current_data = await fetch_website_data()

        if not current_data:
            logging.info("⚠️ No data retrieved from the website.")
        elif current_data != previous_data:
            logging.info("🚨 Website update detected! Sending notifications...")

            admins = await get_all_admins()
            admin_ids = [admin['id'] for admin in admins]

            new_messages = format_text_table(current_data)

            for load_id, msg in new_messages:
                if load_id not in sent_load_ids:  # Avoid duplicates
                    for admin_id in admin_ids:
                        try:
                            await bot.send_message(chat_id=admin_id, text=msg, parse_mode="Markdown")
                            logging.info(f"✅ Sent update to admin {admin_id}")
                        except Exception as e:
                            logging.error(f"❌ Error sending to {admin_id}: {e}")

                    sent_load_ids.add(load_id)  # Mark as sent

            previous_data = current_data  # Update stored data
        else:
            logging.info("✅ No new updates.")

        await asyncio.sleep(10)  # Wait 10 seconds before checking again


# @dp.message(Command("startmonitoring"))
# async def start_monitoring_handler(message: Message):
#     global monitoring_task, monitoring_enabled
#
#     if not await is_admin(message.from_user.id):
#         await message.answer("You are not authorized to use this command.")
#         return
#
#     if monitoring_task is None:
#         monitoring_enabled = True
#         monitoring_task = asyncio.create_task(monitor_website())  # ✅ Start monitoring
#         await message.answer("✅ Monitoring started!")
#     else:
#         await message.answer("⚠️ Monitoring is already running.")
#
#
# @dp.message(Command("stopmonitoring"))
# async def stop_monitoring_handler(message: Message):
#     global monitoring_task, monitoring_enabled
#
#     if not await is_admin(message.from_user.id):
#         await message.answer("You are not authorized to use this command.")
#         return
#
#     if monitoring_task:
#         monitoring_enabled = False  # ✅ Stop the loop in `monitor_website`
#         monitoring_task.cancel()  # ✅ Cancel the asyncio task
#         monitoring_task = None
#         await message.answer("🛑 Monitoring stopped.")
#     else:
#         await message.answer("⚠️ Monitoring is not running.")


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


async def scheduled_admin_check():
    while True:
        await check_expired_admins(bot)
        await asyncio.sleep(86400)  # 24 hours


async def main():
    """Initialize the bot, database, and start monitoring."""
    await init_db()
    await set_default_commands(bot)  # ✅ Set menu here
    dp.include_router(router)

    asyncio.create_task(scheduled_admin_check())  # Start expiration checks

    # # Start monitoring the website
    # asyncio.create_task(monitor_website())

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
