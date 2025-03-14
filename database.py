import os
from datetime import datetime, timedelta, timezone

import asyncpg
import asyncio
import pytz
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Global database pool (initialized once)
pool = None
ADMIN_ID = {626105641, 487479968}

# Define UTC timezone
UTC = pytz.utc
pool_lock = asyncio.Lock()


# Initialize the database pool
async def create_pool():
    global pool
    async with pool_lock:
        if pool is None:
            try:
                pool = await asyncpg.create_pool(
                    DATABASE_URL,
                    min_size=1,
                    max_size=10,
                    timeout=60,
                    command_timeout=60,
                    max_inactive_connection_lifetime=300
                )
            except Exception as e:
                print(f"❌ Database pool creation failed: {e}")
                pool = None  # Prevent broken pool references


async def close_pool():
    global pool
    if pool:
        await pool.close()
        pool = None


# Initialize the database (Ensure table & default admin exists)
async def init_db():
    await create_pool()  # Ensure pool is created

    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id BIGINT PRIMARY KEY,
                name TEXT NOT NULL,
                expiration_date TIMESTAMP WITH TIME ZONE NOT NULL
            )
        """)

        # Ensure the default admin exists with an "unlimited" expiration date
        expiration_date = datetime(9999, 12, 31, tzinfo=timezone.utc)  # Ensure it's timezone-aware

        await conn.execute("""
            INSERT INTO admins (id, name, expiration_date) 
            VALUES ($1, $2, $3) 
            ON CONFLICT (id) DO NOTHING
        """, 626105641, "Firdavs Olimjonov", expiration_date)


# Check if a user is an admin and not expired
async def is_admin(user_id):
    if pool is None:
        await create_pool()  # Ensure pool exists

    async with pool.acquire() as conn:
        return await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM admins 
                WHERE id = $1 AND expiration_date > NOW()
            )
        """, user_id)


# Remove an admin
async def remove_admin(user_id):
    if pool is None:
        await create_pool()  # Ensure pool exists

    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM admins WHERE id = $1", user_id)


# Add a new admin with an expiration date (now + 1 month)
async def add_admin(user_id, name):
    if pool is None:
        await create_pool()  # Ensure pool exists

    if user_id in ADMIN_ID:
        expiration_date = datetime(9999, 12, 31)  # Unlimited expiration for special admin
    else:
        expiration_date = datetime.now(UTC) + timedelta(days=30)  # Set expiration 1 month from now

    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO admins (id, name, expiration_date) 
            VALUES ($1, $2, $3)
            ON CONFLICT (id) 
            DO UPDATE SET expiration_date = $3
        """, user_id, name, expiration_date)


# Get all active admins (not expired)
async def get_all_admins():
    if pool is None:
        await create_pool()  # Ensure pool exists

    async with pool.acquire() as conn:
        result = await conn.fetch("""
            SELECT id, name, expiration_date 
            FROM admins 
            WHERE expiration_date >= NOW()
        """)
        return [{"id": record["id"], "name": record["name"], "expiration_date": record["expiration_date"]} for record in
                result]


# Get admin details by user ID
async def get_admin_by_id(user_id):
    if pool is None:
        await create_pool()  # Ensure pool exists

    async with pool.acquire() as conn:
        result = await conn.fetchrow("""
            SELECT id, name, expiration_date 
            FROM admins 
            WHERE id = $1
        """, user_id)
        if result:
            return {
                "id": result["id"],
                "name": result["name"],
                "expiration_date": result["expiration_date"]
            }
        else:
            return None  # Return None if the admin doesn't exist


# Extend admin expiration (Only ADMIN_ID can use this)
async def update_admin_expiration(user_id):
    if pool is None:
        await create_pool()  # Ensure pool exists

    new_expiration = datetime.now(UTC) + timedelta(days=30)  # Extend by 1 month
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE admins 
            SET expiration_date = $1 
            WHERE id = $2
        """, new_expiration, user_id)

    return f"🔄 Admin ID {user_id} expiration extended to {new_expiration.strftime('%Y-%m-%d')}"

#
# # Check expired admins and notify them
# async def check_expired_admins(bot):
#     async with pool.acquire() as conn:
#         now = datetime.now(UTC)
#         warning_time = now + timedelta(days=3)  # Warn 3 days before expiration
#
#         # Find admins whose expiration date is within the next 3 days
#         warning_admins = await conn.fetch("""
#             SELECT id, name, expiration_date
#             FROM admins
#             WHERE expiration_date BETWEEN NOW() AND $1
#         """, warning_time)
#
#         for record in warning_admins:
#             admin_id = record["id"]
#             expiration_date = record["expiration_date"].strftime("%Y-%m-%d %H:%M:%S")
#
#             try:
#                 await bot.send_message(
#                     admin_id,
#                     f"⚠️ Your admin access will expire on {expiration_date}. Please contact support to renew."
#                 )
#             except Exception as e:
#                 print(f"Error sending expiration warning to {admin_id}: {e}")
#
#         # Find expired admins
#         expired_admins = await conn.fetch("""
#             SELECT id, name, expiration_date
#             FROM admins
#             WHERE expiration_date < NOW()
#         """)
#
#         if expired_admins:
#             expired_list = "\n".join(
#                 [
#                     f"👤 {record['name']} (ID: {record['id']}) - Expired on {record['expiration_date'].strftime('%Y-%m-%d %H:%M:%S')}"
#                     for record in expired_admins]
#             )
#
#             message = f"🚨 The following admins have expired:\n\n{expired_list}"
#
#             try:
#                 for admId in ADMIN_ID:
#                     await bot.send_message(admId, message)  # Notify main admin
#             except Exception as e:
#                 print(f"Error sending expired admin list: {e}")
