import discord
from discord.ext import commands
import json
import os
from datetime import datetime
import sys

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.data_manager import get_guild_file

class SuperLogger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 🧵 خريطة الثريدات: تنظيم هرمي
        self.thread_map = {
            "msg": "🗑️-الرسائل-والصور",
            "voice": "🎙️-الصوت-والكاميرا",
            "member": "👥-حركة-الأعضاء",
            "server": "⚙️-تعديلات-السيرفر",
            "security": "🚨-الأمان-والباند",
            "role": "👮-الرتب-والصلاحيات",
            "channel": "📺-القنوات",
            "invite": "📨-الدعوات"
        }

    def get_config(self, guild_id):
        path = get_guild_file(guild_id, 'log_config.json')
        try:
            with open(path, 'r', encoding='utf-8') as f: return json.load(f)
        except: return {}

    async def get_thread(self, guild, type_key):
        config = self.get_config(guild.id)
        channel_id = config.get('log_channel_id')
        if not channel_id: return None

        channel = guild.get_channel(int(channel_id))
        if not channel: return None

        thread_name = self.thread_map.get(type_key, "logs")
        
        # البحث عن الثريد (نشط أو مؤرشف)
        target = discord.utils.get(channel.threads, name=thread_name)
        if not target:
            async for t in channel.archived_threads(limit=50):
                if t.name == thread_name:
                    target = t
                    break
        
        # إنشاء الثريد
        if not target:
            try:
                target = await channel.create_thread(name=thread_name, type=discord.ChannelType.public_thread)
            except: return channel 
        
        return target

    # 🕵️‍♂️ دالة المخابرات (كشف الفاعل من السجلات)
    async def find_perpetrator(self, guild, action, target_id):
        if not guild.me.guild_permissions.view_audit_log: return None
        try:
            async for entry in guild.audit_logs(limit=3, action=action):
                if entry.target.id == target_id and (discord.utils.utcnow() - entry.created_at).total_seconds() < 20:
                    return entry.user
        except: return None
        return None

    # ==========================
    # 1️⃣ قسم الرسائل (Messages)
    # ==========================
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot or not message.guild: return
        if not self.get_config(message.guild.id).get('events', {}).get('msg_delete'): return
        thread = await self.get_thread(message.guild, "msg")
        if not thread: return

        desc = f"**👤 العضو:** {message.author.mention}\n**📺 القناة:** {message.channel.mention}"
        if message.content: desc += f"\n**📝 المحتوى:**\n```{message.content}```"
        
        # ☢️ كشف الملفات المحذوفة
        if message.attachments:
            desc += "\n**📎 الملفات المحذوفة:**"
            for att in message.attachments:
                desc += f"\n🔹 `{att.filename}` ({round(att.size/1024)}KB) [{att.content_type}]"
                desc += f"\n🔗 [رابط مؤقت للتحميل]({att.proxy_url})"

        embed = discord.Embed(title="🗑️ حذف رسالة", description=desc, color=0xff4d4d)
        embed.set_footer(text=f"Msg ID: {message.id}")
        embed.timestamp = datetime.now()
        await thread.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if not before.guild or before.author.bot or before.content == after.content: return
        if not self.get_config(before.guild.id).get('events', {}).get('msg_edit'): return
        thread = await self.get_thread(before.guild, "msg")
        if not thread: return

        embed = discord.Embed(description=f"**✏️ تعديل رسالة**\n👤 {before.author.mention} | [اذهب للرسالة]({after.jump_url})", color=0xffc107)
        embed.add_field(name="🔴 قبل", value=f"```{before.content[:900]}```", inline=False)
        embed.add_field(name="🟢 بعد", value=f"```{after.content[:900]}```", inline=False)
        await thread.send(embed=embed)

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload):
        if not payload.guild_id: return
        if not self.get_config(payload.guild_id).get('events', {}).get('msg_bulk'): return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return
        thread = await self.get_thread(guild, "msg")
        if thread:
            await thread.send(embed=discord.Embed(description=f"**🧨 حذف جماعي (Bulk Delete)**\nتم حذف **{len(payload.message_ids)}** رسالة في <#{payload.channel_id}>", color=0xff0000))

    # ==========================
    # 2️⃣ قسم الأعضاء (Members)
    # ==========================
    @commands.Cog.listener()
    async def on_member_join(self, member):
        if not self.get_config(member.guild.id).get('events', {}).get('member_join'): return
        thread = await self.get_thread(member.guild, "member")
        if not thread: return

        age = (discord.utils.utcnow() - member.created_at).days
        desc = f"**📥 دخول:** {member.mention}\n**📅 الحساب:** {age} يوم"
        embed = discord.Embed(description=desc, color=0x2ecc71)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else "")
        await thread.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if not self.get_config(member.guild.id).get('events', {}).get('member_leave'): return
        thread = await self.get_thread(member.guild, "member")
        if not thread: return

        # فحص هل هو طرد (Kick)؟
        actor = await self.find_perpetrator(member.guild, discord.AuditLogAction.kick, member.id)
        
        if actor:
            embed = discord.Embed(title="🦵 طرد (KICK)", description=f"**الضحية:** {member.mention}\n**👮‍♂️ الفاعل:** {actor.mention}", color=0xff6b6b)
            # نرسله لثريد الأمان
            sec_thread = await self.get_thread(member.guild, "security")
            if sec_thread: await sec_thread.send(embed=embed)
        else:
            embed = discord.Embed(description=f"**📤 خروج:** {member.mention}", color=0xe74c3c)
            await thread.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        cfg = self.get_config(before.guild.id).get('events', {})
        thread = await self.get_thread(before.guild, "member")
        if not thread: return

        # Nickname
        if before.nick != after.nick and cfg.get('member_update'):
            await thread.send(embed=discord.Embed(description=f"**🏷️ لقب:** {after.mention}\n🔴 `{before.nick}` ➡️ 🟢 `{after.nick}`", color=0x3498db))
        
        # Server Avatar
        if before.guild_avatar != after.guild_avatar and cfg.get('user_update'):
            embed = discord.Embed(title="🖼️ صورة السيرفر", description=f"**العضو:** {after.mention}", color=0x9b59b6)
            if before.guild_avatar: embed.set_thumbnail(url=before.guild_avatar.url)
            if after.guild_avatar: embed.set_image(url=after.guild_avatar.url)
            await thread.send(embed=embed)

        # Timeout 🛑
        if before.timed_out_until != after.timed_out_until:
            sec_thread = await self.get_thread(before.guild, "security")
            if sec_thread:
                if after.timed_out_until:
                    until = after.timed_out_until.strftime("%Y-%m-%d %H:%M")
                    # محاولة كشف الفاعل
                    actor = await self.find_perpetrator(before.guild, discord.AuditLogAction.member_update, before.id)
                    actor_txt = f"\n**👮‍♂️ الفاعل:** {actor.mention}" if actor else ""
                    await sec_thread.send(embed=discord.Embed(description=f"**🤐 تايم أوت:** {after.mention}{actor_txt}\n⏰ **حتى:** {until}", color=0x000000))
                else:
                    await sec_thread.send(embed=discord.Embed(description=f"**🗣️ فك تايم أوت:** {after.mention}", color=0xffffff))

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        # User update is global, but we can check mutual guilds
        # For simplicity and multi-guild context, this is tricky.
        # We'll check all mutual guilds and log if configured.
        pass # Disabling global user update logging to prevent spam across all guilds or need complex loop

    # ==========================
    # 3️⃣ قسم الأمان (Security)
    # ==========================
    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        if not self.get_config(guild.id).get('events', {}).get('ban_add'): return
        thread = await self.get_thread(guild, "security")
        if not thread: return

        actor = await self.find_perpetrator(guild, discord.AuditLogAction.ban, user.id)
        actor_txt = actor.mention if actor else "غير معروف"
        
        await thread.send(embed=discord.Embed(description=f"**🚫 باند (BAN):** {user.mention}\n**👮‍♂️ الفاعل:** {actor_txt}", color=0x990000))

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        if not self.get_config(guild.id).get('events', {}).get('ban_remove'): return
        thread = await self.get_thread(guild, "security")
        if not thread: return
        await thread.send(embed=discord.Embed(description=f"**🔓 فك باند:** {user.mention}", color=0xecf0f1))

    # ==========================
    # 4️⃣ قسم الصوت (Voice)
    # ==========================
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not self.get_config(member.guild.id).get('events', {}).get('voice_update'): return
        thread = await self.get_thread(member.guild, "voice")
        if not thread: return

        desc = ""
        color = 0x95a5a6

        if before.channel is None and after.channel is not None:
            desc = f"**🟢 انضم للصوت:** {after.channel.mention}"
            color = 0x2ecc71
        elif before.channel is not None and after.channel is None:
            desc = f"**🔴 خرج من الصوت:** {before.channel.mention}"
            color = 0xff4d4d
        elif before.channel != after.channel:
            desc = f"**🔄 انتقل:** {before.channel.mention} ➡️ {after.channel.mention}"
            color = 0x3498db
        
        if not before.self_stream and after.self_stream: desc = "**📺 بدأ بث مباشر (Stream)**"; color=0x9b59b6
        if not before.self_video and after.self_video: desc = "**📸 فتح كاميرا**"; color=0x9b59b6
        
        # 🔥 هنا كان الخطأ: غيرنا server_mute إلى mute
        if before.mute != after.mute:
            state = "🤐 ميوت سيرفر" if after.mute else "🗣️ فك ميوت سيرفر"
            actor = await self.find_perpetrator(member.guild, discord.AuditLogAction.member_update, member.id)
            desc = f"**{state}**" + (f" (بواسطة {actor.mention})" if actor else "")
            color = 0x000000

        # 🔥 وضفنا هذا بالمرة عشان لا يطلع ايرور اذا صار Deaf
        if before.deaf != after.deaf:
            state = "🙉 ديفن سيرفر" if after.deaf else "🎧 فك ديفن سيرفر"
            actor = await self.find_perpetrator(member.guild, discord.AuditLogAction.member_update, member.id)
            desc = f"**{state}**" + (f" (بواسطة {actor.mention})" if actor else "")
            color = 0x000000

        if desc:
            await thread.send(embed=discord.Embed(description=f"**👤 {member.mention}**\n{desc}", color=color))

    # ==========================
    # 5️⃣ قسم القنوات والرتب (Channels & Roles)
    # ==========================
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        if not self.get_config(channel.guild.id).get('events', {}).get('channel_create'): return
        thread = await self.get_thread(channel.guild, "channel")
        if thread: await thread.send(embed=discord.Embed(description=f"**✨ قناة جديدة:** {channel.mention}", color=0x2ecc71))

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        if not self.get_config(channel.guild.id).get('events', {}).get('channel_delete'): return
        thread = await self.get_thread(channel.guild, "channel")
        if not thread: return
        actor = await self.find_perpetrator(channel.guild, discord.AuditLogAction.channel_delete, channel.id)
        act_txt = f"\n**👮‍♂️ الفاعل:** {actor.mention}" if actor else ""
        await thread.send(embed=discord.Embed(description=f"**🗑️ حذف قناة:** `{channel.name}`{act_txt}", color=0xff4d4d))

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        if not self.get_config(before.guild.id).get('events', {}).get('channel_update'): return
        thread = await self.get_thread(before.guild, "channel")
        if not thread: return
        if before.name != after.name:
             await thread.send(embed=discord.Embed(description=f"**✏️ اسم قناة:** {before.mention}\n🔴 `{before.name}` ➡️ 🟢 `{after.name}`", color=0xe67e22))

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        if not self.get_config(role.guild.id).get('events', {}).get('role_create'): return
        thread = await self.get_thread(role.guild, "role")
        if thread: await thread.send(embed=discord.Embed(description=f"**✨ رتبة جديدة:** `{role.name}`", color=0x2ecc71))

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        if not self.get_config(role.guild.id).get('events', {}).get('role_delete'): return
        thread = await self.get_thread(role.guild, "role")
        if thread: await thread.send(embed=discord.Embed(description=f"**🗑️ حذف رتبة:** `{role.name}`", color=0xff4d4d))

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        if not self.get_config(before.guild.id).get('events', {}).get('role_update'): return
        thread = await self.get_thread(before.guild, "role")
        if not thread: return
        if before.name != after.name:
             await thread.send(embed=discord.Embed(description=f"**✏️ اسم رتبة:**\n🔴 `{before.name}` ➡️ 🟢 `{after.name}`", color=0xe67e22))

    # ==========================
    # 6️⃣ قسم السيرفر والدعوات (Server & Invites)
    # ==========================
    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        if not self.get_config(after.id).get('events', {}).get('server_update'): return
        thread = await self.get_thread(after, "server")
        if not thread: return
        if before.name != after.name:
            await thread.send(embed=discord.Embed(description=f"**🏰 اسم السيرفر:**\n🔴 `{before.name}` ➡️ 🟢 `{after.name}`", color=0x9b59b6))
        if before.icon != after.icon:
            await thread.send(embed=discord.Embed(description=f"**🖼️ تغيير أيقونة السيرفر**", color=0x9b59b6))
        if before.banner != after.banner:
            await thread.send(embed=discord.Embed(description=f"**🚩 تغيير بنر السيرفر**", color=0x9b59b6))

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        if not self.get_config(guild.id).get('events', {}).get('emoji_update'): return
        thread = await self.get_thread(guild, "server")
        if not thread: return
        if len(after) > len(before):
            new_e = next(e for e in after if e not in before)
            await thread.send(embed=discord.Embed(description=f"**😀 ايموجي جديد:** {new_e} (`{new_e.name}`)", color=0x2ecc71))
        elif len(after) < len(before):
            old_e = next(e for e in before if e not in after)
            await thread.send(embed=discord.Embed(description=f"**🗑️ حذف ايموجي:** `{old_e.name}`", color=0xff4d4d))

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        if not self.get_config(invite.guild.id).get('events', {}).get('invite_update'): return
        thread = await self.get_thread(invite.guild, "invite")
        if thread: await thread.send(embed=discord.Embed(description=f"**📨 دعوة جديدة:** `{invite.code}`\n👤 **المنشئ:** {invite.inviter.mention}", color=0x3498db))

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        if not self.get_config(invite.guild.id).get('events', {}).get('invite_update'): return
        thread = await self.get_thread(invite.guild, "invite")
        if thread: await thread.send(embed=discord.Embed(description=f"**🗑️ حذف دعوة:** `{invite.code}`", color=0xff4d4d))

async def setup(bot):
    await bot.add_cog(SuperLogger(bot))
