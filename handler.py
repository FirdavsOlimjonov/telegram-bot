from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from database import is_admin, add_admin, remove_admin, get_all_admins

router = Router()
monitoring_task = None  # Placeholder for monitoring control


@router.message(Command("start"))
async def start_handler(message: Message):
    """Handles the /start command and sets up admin menu."""
    if await is_admin(message.from_user.id):
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="List Admins")],  # Fixed capitalization
            ],
            resize_keyboard=True
        )
        await message.answer("Welcome, Admin!", reply_markup=keyboard)
    else:
        await message.answer("Hello!")


@router.message(Command("addadmin"))
async def add_admin_handler(message: Message):
    """Handles the /addadmin command."""
    if not await is_admin(message.from_user.id):
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


@router.message(Command("removeadmin"))
async def remove_admin_handler(message: Message):
    """Handles the /removeadmin command."""
    if not await is_admin(message.from_user.id):
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
    if not await is_admin(message.from_user.id):
        await message.answer("You are not authorized to use this command.")
        return

    admins = await get_all_admins()
    if not admins:
        await message.answer("No admins found.")
    else:
        admin_list = "\n".join(f"🔹 {admin['name']} (ID: {admin['id']})" for admin in admins)
        await message.answer(f"📜 Current Admins:\n{admin_list}")
