import discord
from discord.ext import commands
from discord.ui import Modal, TextInput, View
import asyncio
from datetime import timedelta

# --- مودل الاستمارة (Action 9) ---
class GenericModal(Modal):
    def __init__(self, title, target_channel):
        super().__init__(title=title)
        self.target_channel = target_channel
        self.answer = TextInput(label="اكتب هنا", style=discord.TextStyle.paragraph)
        self.add_item(self.answer)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ تم استلام ردك بنجاح!", ephemeral=True)
        if self.target_channel:
            embed = discord.Embed(title="📝 استجابة جديدة", description=f"**من:** {interaction.user.mention}\n**المحتوى:**\n{self.answer.value}", color=0x00ff00)
            await self.target_channel.send(embed=embed)

class InteractiveButtons(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component: return
        
        custom_id = interaction.data.get('custom_id', '')
        if not custom_id.startswith('lona_cmd:'): return

        # تفكيك الكود: lona_cmd:action:value
        try:
            _, action, value = custom_id.split(':', 2)
        except: return

        # --- تنفيذ الأفعال الـ 10 🔥 ---
        
        # 2. 🎭 الرتبة (Role)
        if action == 'role':
            try:
                role = interaction.guild.get_role(int(value))
                if role:
                    if role in interaction.user.roles:
                        await interaction.user.remove_roles(role)
                        await interaction.response.send_message(f"➖ سحبت منك رتبة **{role.name}**", ephemeral=True)
                    else:
                        await interaction.user.add_roles(role)
                        await interaction.response.send_message(f"➕ عطيتك رتبة **{role.name}**", ephemeral=True)
                else:
                    await interaction.response.send_message("❌ الرتبة غير موجودة.", ephemeral=True)
            except:
                await interaction.response.send_message("❌ البوت ما عنده صلاحية يعطي هاي الرتبة.", ephemeral=True)

        # 3. 💬 الرد (Reply)
        elif action == 'reply':
            msg = value.replace('{user}', interaction.user.mention)
            await interaction.response.send_message(msg, ephemeral=True)

        # 4. 🧵 ثريد (Thread)
        elif action == 'thread':
            try:
                thread = await interaction.channel.create_thread(name=f"خاص-{interaction.user.name}", type=discord.ChannelType.private_thread)
                await thread.add_user(interaction.user)
                await interaction.response.send_message(f"✅ فتحت لك ثريد خاص: {thread.mention}", ephemeral=True)
                await thread.send(f"هلاو {interaction.user.mention}، تفضل بشنو نخدمك؟")
            except:
                await interaction.response.send_message("❌ ما اكدر افتح ثريد هنا.", ephemeral=True)

        # 5. 🗑️ حذف (Delete)
        elif action == 'delete':
            try:
                await interaction.message.delete()
            except:
                await interaction.response.send_message("❌ ما اكدر امسح الرسالة.", ephemeral=True)

        # 6. 📩 خاص (DM)
        elif action == 'dm':
            try:
                await interaction.user.send(value)
                await interaction.response.send_message("📨 شيك الخاص!", ephemeral=True)
            except:
                await interaction.response.send_message("❌ الخاص مالك مقفول.", ephemeral=True)

        # 7. 🏷️ لقب (Nickname)
        elif action == 'nick':
            new_nick = value.replace('{user}', interaction.user.name)
            try:
                await interaction.user.edit(nick=new_nick[:32])
                await interaction.response.send_message(f"✅ غيرت اسمك الى: **{new_nick}**", ephemeral=True)
            except:
                await interaction.response.send_message("❌ ما عندي صلاحية اغير اسمك (رتبتك اعلى مني؟)", ephemeral=True)

        # 8. 🔇 تايم أوت (Timeout)
        elif action == 'timeout':
            try:
                duration = timedelta(minutes=int(value))
                await interaction.user.timeout(duration)
                await interaction.response.send_message(f"🤐 أكلت تايم أوت لمدة {value} دقائق!", ephemeral=True)
            except:
                await interaction.response.send_message("❌ فشل التايم أوت.", ephemeral=True)

        # 9. 📝 استمارة (Modal)
        elif action == 'modal':
            # هنا القيمة لازم تكون آيدي قناة اللوج
            try:
                target_channel = interaction.guild.get_channel(int(value))
                await interaction.response.send_modal(GenericModal("استمارة تواصل", target_channel))
            except:
                await interaction.response.send_message("❌ إعدادات الاستمارة خطأ.", ephemeral=True)

        # 10. 🔊 صوت (Sound - Troll)
        elif action == 'sound':
            # بما ان ما عندنا ملفات، راح نسوي حركة "دخول وخروج" سريعة كـ مقلب
            if interaction.user.voice:
                vc = await interaction.user.voice.channel.connect()
                await interaction.response.send_message("👻 بووو!", ephemeral=True)
                await asyncio.sleep(2)
                await vc.disconnect()
            else:
                await interaction.response.send_message("❌ لازم تكون بروم صوتي عشان اخوفك!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(InteractiveButtons(bot))