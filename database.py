import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Global database pool (initialized once)
pool = None


# Initialize the database pool
async def create_pool():
    global pool
    if pool is None:  # Prevent duplicate pools
        pool = await asyncpg.create_pool(DATABASE_URL)


# Initialize the database (Ensure table & default admin exists)
async def init_db():
    await create_pool()  # Ensure pool is created
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id BIGINT PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)
        # Ensure the default admin exists
        await conn.execute("""
            INSERT INTO admins (id, name) VALUES ($1, $2) 
            ON CONFLICT (id) DO NOTHING
        """, 626105641, "Firdavs Olimjonov")


# Check if a user is an admin
async def is_admin(user_id):
    async with pool.acquire() as conn:
        result = await conn.fetchval("SELECT id FROM admins WHERE id = $1", user_id)
        return result is not None  # Return True if admin exists


# Remove an admin
async def remove_admin(user_id):
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM admins WHERE id = $1", user_id)


# Add a new admin
async def add_admin(user_id, name):
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO admins (id, name) VALUES ($1, $2)
            ON CONFLICT (id) DO NOTHING
        """, user_id, name)


# Get all admins
async def get_all_admins():
    async with pool.acquire() as conn:
        result = await conn.fetch("SELECT id, name FROM admins")
        return [{"id": record["id"], "name": record["name"]} for record in result]
