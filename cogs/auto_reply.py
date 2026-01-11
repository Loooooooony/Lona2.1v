import discord
from discord.ext import commands
import json
import os
import sys

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.data_manager import get_guild_file

class AutoReply(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Memory cache: {guild_id: {trigger: response}}
        self.replies_cache = {}

    def get_config_path(self, guild_id):
        return get_guild_file(guild_id, 'auto_reply.json')

    def load_replies(self, guild_id):
        path = self.get_config_path(guild_id)
        if not os.path.exists(path): return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return {}

    def update_guild_replies(self, guild_id, replies):
        """Called from dashboard to update memory cache instantly."""
        self.replies_cache[str(guild_id)] = replies

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild: return

        guild_id = str(message.guild.id)

        # Load from cache or file if not present
        if guild_id not in self.replies_cache:
            self.replies_cache[guild_id] = self.load_replies(message.guild.id)

        replies = self.replies_cache[guild_id]

        # تنظيف الرسالة (نشيل المسافات الزايدة)
        content = message.content.strip()

        # البحث عن رد (مطابقة تامة للكلمة)
        if content in replies:
            await message.reply(replies[content], mention_author=False)

async def setup(bot):
    await bot.add_cog(AutoReply(bot))
