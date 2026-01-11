import discord
from discord import app_commands
from discord.ext import commands
import datetime

class Confess(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="صارحني", description="دز رسالة سرية مجهولة بدون ما احد يعرفك 🤫")
    @app_commands.describe(message="اكتب اعترافك او رسالتك هنا")
    async def confess(self, interaction: discord.Interaction, message: str):
        
        # 1. البحث عن القناة
        target_channel = discord.utils.get(interaction.guild.text_channels, name="صارحني")
        if not target_channel:
            target_channel = discord.utils.get(interaction.guild.text_channels, name="confessions")

        if target_channel:
            # ✅ حفظ الرسالة في الداشبورد (هنا التعديل الجديد)
            if hasattr(self.bot, 'confessions_list'):
                log_entry = {
                    'content': message,
                    'time': datetime.datetime.now().strftime("%I:%M %p"), # الوقت
                    'server': interaction.guild.name # اسم السيرفر
                }
                # نضيف الرسالة ببداية القائمة (عشان تطلع الجديدة اول شي)
                self.bot.confessions_list.insert(0, log_entry)

            # تصميم الرسالة للديسكورد
            embed = discord.Embed(
                title="💌 رسالة صراحة مجهولة",
                description=f"**الرسالة:**\n\n> {message}",
                color=0xff69b4,
                timestamp=datetime.datetime.now()
            )
            embed.set_footer(text="المرسل: مجهول (هوية محمية 🔒)")
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/4645/4645307.png")

            await target_channel.send(embed=embed)
            await interaction.response.send_message("✅ تم إرسال رسالتك بـ(سرية تامة). ولا يهمك!", ephemeral=True)
        
        else:
            await interaction.response.send_message("❌ ما لكيت قناة اسمها `صارحني` بالسيرفر!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Confess(bot))