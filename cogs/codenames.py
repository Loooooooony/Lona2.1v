import discord
from discord.ext import commands
import asyncio
import random
import json
from data.codenames_data import WORDS_LIST, EMOJI_LIST

# دالة لجلب اسم الأمر من الملف
def get_command_name():
    try:
        with open('data/games_config.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('codenames', {}).get('command_name', 'codenames')
    except: return 'codenames'

class CodenamesSession:
    def __init__(self, channel_id):
        self.channel_id = channel_id
        self.game_active = False
        self.players = []
        self.red_team = []
        self.blue_team = []
        self.red_spymaster = None
        self.blue_spymaster = None
        self.board = []
        self.key = []
        self.revealed = []
        self.turn = "red"
        self.host = None
        self.mode = "classic"
        self.team_method = "random"
        self.start_team = "red"

class CodenamesGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}
        self.games_config = 'data/games_config.json'

    def get_session(self, channel_id):
        if channel_id not in self.sessions:
            self.sessions[channel_id] = CodenamesSession(channel_id)
        return self.sessions[channel_id]

    def get_text(self):
        try:
            with open(self.games_config, 'r', encoding='utf-8') as f:
                return json.load(f).get('codenames', {})
        except: return {}

    # الأمر يتغير حسب الداشبورد
    @commands.command(name=get_command_name(), aliases=["cn"])
    async def start_codenames(self, ctx):
        session = self.get_session(ctx.channel.id)
        if session.game_active:
            await ctx.send("⛔ توجد لعبة جارية!")
            return

        # إعدادات الداشبورد
        txt = self.get_text()
        title = txt.get('title', "🕵️‍♂️ الأسماء الحركية")
        desc = txt.get('description', "انضموا..")
        color = int(txt.get('color', '#e74c3c').replace('#', ''), 16)

        # تصفير الجلسة
        self.sessions[ctx.channel.id] = CodenamesSession(ctx.channel.id)
        session = self.sessions[ctx.channel.id]
        session.host = ctx.author
        session.players.append(ctx.author)

        embed = discord.Embed(title=title, description=desc, color=color)
        embed.set_footer(text=f"المنظم: {session.host.display_name}")
        
        # تمرير النصوص للفيو
        view = LobbyView(self, session, txt)
        view.message = await ctx.send(embed=embed, view=view)

    # --- باقي دوال اللعبة (نفس المنطق) ---
    async def initiate_game_start(self, interaction, session):
        if len(session.players) < 2: # قللت العدد للتجربة (سويه 4 بعدين)
            return await interaction.response.send_message("⚠️ نحتاج لاعبين أكثر!", ephemeral=True)

        if session.team_method == "manual":
            await interaction.message.delete()
            view = TeamSelectionView(self, session)
            await interaction.channel.send("⚖️ **اختر فريقك:**", view=view)
            return

        await interaction.message.delete()
        random.shuffle(session.players)
        mid = len(session.players) // 2
        session.red_team = session.players[:mid]
        session.blue_team = session.players[mid:]
        await self.finalize_setup(interaction.channel, session)

    async def finalize_setup(self, channel, session):
        if not session.red_team or not session.blue_team:
             await channel.send("⚠️ خطأ: أحد الفرق فارغ!")
             session.game_active = False
             return

        session.red_spymaster = random.choice(session.red_team)
        session.blue_spymaster = random.choice(session.blue_team)
        session.game_active = True
        
        source_list = WORDS_LIST if session.mode == "classic" else EMOJI_LIST
        session.board = random.sample(source_list, 25)
        session.revealed = [False] * 25

        session.start_team = random.choice(["red", "blue"])
        session.turn = session.start_team
        
        cards = [session.start_team] * 9 + (["blue"] if session.start_team == "red" else ["red"]) * 8 + ["neutral"] * 7 + ["assassin"] * 1
        random.shuffle(cards)
        session.key = cards

        await channel.send(
            f"📢 **بدأت!**\n🔴 قائد الأحمر: {session.red_spymaster.mention}\n🔵 قائد الأزرق: {session.blue_spymaster.mention}\n👉 الدور للفريق: **{ 'الأحمر 🔴' if session.turn == 'red' else 'الأزرق 🔵' }**"
        )
        
        view = GameBoardView(self, session)
        await channel.send("🤔 **اللوحة:**", view=view)

        control_view = GameControlView(self, session)
        await channel.send("🎮 **التحكم:**", view=control_view)

    def generate_map_string(self, session):
        grid_str = ""
        map_emoji = {"red": "🟥", "blue": "🟦", "neutral": "⬜", "assassin": "💀"}
        for i in range(25):
            if i % 5 == 0 and i != 0: grid_str += "\n"
            grid_str += map_emoji[session.key[i]] + " "
        return f"```\n{grid_str}\n```"

    async def process_click(self, interaction, session, index):
        if session.revealed[index]: return await interaction.response.defer()

        player = interaction.user
        current_team = session.red_team if session.turn == "red" else session.blue_team
        current_spy = session.red_spymaster if session.turn == "red" else session.blue_spymaster
        
        if player not in current_team: return await interaction.response.send_message("✋ ليس دورك!", ephemeral=True)
        if player == current_spy: return await interaction.response.send_message("🤫 القائد يلمح فقط!", ephemeral=True)

        card_type = session.key[index]
        session.revealed[index] = True
        
        view = GameBoardView(self, session)
        await interaction.message.edit(view=view)

        if card_type == "assassin":
            winner = "blue" if session.turn == "red" else "red"
            await interaction.channel.send(f"💥 **بوم!** {player.mention} كشف القاتل!\n🏆 فاز الفريق { 'الأزرق 🔵' if winner == 'blue' else 'الأحمر 🔴' }!")
            session.game_active = False
        elif card_type == "neutral":
            await interaction.response.send_message(f"😐 مواطن بريء.", ephemeral=False)
            self.switch_turn(interaction.channel, session)
        elif card_type != session.turn:
            await interaction.response.send_message(f"😱 كشف بطاقة للخصم!", ephemeral=False)
            self.check_win(interaction.channel, session)
            if session.game_active: self.switch_turn(interaction.channel, session)
        else:
            await interaction.response.send_message(f"✅ كفو! صح.", ephemeral=False)
            self.check_win(interaction.channel, session)

    async def pass_turn(self, interaction, session):
        player = interaction.user
        current_team = session.red_team if session.turn == "red" else session.blue_team
        current_spy = session.red_spymaster if session.turn == "red" else session.blue_spymaster

        if player not in current_team: return await interaction.response.send_message("✋ ليس دورك!", ephemeral=True)
        if player == current_spy: return await interaction.response.send_message("🤫 القائد ما ينهي الدور.", ephemeral=True)
        
        await interaction.response.send_message(f"🏳️ **{player.display_name}** أنهى الدور.", ephemeral=False)
        self.switch_turn(interaction.channel, session)

    def switch_turn(self, channel, session):
        session.turn = "blue" if session.turn == "red" else "red"
        asyncio.create_task(channel.send(f"🔄 الدور للفريق **{ 'الأحمر 🔴' if session.turn == 'red' else 'الأزرق 🔵' }**."))

    def check_win(self, channel, session):
        red_left = sum(1 for i in range(25) if not session.revealed[i] and session.key[i] == "red")
        blue_left = sum(1 for i in range(25) if not session.revealed[i] and session.key[i] == "blue")
        
        if red_left == 0:
            asyncio.create_task(channel.send("🎉 **الأحمر 🔴 فاز!** 🏆"))
            session.game_active = False
        elif blue_left == 0:
            asyncio.create_task(channel.send("🎉 **الأزرق 🔵 فاز!** 🏆"))
            session.game_active = False

# --- Views ---
class LobbyView(discord.ui.View):
    def __init__(self, cog, session, txt):
        super().__init__(timeout=None)
        self.cog = cog
        self.session = session
        # نصوص الأزرار من الداشبورد
        self.children[1].label = txt.get('btn_join', "انضمام")
        self.children[2].label = txt.get('btn_start', "بدء اللعب")

    @discord.ui.select(placeholder="⚙️ الإعدادات", options=[
        discord.SelectOption(label="نمط: كلمات", value="classic", emoji="📜"),
        discord.SelectOption(label="نمط: إيموجي", value="emoji", emoji="🤡"),
        discord.SelectOption(label="فرق: عشوائي", value="random", emoji="🎲"),
        discord.SelectOption(label="فرق: يدوي", value="manual", emoji="✋"),
    ])
    async def select_callback(self, interaction, select):
        if interaction.user != self.session.host: return await interaction.response.send_message("بس المنظم!", ephemeral=True)
        val = select.values[0]
        if val in ["classic", "emoji"]: self.session.mode = val
        elif val in ["random", "manual"]: self.session.team_method = val
        await interaction.response.edit_message(content="تم التحديث!", view=self)

    @discord.ui.button(style=discord.ButtonStyle.success)
    async def join(self, interaction, button):
        if interaction.user in self.session.players: return await interaction.response.send_message("مسجل!", ephemeral=True)
        self.session.players.append(interaction.user)
        embed = interaction.message.embeds[0]
        players_str = ", ".join([p.display_name for p in self.session.players])
        embed.set_field_at(0, name=f"اللاعبون ({len(self.session.players)})", value=players_str, inline=False) if embed.fields else embed.add_field(name=f"اللاعبون ({len(self.session.players)})", value=players_str, inline=False)
        await interaction.message.edit(embed=embed)
        await interaction.response.send_message("تم!", ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.primary)
    async def start(self, interaction, button):
        if interaction.user != self.session.host: return await interaction.response.send_message("بس المنظم!", ephemeral=True)
        await self.cog.initiate_game_start(interaction, self.session)

class TeamSelectionView(discord.ui.View):
    def __init__(self, cog, session):
        super().__init__(timeout=None)
        self.cog = cog
        self.session = session

    @discord.ui.button(label="🔴 أحمر", style=discord.ButtonStyle.danger)
    async def join_red(self, interaction, button):
        if interaction.user not in self.session.red_team:
            if interaction.user in self.session.blue_team: self.session.blue_team.remove(interaction.user)
            self.session.red_team.append(interaction.user)
            await self.update_msg(interaction)
        else: await interaction.response.send_message("أنت هنا!", ephemeral=True)

    @discord.ui.button(label="🔵 أزرق", style=discord.ButtonStyle.primary)
    async def join_blue(self, interaction, button):
        if interaction.user not in self.session.blue_team:
            if interaction.user in self.session.red_team: self.session.red_team.remove(interaction.user)
            self.session.blue_team.append(interaction.user)
            await self.update_msg(interaction)
        else: await interaction.response.send_message("أنت هنا!", ephemeral=True)

    @discord.ui.button(label="✅ تأكيد", style=discord.ButtonStyle.success, row=1)
    async def confirm(self, interaction, button):
        if interaction.user != self.session.host: return
        if not self.session.red_team or not self.session.blue_team: return await interaction.response.send_message("الفرق ناقصة!", ephemeral=True)
        await interaction.message.delete()
        await self.cog.finalize_setup(interaction.channel, self.session)

    async def update_msg(self, interaction):
        embed = discord.Embed(title="تكوين الفرق", color=discord.Color.light_grey())
        embed.add_field(name=f"🔴 ({len(self.session.red_team)})", value="\n".join([p.display_name for p in self.session.red_team]) or "-")
        embed.add_field(name=f"🔵 ({len(self.session.blue_team)})", value="\n".join([p.display_name for p in self.session.blue_team]) or "-")
        await interaction.response.edit_message(embed=embed, view=self)

class GameBoardView(discord.ui.View):
    def __init__(self, cog, session):
        super().__init__(timeout=None)
        self.cog = cog
        self.session = session
        for i in range(25):
            label = self.session.board[i]
            style = discord.ButtonStyle.secondary
            disabled = False
            if self.session.revealed[i]:
                disabled = True
                ct = self.session.key[i]
                if ct == "red": style = discord.ButtonStyle.danger
                elif ct == "blue": style = discord.ButtonStyle.primary
                elif ct == "neutral": label = "😐"
                elif ct == "assassin": label = "💀"
            btn = discord.ui.Button(label=str(label), style=style, disabled=disabled, row=i//5)
            btn.callback = self.create_callback(i)
            self.add_item(btn)

    def create_callback(self, idx):
        async def callback(interaction):
            if not self.session.game_active: return await interaction.response.send_message("انتهت!", ephemeral=True)
            await self.cog.process_click(interaction, self.session, idx)
        return callback

class GameControlView(discord.ui.View):
    def __init__(self, cog, session):
        super().__init__(timeout=None)
        self.cog = cog
        self.session = session

    @discord.ui.button(label="🏳️ إنهاء الدور", style=discord.ButtonStyle.grey)
    async def pass_turn(self, interaction, button):
        await self.cog.pass_turn(interaction, self.session)

    @discord.ui.button(label="👁️ أنا القائد", style=discord.ButtonStyle.blurple)
    async def show_key(self, interaction, button):
        if interaction.user not in [self.session.red_spymaster, self.session.blue_spymaster]:
            return await interaction.response.send_message("للقادة فقط!", ephemeral=True)
        await interaction.response.send_message(f"🤫 **الخريطة:**\n{self.cog.generate_map_string(self.session)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(CodenamesGame(bot))