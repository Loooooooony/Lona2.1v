import discord
from discord.ext import commands, tasks
import json
import datetime
import pytz
import asyncio

# 🔥 الروابط السريعة (ضد الحظر وضد صرف المعالج)
READERS = {
    "mp3quran": {
        "name": "إذاعة القرآن العامة", 
        "url": "http://stream.radiojar.com/4wqre23fytzuv"
    },
    "abdulbasit": {
        "name": "عبدالباسط عبدالصمد (مجود)", 
        "url": "https://qurango.net/radio/abdulbasit_mojawwad"
    },
    "afasi": {
        "name": "مشاري العفاسي", 
        "url": "https://qurango.net/radio/mishary_alafasi"
    },
    "maher": {
        "name": "ماهر المعيقلي", 
        "url": "https://qurango.net/radio/maher_al_muaiqly"
    },
    "sudais": {
        "name": "عبدالرحمن السديس", 
        "url": "https://qurango.net/radio/abdulrahman_alsudaes"
    },
    "shuraim": {
        "name": "سعود الشريم", 
        "url": "https://qurango.net/radio/saud_alshuraim"
    },
    "yasser": {
        "name": "ياسر الدوسري", 
        "url": "https://qurango.net/radio/yasser_aldosari"
    }
}

class IslamicSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_path = 'data/islamic_config.json'
        self.baghdad_tz = pytz.timezone('Asia/Baghdad')
        self.current_stream_url = None 
        self.islamic_loop.start()

    def load_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return {}

    # خلينا الفحص كل دقيقة، كافي وزايد
    @tasks.loop(seconds=60) 
    async def islamic_loop(self):
        config = self.load_config()
        
        # اذا طفوه من الداشبورد، نفصل ونرتاح
        if not config.get('enabled', False): 
            for vc in self.bot.voice_clients:
                await vc.disconnect()
            self.current_stream_url = None
            return

        now = datetime.datetime.now(self.baghdad_tz)

        # 1. الأذكار (ما تصرف شي)
        if config.get('text_channel_id'):
            await self.handle_azkar(config, now)

        # 2. الراديو (المهمة الصعبة)
        if config.get('voice_channel_id'):
            await self.handle_radio(config)

    async def handle_azkar(self, config, now):
        try:
            channel = self.bot.get_channel(int(config['text_channel_id']))
            if not channel: return
            if now.second > 10: return 

            if config.get('azkar_sabah', True) and now.hour == 8 and now.minute == 0:
                await channel.send("🌅 **أذكار الصباح**\nاللهم بك أصبحنا وبك أمسينا وبك نحيا وبك نموت وإليك النشور.")
            elif config.get('azkar_masa', True) and now.hour == 17 and now.minute == 0:
                await channel.send("🌇 **أذكار المساء**\nأمسينَا وأمسَى الملكُ لله، والحمدُ لله، لا إلهَ إلاَّ اللهُ وحدَهُ لا شريكَ لهُ.")
            elif config.get('friday_kahf', True) and now.weekday() == 4 and now.hour == 10 and now.minute == 0:
                await channel.send("🕌 **جمعة مباركة!**\nلا تنسوا قراءة سورة الكهف والصلاة على النبي ﷺ.")
        except: pass

    async def handle_radio(self, config):
        try:
            channel_id = int(config['voice_channel_id'])
            voice_channel = self.bot.get_channel(channel_id)
            if not voice_channel: return

            voice_client = discord.utils.get(self.bot.voice_clients, guild=voice_channel.guild)

            # اتصال ذكي (Deaf) لتقليل البيانات
            if not voice_client:
                voice_client = await voice_channel.connect()
                await voice_channel.guild.change_voice_state(channel=voice_channel, self_deaf=True)
            elif voice_client.channel.id != channel_id:
                await voice_client.move_to(voice_channel)

            selected_reader = config.get('reader', 'mp3quran')
            stream_data = READERS.get(selected_reader, READERS['mp3quran'])
            target_url = stream_data['url']

            # تشغيل فقط اذا لازم
            if not voice_client.is_playing() or self.current_stream_url != target_url:
                if voice_client.is_playing(): voice_client.stop()
                
                # 🔥🔥🔥 إعدادات توفير المعالج (Eco Mode) 🔥🔥🔥
                ffmpeg_opts = {
                    # تقليل محاولات الاتصال المفرطة
                    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin',
                    # -threads 1: يجبره يستخدم نواة وحدة بس!
                    # -ar 48000 -ac 2: يجهز الصوت لديسكورد مباشرة بدون معالجة إضافية
                    'options': '-vn -threads 1 -ar 48000 -ac 2 -b:a 96k -user_agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"'
                }

                voice_client.play(
                    discord.FFmpegPCMAudio(target_url, **ffmpeg_opts),
                    after=lambda e: self.on_play_error(e)
                )
                
                self.current_stream_url = target_url
                await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f"{stream_data['name']}"))

        except Exception as e:
            print(f"⚠️ Radio Logic Error: {e}")
            # انتظار بسيط في حالة الخطأ عشان ما يضرب اللوب
            await asyncio.sleep(5)

    def on_play_error(self, error):
        if error:
            print(f"❌ Playback Error: {error}")
            self.current_stream_url = None 

    @islamic_loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(IslamicSystem(bot))