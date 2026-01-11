import aiomysql
import os
import asyncio
import logging

class Database:
    def __init__(self):
        self.pool = None
        self.host = os.getenv('DB_HOST')
        self.user = os.getenv('DB_USER')
        self.password = os.getenv('DB_PASSWORD')
        self.db_name = os.getenv('DB_NAME')

    async def connect(self):
        if not self.pool:
            try:
                self.pool = await aiomysql.create_pool(
                    host=self.host,
                    user=self.user,
                    password=self.password,
                    db=self.db_name,
                    autocommit=True
                )
                print("✅ Database connected successfully.")
                await self.init_tables()
            except Exception as e:
                print(f"❌ Database connection failed: {e}")

    async def execute(self, query, *args):
        if not self.pool: await self.connect()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, args)
                return cur.lastrowid

    async def fetch(self, query, *args):
        if not self.pool: await self.connect()
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, args)
                return await cur.fetchall()

    async def fetchrow(self, query, *args):
        if not self.pool: await self.connect()
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, args)
                return await cur.fetchone()

    async def init_tables(self):
        queries = [
            """
            CREATE TABLE IF NOT EXISTS ticket_configs (
                guild_id BIGINT PRIMARY KEY,
                support_role_id BIGINT,
                admin_role_id BIGINT,
                category_id BIGINT,
                log_channel_id BIGINT,
                transcript_channel_id BIGINT,
                naming_format VARCHAR(255) DEFAULT 'ticket-{user}',
                staff_shift_active BOOLEAN DEFAULT TRUE,
                require_shift BOOLEAN DEFAULT FALSE,
                allow_voice BOOLEAN DEFAULT TRUE,
                allow_escalation BOOLEAN DEFAULT TRUE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS ticket_panels (
                message_id BIGINT PRIMARY KEY,
                guild_id BIGINT,
                channel_id BIGINT,
                embed_title VARCHAR(255),
                embed_desc TEXT,
                embed_color VARCHAR(10),
                button_label VARCHAR(50),
                button_emoji VARCHAR(50),
                button_color VARCHAR(20)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS active_tickets (
                channel_id BIGINT PRIMARY KEY,
                guild_id BIGINT,
                user_id BIGINT,
                claimed_by BIGINT DEFAULT NULL,
                status VARCHAR(20) DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                rating INT DEFAULT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS emoji_settings (
                guild_id BIGINT PRIMARY KEY,
                target_channel_id BIGINT,
                allow_external BOOLEAN DEFAULT TRUE,
                only_emojis_mode BOOLEAN DEFAULT FALSE,
                enabled BOOLEAN DEFAULT FALSE
            )
            """
        ]

        for q in queries:
            await self.execute(q)
        print("✅ Database tables initialized.")

# Global DB Instance
db = Database()
