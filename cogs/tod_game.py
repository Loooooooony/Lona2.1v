import discord
from discord.ext import commands
import asyncio
import random
from data.tod_data import GAME_DATA

# --- 📦 كلاس الجلسة ---
class ToDSession:
    def __init__(self, channel_id):
        self.channel_id = channel_id
        self.game_active = False
        self.players = []
        self.host = None
        self.mode = "cute"
        self.current_player = None
        self.turn_counts = {} 
        self.chickens = set() # 🐔 قائمة الدجاج (المنسحبين)

class ToDGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}

    def get_session(self, channel_id):
        if channel_id not in self.sessions:
            self.sessions[channel_id] = ToDSession(channel_id)
        return self.sessions[channel_id]

    # --- 1️⃣ اللوبي ---
    @commands.command(name="صراحة", aliases=["tod"], help="بدء لعبة صراحة أو جرأة بمودات مختلفة (كيوت، عادي، كراهية..).")
    async def start_tod(self, ctx):
        session = self.get_session(ctx.channel.id)
        if session.game_active:
            await ctx.send("⛔ **توجد لعبة جارية!** استخدم `!توقيف_صراحة` لإنهائها.")
            return

        self.sessions[ctx.channel.id] = ToDSession(ctx.channel.id)
        session = self.sessions[ctx.channel.id]
        session.host = ctx.author
        session.players.append(ctx.author)

        embed = self.create_lobby_embed(session)
        view = LobbyView(self, session)
        view.message = await ctx.send(embed=embed, view=view)

    @commands.command(name="توقيف_صراحة", aliases=["stop_tod"], help="إيقاف لعبة صراحة أو جرأة الجارية.")
    async def stop_game(self, ctx):
        session = self.get_session(ctx.channel.id)
        if not session.game_active: return await ctx.send("⛔ لا توجد لعبة.")
        if ctx.author != session.host and not ctx.author.guild_permissions.administrator:
            return await ctx.send("⛔ فقط المنظم يمكنه الإيقاف.")
        
        session.game_active = False
        await ctx.send("🛑 **تم إيقاف اللعبة.**")

    def create_lobby_embed(self, session):
        if not session.players: players_list = "لا يوجد لاعبين."
        else: players_list = "\n".join([f"{i+1}. {p.mention}" for i, p in enumerate(session.players)])

        mode_names = {
            "cute": "🌸 كيوت", "normal": "🙂 عادي",
            "embarrassing": "😳 محرج", "hate": "👿 كراهية (خطر ☢️)"
        }

        embed = discord.Embed(
            title="🍾 لعبة صراحة أو جرأة (Truth or Dare)",
            description=f"**المود الحالي:** `{mode_names[session.mode]}`\n\nاضغط انضمام ثم بدء.",
            color=discord.Color.dark_purple()
        )
        embed.add_field(name=f"👥 اللاعبون ({len(session.players)})", value=players_list, inline=False)
        embed.set_footer(text=f"المنظم: {session.host.display_name}")
        return embed

    # --- 2️⃣ بدء اللعبة ---
    async def initiate_start(self, interaction, session):
        if len(session.players) < 2:
            return await interaction.response.send_message("⚠️ نحتاج لاعبين اثنين على الأقل!", ephemeral=True)

        # تصفير عداد الأدوار عند البدء
        for p in session.players:
            session.turn_counts[p.id] = 0

        if session.mode == "hate":
            await interaction.message.delete()
            await self.start_hate_intro(interaction.channel, session)
        else:
            await interaction.message.delete()
            await self.start_game_logic(interaction.channel, session)

    async def start_hate_intro(self, channel, session):
        mentions = " ".join([p.mention for p in session.players])
        embed = discord.Embed(
            title="☢️ تحذير: منطقة خطر (مود الكراهية)",
            description="**لقد اخترتم الطريق الصعب...**\nالأسئلة مصممة لإثارة الفتنة والمشاكل.\nالرجاء الموافقة على الشروط.",
            color=discord.Color.dark_red()
        )
        view = HateIntroView(self, session)
        await channel.send(content=f"{mentions}\n🔥🔥 **تجمعوا!** 🔥🔥", embed=embed, view=view)

    # --- 3️⃣ منطق اللعب والفر (الذكي والعادل جداً) ---
    async def start_game_logic(self, channel, session):
        session.game_active = True
        await channel.send("🔥 **انطلقت اللعبة!**")
        await self.spin_bottle(channel, session)

    async def spin_bottle(self, channel, session):
        if not session.game_active: return

        spin_msg = await channel.send("🍾 **الزجاجة تدور...**")
        await asyncio.sleep(1.5)
        await spin_msg.edit(content="🍾 **الزجاجة تدور... 💫**")
        await asyncio.sleep(1.0)

        # --- ⚖️ نظام العدالة الصارمة ---
        weights = []
        for p in session.players:
            count = session.turn_counts.get(p.id, 0)
            # المعادلة الجديدة: الوزن يقل بشكل جنوني كلما زاد اللعب
            # 1 / (count + 1)^3
            weight = 1.0 / ((count + 1) ** 3)
            weights.append(weight)

        # اختيار الضحية
        victim = random.choices(session.players, weights=weights, k=1)[0]
        
        # زيادة العداد
        session.turn_counts[victim.id] = session.turn_counts.get(victim.id, 0) + 1
        session.current_player = victim
        
        await spin_msg.edit(content=f"👉 **وقفت الزجاجة عند:** {victim.mention} 😈")
        
        # التحقق من الدجاج 🐔
        if victim.id in session.chickens:
            await channel.send(f"🐔 **{victim.mention} أنت (دجاجة) سابقاً!**\nليس لديك حق الاختيار.. البوت سيختار لك عشوائياً! 🎲")
            await asyncio.sleep(2)
            forced_choice = random.choice(["truth", "dare"])
            await self.generate_challenge(channel, session, forced_choice)
        else:
            view = ChoiceView(self, session, victim)
            await channel.send(f"{victim.mention}، أمامك 30 ثانية للاختيار:", view=view)

    # --- 4️⃣ توليد الأسئلة ---
    async def generate_challenge(self, destination, session, choice_type, interaction=None):
        try:
            questions_pool = GAME_DATA[session.mode][choice_type]
        except:
            questions_pool = ["حدث خطأ في الداتا."]

        question_text = random.choice(questions_pool)

        if "{target}" in question_text:
            potential_targets = [p for p in session.players if p != session.current_player]
            target_name = random.choice(potential_targets).mention if potential_targets else "نفسك"
            question_text = question_text.replace("{target}", target_name)

        emoji = "🗣️" if choice_type == "truth" else "🔥"
        header = "سؤال صراحة" if choice_type == "truth" else "تحدي جرأة"
        
        msg_content = (
            f"> ## {emoji} {header}\n"
            f"> **{question_text}**\n\n"
            f"اللاعب: {session.current_player.mention}\n"
            f"⏳ **بانتظار حكم المنظم...**"
        )

        view = HostActionView(self, session)
        
        if interaction:
            await interaction.response.send_message(content=msg_content, view=view)
        else:
            await destination.send(content=msg_content, view=view)

# --- 🖥️ الواجهات (Views) ---

class LobbyView(discord.ui.View):
    def __init__(self, cog, session):
        super().__init__(timeout=None)
        self.cog = cog
        self.session = session

    @discord.ui.select(placeholder="مود اللعبة (للمنظم)", options=[
        discord.SelectOption(label="🌸 كيوت", value="cute"),
        discord.SelectOption(label="🙂 عادي", value="normal"),
        discord.SelectOption(label="😳 محرج", value="embarrassing"),
        discord.SelectOption(label="👿 كراهية", value="hate", description="فتنة ومشاكل (خطر)"),
    ])
    async def select_mode(self, interaction, select):
        if interaction.user != self.session.host: return await interaction.response.send_message("للمنظم فقط.", ephemeral=True)
        self.session.mode = select.values[0]
        await interaction.response.edit_message(embed=self.cog.create_lobby_embed(self.session), view=self)

    @discord.ui.button(label="انضمام", style=discord.ButtonStyle.success)
    async def join(self, interaction, button):
        if interaction.user in self.session.players: return await interaction.response.send_message("أنت مسجل.", ephemeral=True)
        self.session.players.append(interaction.user)
        self.session.turn_counts[interaction.user.id] = 0
        await interaction.response.edit_message(embed=self.cog.create_lobby_embed(self.session), view=self)

    @discord.ui.button(label="بدء", style=discord.ButtonStyle.primary)
    async def start(self, interaction, button):
        if interaction.user != self.session.host: return await interaction.response.send_message("فقط المنظم يبدأ اللعبة.", ephemeral=True)
        await self.cog.initiate_start(interaction, self.session)

class HateIntroView(discord.ui.View):
    def __init__(self, cog, session):
        super().__init__(timeout=None)
        self.cog = cog
        self.session = session

    @discord.ui.button(label="📜 قراءة الشروط (المخاطر)", style=discord.ButtonStyle.secondary)
    async def show_terms(self, interaction, button):
        terms = (
            "**⚠️ شروط مود الكراهية:**\n"
            "1. ما يحدث في اللعبة يبقى في اللعبة.\n"
            "2. ممنوع الزعل أو البلوك بعد انتهاء اللعبة.\n"
            "3. استعد لخسارة بعض الأصدقاء.\n"
        )
        await interaction.response.send_message(terms, ephemeral=True)

    @discord.ui.button(label="أنا موافق (تحمل المسؤولية) 🩸", style=discord.ButtonStyle.danger)
    async def accept(self, interaction, button):
        await interaction.response.send_message(f"💀 **{interaction.user.display_name}** باع حياته ووافق!", ephemeral=False)

    @discord.ui.button(label="🚀 إطلاق الفوضى (للمنظم)", style=discord.ButtonStyle.primary, row=1)
    async def start_chaos(self, interaction, button):
        if interaction.user != self.session.host: return
        await interaction.message.delete()
        await self.cog.start_game_logic(interaction.channel, self.session)

class ChoiceView(discord.ui.View):
    def __init__(self, cog, session, player):
        super().__init__(timeout=None) # ♾️ وقت مفتوح
        self.cog = cog
        self.session = session
        self.player = player
        self.responded = False

    async def interaction_check(self, interaction):
        if interaction.user != self.player:
            await interaction.response.send_message("انتظر دورك!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="صراحة 🗣️", style=discord.ButtonStyle.blurple)
    async def truth(self, interaction, button):
        self.responded = True
        self.stop()
        await self.cog.generate_challenge(None, self.session, "truth", interaction)

    @discord.ui.button(label="جرأة 🔥", style=discord.ButtonStyle.danger)
    async def dare(self, interaction, button):
        self.responded = True
        self.stop()
        await self.cog.generate_challenge(None, self.session, "dare", interaction)

class HostActionView(discord.ui.View):
    def __init__(self, cog, session):
        super().__init__(timeout=None) # ♾️ وقت مفتوح
        self.cog = cog
        self.session = session

    async def interaction_check(self, interaction):
        if interaction.user != self.session.host:
            await interaction.response.send_message(f"⛔ **فقط المنظم ({self.session.host.display_name}) هو الحكم!**", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✅ نفذ (بطل)", style=discord.ButtonStyle.success)
    async def done(self, interaction, button):
        await interaction.response.send_message(f"👏 **حكم المنظم:** {self.session.current_player.mention} نفذ التحدي بنجاح!")
        self.stop()
        
        # توبة الدجاجة
        if self.session.current_player.id in self.session.chickens:
             self.session.chickens.remove(self.session.current_player.id)
             await interaction.followup.send(f"✨ **تم العفو عن {self.session.current_player.mention} من لقب دجاجة!**")

        await asyncio.sleep(2)
        await self.cog.spin_bottle(interaction.channel, self.session)

    @discord.ui.button(label="🐔 انسحب (دجاجة)", style=discord.ButtonStyle.secondary)
    async def chicken(self, interaction, button):
        player = self.session.current_player
        self.session.chickens.add(player.id) # 📝 تسجيله في القائمة
        
        await interaction.response.send_message(
            f"🐔 **حكم المنظم:** {player.mention} انسحب!\n"
            f"**العقاب:** في دورك القادم، البوت سيختار لك إجبارياً!"
        )
        self.stop()
        await asyncio.sleep(2)
        await self.cog.spin_bottle(interaction.channel, self.session)

async def setup(bot):
    await bot.add_cog(ToDGame(bot))