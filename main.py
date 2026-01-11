import dashboard
import discord
from discord.ext import commands
import os
import asyncio
import logging
from dotenv import load_dotenv

# إعداد اللوق (حتى نعرف ليش يطفي)
logging.basicConfig(level=logging.INFO)

# تحميل التوكن
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# إعدادات البوت
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    print('------')
    print('Bot is Online and Ready! 🚀')
    # تغيير الحالة للتأكد من العمل
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Lona Dashboard"))

# دالة التحميل
async def load_extensions():
    if os.path.exists('./cogs'):
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await bot.load_extension(f'cogs.{filename[:-3]}')
                    print(f'✅ تم تحميل: {filename}')
                except Exception as e:
                    print(f'❌ فشل تحميل {filename}: {e}')

async def main():
    if not TOKEN:
        print("Error: TOKEN not found in .env file!")
        return

    # قائمة الاعترافات (مهمة للداشبورد)
    bot.confessions_list = []
    
    async with bot:
        await load_extensions()
        
        # 🔥 التعديل الجذري: تشغيل الداشبورد والبوت سوية بطريقة صحيحة
        # هذا يمنع البوت من أن يوقف الداشبورد والعكس
        await asyncio.gather(
            bot.start(TOKEN),            # تشغيل البوت
            dashboard.run_server(bot)    # تشغيل الداشبورد
        )

if __name__ == '__main__':
    try:
        # حلقة تمنع السكربت من التوقف
        asyncio.run(main())
    except KeyboardInterrupt:
        # توقف يدوي (CTRL+C)
        print("🛑 تم إيقاف البوت يدوياً.")
    except Exception as e:
        # أي خطأ ثاني
        print(f"⚠️ حدث خطأ غير متوقع وأدى لإيقاف البوت: {e}")