import discord
from discord.ext import commands
import json
import os

class AutoReply(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_path = 'data/auto_reply.json'
        self.replies = self.load_replies()

    def load_replies(self):
        if not os.path.exists(self.data_path): return {}
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return {}

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: return

        # تنظيف الرسالة (نشيل المسافات الزايدة)
        content = message.content.strip()
        
        # البحث عن رد (مطابقة تامة للكلمة)
        # ملاحظة: تكدرين تسويها if key in content للبحث الجزئي
        if content in self.replies:
            await message.reply(self.replies[content], mention_author=False)
            
    # أمر لتحديث الردود من الداشبورد بدون ريستارت
    @commands.command(hidden=True)
    @commands.is_owner()
    async def reload_replies(self, ctx):
        self.replies = self.load_replies()
        await ctx.send("✅ تم تحديث الذاكرة!")

async def setup(bot):
    await bot.add_cog(AutoReply(bot))