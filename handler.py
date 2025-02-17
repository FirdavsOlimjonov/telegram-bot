from datetime import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from database import add_admin, remove_admin, get_all_admins, update_admin_expiration, get_admin_by_id

router = Router()
monitoring_task = None  # Placeholder for monitoring control

ADMIN_ID = {626105641, 487479968}


# @router.message(Command("stopworld"))
# async def start_handler(message: Message):
#     """Handles the /stopworld command and sets up admin menu."""
#     if message.from_user.id in ADMIN_ID:
#         exit_program()


@router.message(Command("start"))
async def start_handler(message: Message):
    """Handles the /start command and sets up admin menu."""
    if message.from_user.id in ADMIN_ID:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="List Admins")],  # Fixed capitalization
                [KeyboardButton(text="/addadmin")],  # Fixed capitalization
                [KeyboardButton(text="/removeadmin")],  # Fixed capitalization
                [KeyboardButton(text="/updateadmin")],  # Fixed capitalization
            ],
            resize_keyboard=True
        )
        await message.answer("Welcome, Admin!", reply_markup=keyboard)
    else:
        admin = await get_admin_by_id(message.from_user.id)  # Await the coroutine
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

    await add_admin(new_admin_id, new_admin_name)
    await message.answer(f"✅ User {new_admin_id} ('{new_admin_name}') added as admin.")


@router.message(Command("updateadmin"))
async def handle_update_admin(message: Message):
    if message.from_user.id not in ADMIN_ID:
        await message.answer("You are not authorized to use this command.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("⚠️ Usage: /updateadmin <user_id>")
        return

    user_id = int(args[1])

    response = await update_admin_expiration(user_id)
    await message.answer(response)


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

    # Get list of admin IDs
    admins = await get_all_admins()
    admin_ids = [admin["id"] for admin in admins]

    if len(admin_ids) == 1 and admin_id in admin_ids:
        await message.answer("❌ You cannot remove the last admin!")
        return

    await remove_admin(admin_id)
    await message.answer(f"✅ User {admin_id} removed as admin.")


@router.message(lambda message: message.text.lower().strip() == "list admins")
async def list_admins_handler(message: Message):
    """Handles the "List Admins" button or command."""
    if message.from_user.id not in ADMIN_ID:
        await message.answer("You are not authorized to use this command.")
        return

    admins = await get_all_admins()
    if not admins:
        await message.answer("No admins found.")
    else:
        admin_list = "\n".join(
            f"🔹 {admin['name']} (ID: {admin['id']} expiration date: {admin['expiration_date'].strftime('%Y-%m-%d')})"
            for admin in admins
        )
        await message.answer(f"📜 Current Admins:\n{admin_list}")
