from datetime import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

router = Router()
monitoring_task = None  # Placeholder for monitoring control

ADMIN_ID = {626105641, 487479968}

admins = [
    {'id': 1336348253, 'name': '@AlexCole_1', 'expiration_date': datetime(2025, 4, 10)},
    {'id': 7216398031, 'name': '@adam_griggs', 'expiration_date': datetime(2025, 4, 10)},
    {'id': 5015197070, 'name': '@Zach_Progressive', 'expiration_date': datetime(2025, 4, 10)},
    {'id': 1079500211, 'name': '@jaywesttt', 'expiration_date': datetime(2025, 4, 10)},
    {'id': 1018263860, 'name': '@click_onit', 'expiration_date': datetime(2025, 4, 20)},
    {'id': 1392048770, 'name': '@nickprogressivecarriers', 'expiration_date': datetime(2025, 4, 20)},
]


@router.message(Command("start"))
async def start_handler(message: Message):
    """Handles the /start command and sets up admin menu."""
    if message.from_user.id in ADMIN_ID:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="List Admins")],
                [KeyboardButton(text="/addadmin")],
                [KeyboardButton(text="/removeadmin")],
                [KeyboardButton(text="/updateadmin")],
            ],
            resize_keyboard=True
        )
        await message.answer("Welcome, Admin!", reply_markup=keyboard)
    else:
        admin = next((a for a in admins if a['id'] == message.from_user.id), None)
        if admin:
            await message.answer(
                f"Hello {admin['name']} (ID: {admin['id']} expiration date: {admin['expiration_date'].strftime('%Y-%m-%d')})"
            )
        else:
            await message.answer("You are not an admin.")


@router.message(Command("addadmin"))
async def add_admin_handler(message: Message):
    """Handles the /addadmin command."""
    if message.from_user.id not in ADMIN_ID:
        await message.answer("You are not authorized to use this command.")
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("Usage: /addadmin <user_id> <name>")
        return

    new_admin_id = int(args[1])
    new_admin_name = args[2]
    expiration_date = datetime(2025, 12, 31)

    if any(admin['id'] == new_admin_id for admin in admins):
        await message.answer(f"⚠️ User {new_admin_id} is already an admin.")
        return

    admins.append({'id': new_admin_id, 'name': new_admin_name, 'expiration_date': expiration_date})
    await message.answer(f"✅ User {new_admin_id} ('{new_admin_name}') added as admin.")


@router.message(Command("removeadmin"))
async def remove_admin_handler(message: Message):
    """Handles the /removeadmin command."""
    if message.from_user.id not in ADMIN_ID:
        await message.answer("You are not authorized to use this command.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("Usage: /removeadmin <user_id>")
        return

    admin_id = int(args[1])

    # Prevent removing the last admin
    if len(admins) == 1 and any(admin['id'] == admin_id for admin in admins):
        await message.answer("❌ You cannot remove the last admin!")
        return

    # Remove the admin
    for admin in admins:
        if admin["id"] == admin_id:
            admins.remove(admin)
            await message.answer(f"✅ User {admin_id} removed as admin.")
            return

    await message.answer(f"⚠️ User {admin_id} not found in the admin list.")


@router.message(lambda message: message.text.lower().strip() == "list admins")
async def list_admins_handler(message: Message):
    """Handles the "List Admins" button or command."""
    if message.from_user.id not in ADMIN_ID:
        await message.answer("You are not authorized to use this command.")
        return

    if not admins:
        await message.answer("No admins found.")
    else:
        admin_list = "\n".join(
            f"🔹 {admin['name']} (ID: {admin['id']} expiration date: {admin['expiration_date'].strftime('%Y-%m-%d')})"
            for admin in admins
        )
        await message.answer(f"📜 Current Admins:\n{admin_list}")
