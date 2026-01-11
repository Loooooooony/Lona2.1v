import discord
from discord.ext import commands
import random
import datetime
# نستدعي قائمة الخيرة من ملف الداتا اللي سويناه فوق
from utils.khira_data import KHIRA_LIST

class Khira(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="خيرة", aliases=["khira", "فال", "توقعات"])
    async def khira(self, ctx):
        """
        أمر يعطي خيرة عشوائية ممزوجة بالتنمر وعلم النفس والتحشيش.
        """
        # اختيار رد عشوائي
        fortune = random.choice(KHIRA_LIST)
        
        # تنسيق الرسالة بشكل مرتب (Embed)
        embed = discord.Embed(
            title="🔮 خيرة أم عباس الروحانية (للتحطيم النفسي)", 
            description=f"**يا {ctx.author.name}.. صفيت النية وفتحت الفال:**\n\n📜 **\"{fortune}\"**", 
            color=0x9b59b6, # لون بنفسجي
            timestamp=datetime.datetime.now()
        )
        
        
        # تذييل الرسالة
        embed.set_footer(text="خيرة ام عباس درجة اولى ما تغلط")
        
        await ctx.send(embed=embed)

# دالة التحميل
async def setup(bot):
    await bot.add_cog(Khira(bot))