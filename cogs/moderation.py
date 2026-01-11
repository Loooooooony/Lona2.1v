import discord
from discord.ext import commands
import json
import asyncio
import datetime
import os

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_path = 'data/moderation_config.json'
        self.warnings_path = 'data/warnings.json'
        
        # 🗺️ خريطة الصلاحيات: نربط كل أمر بصلاحية الديسكورد الأصلية
        self.perm_map = {
            "kick": "kick_members",
            "ban": "ban_members",
            "unban": "ban_members",
            "mute": "moderate_members",
            "unmute": "moderate_members",
            "vkick": "move_members",
            "vmute": "mute_members",
            "vunmute": "mute_members",
            "move": "move_members",
            "clear": "manage_messages",
            "lock": "manage_channels",
            "unlock": "manage_channels",
            "slowmode": "manage_channels",
            "warn": "kick_members", # أو أي صلاحية إدارية تفضليها
            "warns": "kick_members",
            "role": "manage_roles",
            "nick": "manage_nicknames",
            "setcolor": "manage_roles"
        }

    # --- 🛠️ أدوات مساعدة ---
    
    def get_cmd_config(self, cmd_key):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get(cmd_key, {})
        except: return {}

    async def check_auth(self, ctx, cmd_key):
        # 1. 👑 الأونر والأدمن (صلاحية مطلقة دائماً)
        if ctx.guild.owner_id == ctx.author.id or ctx.author.guild_permissions.administrator:
            return True

        conf = self.get_cmd_config(cmd_key)
        
        # 2. 📜 فحص الداتا (الرتب المخصصة):
        # إذا عنده الرتبة المذكورة بالملف، يعبر حتى لو ما عنده صلاحية ديسكورد
        if conf:
            # إذا الأمر معطل من الكونفق، نمنعه (ممكن نرد أو نسكت حسب الرغبة، هنا راح أخليه يرجع False بصمت)
            if not conf.get('enabled', True):
                return False

            allowed_roles = conf.get('roles', [])
            user_role_ids = [str(r.id) for r in ctx.author.roles]
            
            # هل يمتلك وحدة من الرتب المسموحة؟
            if any(rid in user_role_ids for rid in allowed_roles):
                return True # ✅ نجح عبر الواسطة (الداتا)

        # 3. 🛡️ فحص صلاحيات الديسكورد الأصلية (للي ما موجودين بالداتا):
        # نجيب الصلاحية المطلوبة لهذا الأمر
        req_perm = self.perm_map.get(cmd_key)
        if req_perm:
            # نشيك هل العضو عنده هاي الصلاحية بالديسكورد؟
            if getattr(ctx.author.guild_permissions, req_perm, False):
                
                # ملاحظة: حتى لو عنده صلاحية، نتأكد إنه بالروم المسموح (إذا محددين رومات)
                if conf:
                    allowed_channels = conf.get('channels', [])
                    if allowed_channels and str(ctx.channel.id) not in allowed_channels:
                        return False # عنده صلاحية بس بغير روم
                
                return True # ✅ نجح عبر الصلاحية الأصلية

        # 4. ❌ إذا لا واسطة ولا صلاحية -> صمت تام (False)
        return False

    def parse_time(self, time_str):
        seconds = 0
        time_str = time_str.lower()
        if time_str.endswith("s"): seconds = int(time_str[:-1])
        elif time_str.endswith("m"): seconds = int(time_str[:-1]) * 60
        elif time_str.endswith("h"): seconds = int(time_str[:-1]) * 3600
        elif time_str.endswith("d"): seconds = int(time_str[:-1]) * 86400
        elif time_str.isdigit(): seconds = int(time_str)
        return seconds

    def add_warning(self, user_id, reason, moderator):
        try:
            with open(self.warnings_path, 'r', encoding='utf-8') as f: data = json.load(f)
        except: data = {}
        
        uid = str(user_id)
        if uid not in data: data[uid] = []
        warn_entry = {"reason": reason, "mod": moderator, "date": str(datetime.date.today())}
        data[uid].append(warn_entry)
        
        with open(self.warnings_path, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4)
        return len(data[uid])

    # --- 👂 الأذن السحرية ---
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.content: return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f: config = json.load(f)
        except: return

        parts = message.content.split()
        if not parts: return
        
        trigger_word = parts[0].lower()
        found_cmd_key = None
        
        for cmd_key, data in config.items():
            if trigger_word == cmd_key.lower():
                found_cmd_key = cmd_key
                break
            aliases = [a.lower() for a in data.get('aliases', [])]
            if trigger_word in aliases:
                found_cmd_key = cmd_key
                break
        
        if found_cmd_key:
            if found_cmd_key == "setnick": found_cmd_key = "nick"

            prefix = await self.bot.get_prefix(message)
            if isinstance(prefix, list): prefix = prefix[0]
            
            args = message.content[len(parts[0]):]
            new_content = f"{prefix}{found_cmd_key}{args}"
            message.content = new_content
            await self.bot.process_commands(message)

    # --- 🚨 معالج الأخطاء ---
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if ctx.cog != self: return

        # هنا نطبع الأخطاء "الاستخدامية" بس، ما نطبع أخطاء الصلاحيات
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ **ناقص معلومة!** الصيغة: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ **ما لكيت العضو!** تأكدي من المنشن.")
        elif isinstance(error, commands.ChannelNotFound):
            await ctx.send("❌ **ما لكيت الروم!**")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ **كتبتي شي غلط!**")
        # ألغينا طباعة MissingPermissions لأن check_auth هو المسؤول هسة

    # ==========================
    # 🚨 أوامر الطرد والحظر
    # ==========================
    
    @commands.command(name="kick")
    async def kick_user(self, ctx, member: discord.Member, *, reason="بدون سبب"):
        if not await self.check_auth(ctx, "kick"): return # صمت تام
        try:
            await member.kick(reason=reason)
            msg = await ctx.send(f"🦵 **تم طرد {member.mention}** | 📝 السبب: {reason}")
            conf = self.get_cmd_config("kick")
            if conf.get('delete_after', 0) > 0: await msg.delete(delay=conf['delete_after'])
        except discord.Forbidden:
            await ctx.send("❌ **ما كدرت أطرده! (يمكن رتبته أعلى مني)**")

    @commands.command(name="ban")
    async def ban_user(self, ctx, member: discord.Member, *, reason="بدون سبب"):
        if not await self.check_auth(ctx, "ban"): return
        try:
            await member.ban(reason=reason)
            msg = await ctx.send(f"🔨 **تم حظر {member.mention} نهائياً** | 📝 السبب: {reason}")
            conf = self.get_cmd_config("ban")
            if conf.get('delete_after', 0) > 0: await msg.delete(delay=conf['delete_after'])
        except discord.Forbidden:
            await ctx.send("❌ **ما كدرت أحظره! (رتبته عالية؟)**")

    @commands.command(name="unban")
    async def unban_user(self, ctx, user_id: int):
        if not await self.check_auth(ctx, "unban"): return
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user)
            await ctx.send(f"🕊️ **تم فك الحظر عن {user.name}**")
        except:
            await ctx.send("❌ **ما لكيت هذا العضو أو صار خطأ!**")

    # ==========================
    # 🔇 أوامر الإسكات
    # ==========================

    @commands.command(name="mute")
    async def text_mute(self, ctx, member: discord.Member, time_str: str, *, reason="بدون سبب"):
        if not await self.check_auth(ctx, "mute"): return
        seconds = self.parse_time(time_str)
        if seconds == 0: return await ctx.send("❌ **صيغة الوقت غلط!**")
        
        try:
            await member.timeout(datetime.timedelta(seconds=seconds), reason=reason)
            await ctx.send(f"😶 **تم إسكات {member.mention}** لمدة `{time_str}` | السبب: {reason}")
        except discord.Forbidden:
             await ctx.send("❌ **ما كدرت أسكته! (رتبته أعلى مني؟)**")

    @commands.command(name="unmute")
    async def text_unmute(self, ctx, member: discord.Member):
        if not await self.check_auth(ctx, "unmute"): return
        try:
            await member.timeout(None)
            await ctx.send(f"😀 **تم فك الإسكات عن {member.mention}**")
        except:
            await ctx.send("❌ **فشل فك الإسكات!**")

    # ==========================
    # 🔊 أوامر الصوت
    # ==========================

    @commands.command(name="vkick")
    async def voice_kick(self, ctx, member: discord.Member):
        if not await self.check_auth(ctx, "vkick"): return
        if member.voice:
            try:
                await member.move_to(None)
                await ctx.send(f"🔊🚫 **تم طرد {member.mention} من الروم الصوتي!**")
            except discord.Forbidden:
                await ctx.send("❌ **ما عندي صلاحية (Move Members) حتى أطرده!**")
        else:
            await ctx.send("❌ **هو مو داخل روم صوتي أصلاً!**")

    @commands.command(name="vmute")
    async def voice_mute(self, ctx, member: discord.Member):
        if not await self.check_auth(ctx, "vmute"): return
        if member.voice:
            try:
                await member.edit(mute=True)
                await ctx.send(f"🔇 **تم كتم {member.mention} صوتياً!**")
            except:
                await ctx.send("❌ **فشل الكتم!**")
        else:
            await ctx.send("❌ **لازم يكون بروم صوتي.**")

    @commands.command(name="vunmute")
    async def voice_unmute(self, ctx, member: discord.Member):
        if not await self.check_auth(ctx, "vunmute"): return
        if member.voice:
            try:
                await member.edit(mute=False)
                await ctx.send(f"🔊 **تم فك الكتم الصوتي عن {member.mention}!**")
            except:
                await ctx.send("❌ **فشل فك الكتم!**")
        else:
            await ctx.send("❌ **لازم يكون بروم صوتي.**")

    @commands.command(name="move")
    async def move_member(self, ctx, member: discord.Member, channel: discord.VoiceChannel = None):
        # 1. التحقق من الصلاحية (داتا أو ديسكورد)
        if not await self.check_auth(ctx, "move"): return
        
        # 2. السحب الذكي: إذا ماكو روم محدد، نستخدم روم اللي كتب الأمر
        if channel is None:
            if ctx.author.voice and ctx.author.voice.channel:
                channel = ctx.author.voice.channel
            else:
                # هنا لازم نرد عليه نكله انت وين؟ لان هو عنده صلاحية بس غلط بالاستخدام
                return await ctx.send("❌ **لازم تكونين داخل روم صوتي حتى أسحبه يمج، أو حددي اسم الروم بالأمر!**")

        # 3. التنفيذ
        if member.voice:
            try:
                await member.move_to(channel)
                await ctx.send(f"✈️ **تم سحب {member.mention} إلى {channel.name}**")
            except discord.Forbidden:
                await ctx.send("❌ **ما كدرت أسحبه! (ما عندي صلاحية Move Members)**")
            except Exception as e:
                await ctx.send(f"❌ **صار خطأ:** {e}")
        else:
            await ctx.send("❌ **العضو مو بالصوت أصلاً!**")

    # ==========================
    # 🧹 إدارة الشات
    # ==========================

    @commands.command(name="clear")
    async def clear_msgs(self, ctx, amount: int):
        if not await self.check_auth(ctx, "clear"): return
        try:
            deleted = await ctx.channel.purge(limit=amount+1)
            msg = await ctx.send(f"🧹 **تم مسح {len(deleted)-1} رسالة**")
            await msg.delete(delay=3)
        except:
             await ctx.send("❌ **ما عندي صلاحية (Manage Messages)!**")

    @commands.command(name="lock")
    async def lock_channel(self, ctx):
        if not await self.check_auth(ctx, "lock"): return
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send("🔒 **تم قفل الروم!**")

    @commands.command(name="unlock")
    async def unlock_channel(self, ctx):
        if not await self.check_auth(ctx, "unlock"): return
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.send("🔓 **تم فتح الروم!**")

    @commands.command(name="slowmode")
    async def set_slowmode(self, ctx, time_str: str):
        if not await self.check_auth(ctx, "slowmode"): return
        seconds = self.parse_time(time_str)
        await ctx.channel.edit(slowmode_delay=seconds)
        if seconds == 0: await ctx.send("🚀 **تم تعطيل الوضع البطيء!**")
        else: await ctx.send(f"🐢 **تم تفعيل الوضع البطيء:** رسالة كل {seconds} ثانية.")

    # ==========================
    # ⚠️ التحذيرات
    # ==========================

    @commands.command(name="warn")
    async def warn_user(self, ctx, member: discord.Member, *, reason="مخالفة قوانين"):
        if not await self.check_auth(ctx, "warn"): return
        count = self.add_warning(member.id, reason, ctx.author.name)
        
        embed = discord.Embed(title="⚠️ تم تحذير العضو", color=discord.Color.gold())
        embed.add_field(name="العضو", value=member.mention)
        embed.add_field(name="السبب", value=reason)
        embed.add_field(name="عدد التحذيرات", value=f"{count}")
        await ctx.send(embed=embed)

    @commands.command(name="warns")
    async def show_warnings(self, ctx, member: discord.Member):
        if not await self.check_auth(ctx, "warns"): return
        try:
            with open(self.warnings_path, 'r', encoding='utf-8') as f: data = json.load(f)
        except: data = {}
        warns = data.get(str(member.id), [])
        if not warns: return await ctx.send(f"✅ **{member.display_name}** نظيف! ما عنده ولا تحذير.")
        
        embed = discord.Embed(title=f"📜 سجل تحذيرات {member.display_name}", color=discord.Color.orange())
        for i, w in enumerate(warns, 1):
            embed.add_field(name=f"#{i}", value=f"📝 {w['reason']}\n📅 {w['date']}", inline=False)
        await ctx.send(embed=embed)

    # ==========================
    # 🎭 الإدارة العامة
    # ==========================

    @commands.command(name="role")
    async def manage_role(self, ctx, member: discord.Member, role: discord.Role):
        if not await self.check_auth(ctx, "role"): return
        try:
            if role in member.roles:
                await member.remove_roles(role)
                await ctx.send(f"➖ **تم سحب رتبة {role.name}**")
            else:
                await member.add_roles(role)
                await ctx.send(f"➕ **تم إعطاء رتبة {role.name}**")
        except discord.Forbidden:
            await ctx.send("❌ **ما كدرت أعدل الرتب! (رتبتي ناصية أو ما عندي صلاحية)**")

    @commands.command(name="nick", aliases=["setnick"])
    async def set_nickname(self, ctx, member: discord.Member, *, name):
        auth_nick = await self.check_auth(ctx, "nick")
        auth_setnick = await self.check_auth(ctx, "setnick")
        if not auth_nick and not auth_setnick: return # صمت تام

        try:
            await member.edit(nick=name)
            await ctx.send(f"🏷️ **تم تغيير الاسم إلى:** {name}")
        except:
            await ctx.send("❌ **ما أكدر أغير اسمه! (رتبته أعلى مني؟)**")

    @commands.command(name="setcolor")
    async def set_role_color(self, ctx, role: discord.Role, hex_color: str):
        if not await self.check_auth(ctx, "setcolor"): return
        hex_color = hex_color.replace("#", "")
        try:
            color = discord.Color(int(hex_color, 16))
            await role.edit(color=color)
            await ctx.send(f"🎨 **تم تغيير لون رتبة {role.name} بنجاح!**")
        except:
            await ctx.send("❌ **كود اللون غلط!**")

async def setup(bot):
    await bot.add_cog(Moderation(bot))