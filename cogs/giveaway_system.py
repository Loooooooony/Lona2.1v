import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
import asyncio
import json
import random
import datetime
import os
import sys

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.data_manager import get_guild_file

# --- 🔘 زر الانضمام الذكي ---
class JoinButton(Button):
    def __init__(self, bot, requirements, guild_id):
        super().__init__(label="🎉 انضمام", style=discord.ButtonStyle.primary, custom_id="join_giveaway_btn")
        self.bot = bot
        self.requirements = requirements
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        # 1. التحقق: هل القيف اوي منتهي؟
        view: GiveawayView = self.view
        if view.ended:
            return await interaction.response.send_message("❌ انتهى هذا القيف اوي!", ephemeral=True)

        user = interaction.user
        reqs = self.requirements
        
        # --- 🛡️ فحص الشروط (Logic) 🛡️ ---

        # A. رتبة التجاوز (VIP Bypass) - اذا عنده يعبر كلشي
        bypass_id = reqs.get('bypass_role_id')
        has_bypass = False
        if bypass_id and any(r.id == int(bypass_id) for r in user.roles):
            has_bypass = True

        if not has_bypass:
            # B. القائمة السوداء (Blacklist)
            blacklist_id = reqs.get('blacklist_role_id')
            if blacklist_id and any(r.id == int(blacklist_id) for r in user.roles):
                return await interaction.response.send_message("⛔ عذراً، أنت ممنوع من المشاركة (Blacklisted)!", ephemeral=True)

            # C. الرتبة المطلوبة
            req_role_id = reqs.get('req_role_id')
            if req_role_id and not any(r.id == int(req_role_id) for r in user.roles):
                return await interaction.response.send_message(f"❌ تحتاج رتبة <@&{req_role_id}> للمشاركة!", ephemeral=True)

            # D. التحقق من الفويس (وقت أو تواجد)
            req_voice_min = int(reqs.get('req_voice_minutes', 0) or 0)
            if req_voice_min > 0 or reqs.get('req_voice'): # اذا مطلوب فويس
                if not user.voice:
                    msg = "❌ يجب أن تكون داخل **روم صوتي** للمشاركة!"
                    if req_voice_min > 0:
                        msg += f"\n⏳ (المطلوب: البقاء لمدة {req_voice_min} دقيقة)"
                    return await interaction.response.send_message(msg, ephemeral=True)

            # E. عمر الحساب (Account Age)
            min_acc_age = int(reqs.get('min_account_age', 0) or 0)
            if min_acc_age > 0:
                # نحسب الفرق بالأيام
                acc_age = (datetime.datetime.now(datetime.timezone.utc) - user.created_at).days
                if acc_age < min_acc_age:
                    return await interaction.response.send_message(f"❌ حسابك جديد جداً! يجب أن يكون عمره {min_acc_age} يوم.", ephemeral=True)

            # F. مدة دخول السيرفر (Server Join Age)
            min_srv_age = int(reqs.get('min_server_age', 0) or 0)
            if min_srv_age > 0:
                srv_age = (datetime.datetime.now(datetime.timezone.utc) - user.joined_at).days
                if srv_age < min_srv_age:
                    return await interaction.response.send_message(f"❌ يجب أن تكون عضواً في السيرفر منذ {min_srv_age} يوم.", ephemeral=True)

        # --- ✅ إدارة المشاركة (دخول/خروج) ---
        if user.id in view.participants:
            view.participants.remove(user.id)
            await interaction.response.send_message("⚠️ تم إلغاء مشاركتك.", ephemeral=True)
        else:
            view.participants.append(user.id)
            await interaction.response.send_message("✅ تم تسجيل دخولك بنجاح! بالتوفيق 💖", ephemeral=True)

        # تحديث نص الزر
        self.label = f"🎉 انضمام ({len(view.participants)})"
        await interaction.message.edit(view=view)
        
        # 💾 حفظ فوري في الملف (عشان لو طفى البوت)
        if self.bot.get_cog("GiveawaySystem"):
            self.bot.get_cog("GiveawaySystem").update_data(self.guild_id, interaction.message.id, view.participants)

# --- 👀 الـ View (الحاوية مال الزر) ---
class GiveawayView(View):
    def __init__(self, bot, requirements, guild_id, participants=None):
        super().__init__(timeout=None) # 🔥 الزر ما يموت أبداً
        self.participants = participants if participants else []
        self.ended = False
        self.guild_id = guild_id
        self.add_item(JoinButton(bot, requirements, guild_id))

# --- ⚙️ الكوج الرئيسي (النظام) ---
class GiveawaySystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_giveaways = {} # Format: {msg_id: {data..., view}}
        # بدء مهمة مراقبة الوقت
        self.check_task.start()

    def cog_unload(self):
        self.check_task.cancel()

    # --- 📂 دوال التعامل مع الملفات (Database Lite) ---
    def load_json(self, path):
        if not os.path.exists(path): return {}
        try:
            with open(path, 'r', encoding='utf-8') as f: return json.load(f)
        except: return {}

    def save_json(self, path, data):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def get_config_path(self, guild_id):
        return get_guild_file(guild_id, 'giveaway_config.json')

    def get_active_path(self, guild_id):
        return get_guild_file(guild_id, 'active_giveaways.json')

    # تحديث المشاركين في الملف
    def update_data(self, guild_id, msg_id, participants):
        path = self.get_active_path(guild_id)
        data = self.load_json(path)
        if str(msg_id) in data:
            data[str(msg_id)]['participants'] = participants
            self.save_json(path, data)

    # --- 🔄 عند تشغيل البوت (Restoration) ---
    @commands.Cog.listener()
    async def on_ready(self):
        print("🔄 Loading active giveaways...")
        count = 0

        # We need to iterate over all guilds to find active giveaways
        for guild in self.bot.guilds:
            active_path = self.get_active_path(guild.id)
            if not os.path.exists(active_path):
                continue

            data = self.load_json(active_path)
            for msg_id, g_data in data.items():
                channel = self.bot.get_channel(g_data['channel_id'])
                if channel:
                    # استرجاع الزر وتشغيله
                    view = GiveawayView(self.bot, g_data['requirements'], guild.id, g_data['participants'])
                    self.bot.add_view(view, message_id=int(msg_id))

                    # إرجاعه للذاكرة
                    self.active_giveaways[int(msg_id)] = {**g_data, "view": view, "guild_id": guild.id}
                    count += 1
        print(f"✅ Restored {count} active giveaways.")

    # --- 🔥 أمر البدء (Prefix Command) 🔥 ---
    @commands.command(name="gstart", aliases=["بدء_قيف"])
    @commands.has_permissions(administrator=True)
    async def start_giveaway(self, ctx):
        # 1. تحميل الإعدادات من الداشبورد
        config = self.load_json(self.get_config_path(ctx.guild.id))
        if not config:
            return await ctx.send("❌ لا يوجد قالب محفوظ! يرجى الحفظ من الداشبورد أولاً.")

        # 2. حساب الوقت
        time_val = int(config.get('time_val', 24))
        unit = config.get('time_unit', 'h')
        seconds = time_val * {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}.get(unit, 3600)
        end_ts = int((datetime.datetime.now() + datetime.timedelta(seconds=seconds)).timestamp())

        # 3. تجهيز الامبيد (الشكل)
        color = int(config.get('color', '#ffb7c5').replace('#', ''), 16)
        embed = discord.Embed(
            title=f"🎁 {config.get('prize')}",
            description=f"{config.get('description', '')}\n\n⏰ **ينتهي:** <t:{end_ts}:R>\n👑 **المستضيف:** {ctx.author.mention}",
            color=color
        )
        
        # الصور
        if config.get('image_url'): embed.set_image(url=config['image_url'])
        if config.get('thumbnail_url'): embed.set_thumbnail(url=config['thumbnail_url'])

        # عرض الشروط في الامبيد
        req_text = ""
        # الرتب
        if config.get('req_role_id'): req_text += f"• رتبة مطلوبة: <@&{config['req_role_id']}>\n"
        if config.get('blacklist_role_id'): req_text += f"• رتبة ممنوعة: <@&{config['blacklist_role_id']}>\n"
        if config.get('bypass_role_id'): req_text += f"• رتبة تجاوز: <@&{config['bypass_role_id']}>\n"
        
        # الفويس
        voice_min = int(config.get('req_voice_minutes', 0) or 0)
        if voice_min > 0: req_text += f"• تواجد صوتي: **{voice_min} دقيقة**\n"
        elif config.get('req_voice'): req_text += f"• تواجد صوتي: مطلوب\n"
        
        # العمر
        if config.get('min_account_age'): req_text += f"• عمر الحساب: +{config['min_account_age']} يوم\n"
        if config.get('min_server_age'): req_text += f"• مدة بالسيرفر: +{config['min_server_age']} يوم\n"

        if req_text:
            embed.add_field(name="🔒 الشروط والمتطلبات:", value=req_text, inline=False)
        
        embed.set_footer(text="Lona Giveaways System")

        # 4. النشر (المنشن والقناة)
        channel_id = config.get('channel_id')
        channel = self.bot.get_channel(int(channel_id)) if channel_id else ctx.channel
        
        if not channel: return await ctx.send("❌ القناة غير موجودة!")

        content = "🎉 **GIVEAWAY**"
        ping = config.get('ping_type', 'none')
        if ping == 'everyone': content += " @everyone"
        elif ping == 'here': content += " @here"

        view = GiveawayView(self.bot, config, ctx.guild.id)
        msg = await channel.send(content=content, embed=embed, view=view)

        # 5. الحفظ (Persistence)
        giveaway_data = {
            "channel_id": channel.id,
            "prize": config.get('prize'),
            "winners_count": int(config.get('winners', 1)),
            "end_timestamp": end_ts,
            "requirements": config,
            "participants": []
        }
        
        # حفظ في الملف
        active_path = self.get_active_path(ctx.guild.id)
        saved = self.load_json(active_path)
        saved[str(msg.id)] = giveaway_data
        self.save_json(active_path, saved)
        
        # حفظ في الذاكرة
        self.active_giveaways[msg.id] = {**giveaway_data, "view": view, "guild_id": ctx.guild.id}

        # تنظيف الأمر
        try: await ctx.message.delete()
        except: pass

    # --- 🏁 إنهاء القيف اوي ---
    async def end_giveaway(self, msg_id, guild_id=None):
        # 1. جلب البيانات
        if msg_id not in self.active_giveaways: return False
        g_data = self.active_giveaways[msg_id]
        
        # Resolve guild_id from memory if not provided
        if not guild_id:
            guild_id = g_data.get('guild_id')

        channel = self.bot.get_channel(g_data['channel_id'])
        if not channel: return False
        
        try: msg = await channel.fetch_message(msg_id)
        except: return False

        # 2. تعطيل القيف اوي
        view = g_data['view']
        view.ended = True
        for child in view.children: child.disabled = True
        
        # 3. السحب
        participants = view.participants
        winners_count = g_data['winners_count']
        prize = g_data['prize']
        
        embed = msg.embeds[0]

        if not participants:
            embed.description += "\n\n❌ **انتهى الوقت ولم يشارك أحد!**"
            embed.color = 0x2f3136 # رمادي
            await msg.edit(embed=embed, view=view)
        else:
            # اختيار الفائزين عشوائياً
            count = min(len(participants), winners_count)
            winners = random.sample(participants, k=count)
            winners_text = ", ".join([f"<@{uid}>" for uid in winners])
            
            embed.description = f"🎁 **الجائزة:** {prize}\n👑 **الفائز:** {winners_text}\n👥 **عدد المشاركين:** {len(participants)}"
            embed.color = 0x00ff00 # أخضر
            embed.set_footer(text="انتهى القيف اوي ✅")
            
            await msg.edit(content=f"🎉 **مبروووك للفائزين:** {winners_text}", embed=embed, view=view)
            await channel.send(f"🎉 الف مبروك {winners_text}! لقد فزتم بـ **{prize}** 🎁\nيرجى فتح تذكرة لاستلام الجائزة.")

        # 4. الحذف من النظام
        del self.active_giveaways[msg_id]

        if guild_id:
            active_path = self.get_active_path(guild_id)
            saved = self.load_json(active_path)
            if str(msg_id) in saved:
                del saved[str(msg_id)]
                self.save_json(active_path, saved)
        
        return True

    # --- ⏰ مؤقت الخلفية (لفحص الانتهاء) ---
    @tasks.loop(seconds=10)
    async def check_task(self):
        current_time = datetime.datetime.now().timestamp()
        # ننسخ القائمة (list) عشان ما يصير خطأ اذا حذفنا منها اثناء اللوب
        for msg_id in list(self.active_giveaways.keys()):
            g_data = self.active_giveaways[msg_id]
            if current_time >= g_data['end_timestamp']:
                await self.end_giveaway(msg_id)

async def setup(bot):
    await bot.add_cog(GiveawaySystem(bot))
