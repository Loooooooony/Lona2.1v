import discord
from discord.ext import commands
import json
import random
import asyncio
from difflib import SequenceMatcher

# --- ⚙️ إعدادات الوقت (ثواني) ---
FACE_OFF_TIME = 20
TURN_TIME = 15
STEAL_TIME = 20

# --- 🛠️ دالة لجلب اسم الأمر من الملف ---
def get_command_name():
    try:
        with open('data/games_config.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('family', {}).get('command_name', 'family')
    except: return 'family'

def check_similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

# --- 🎛️ كلاس 1: قائمة الإعدادات (Setup Menu) ---
class SetupView(discord.ui.View):
    def __init__(self, ctx, organizer, txt):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.organizer = organizer
        self.txt = txt # نصوص الداشبورد
        self.team_size = 4
        self.mode = "MANUAL"
        self.confirmed = False

    def update_embed(self):
        # هنا نستخدم العنوان واللون من الداشبورد
        title = self.txt.get('title', "👨‍👩‍👧‍👦 عائلتي تربح")
        color = int(self.txt.get('color', '#f1c40f').replace('#', ''), 16)
        
        embed = discord.Embed(title=f"⚙️ إعدادات: {title}", description="يا منظم، اختار إعدادات الجولة:", color=color)
        embed.add_field(name="👥 حجم الفرق", value=f"**{self.team_size} ضد {self.team_size}**", inline=True)
        mode_text = "يدوي (اللاعب يختار)" if self.mode == "MANUAL" else "عشوائي (البوت يوزع)"
        embed.add_field(name="🔀 التوزيع", value=f"**{mode_text}**", inline=True)
        embed.set_footer(text="عدل الخيارات واضغط تأكيد ✅")
        return embed

    @discord.ui.button(label="تغيير العدد 👥", style=discord.ButtonStyle.secondary)
    async def toggle_size(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.organizer.id: return
        if self.team_size == 2: self.team_size = 4
        elif self.team_size == 4: self.team_size = 6
        else: self.team_size = 2
        await interaction.response.edit_message(embed=self.update_embed(), view=self)

    @discord.ui.button(label="تغيير النمط 🔀", style=discord.ButtonStyle.secondary)
    async def toggle_mode(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.organizer.id: return
        self.mode = "RANDOM" if self.mode == "MANUAL" else "MANUAL"
        await interaction.response.edit_message(embed=self.update_embed(), view=self)

    @discord.ui.button(label="تأكيد وبدء ✅", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.organizer.id: return
        self.confirmed = True
        self.stop()
        await interaction.response.defer()

# --- 🚪 كلاس 2: اللوبي (Lobby) ---
class GameLobbyView(discord.ui.View):
    def __init__(self, ctx, organizer, team_size, mode, txt):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.organizer = organizer
        self.team_size = team_size
        self.mode = mode
        self.txt = txt # نصوص الداشبورد
        
        self.red_team = []
        self.blue_team = []
        self.pool = []
        self.started = False

        self.setup_buttons()

    def setup_buttons(self):
        self.clear_items()
        
        # زر التعليمات
        self.add_item(discord.ui.Button(label="📜 التعليمات", style=discord.ButtonStyle.gray, custom_id="help_btn"))

        # نصوص الأزرار من الداشبورد
        join_txt = self.txt.get('btn_join', "تسجيل")
        start_txt = self.txt.get('btn_start', "انطلاق")

        if self.mode == "MANUAL":
            self.add_item(discord.ui.Button(label=f"🔴 {join_txt} أحمر", style=discord.ButtonStyle.danger, custom_id="join_red"))
            self.add_item(discord.ui.Button(label=f"🔵 {join_txt} أزرق", style=discord.ButtonStyle.primary, custom_id="join_blue"))
        else:
            self.add_item(discord.ui.Button(label=f"✋ {join_txt}", style=discord.ButtonStyle.success, custom_id="join_pool"))

        # زر البدء
        self.add_item(discord.ui.Button(label=f"🚀 {start_txt}", style=discord.ButtonStyle.success, custom_id="start_game", row=1))

    def update_embed(self):
        # قراءة النصوص والألوان
        title = self.txt.get('title', "🔥 ساحة الانتظار")
        desc = self.txt.get('description', "المطلوب: لاعبين لكل فريق.")
        color = int(self.txt.get('color', '#ffd700').replace('#', ''), 16)

        embed = discord.Embed(title=title, description=desc, color=color)
        
        if self.mode == "MANUAL":
            red_txt = "\n".join([f"<@{u}>" for u in self.red_team]) if self.red_team else "..."
            blue_txt = "\n".join([f"<@{u}>" for u in self.blue_team]) if self.blue_team else "..."
            embed.add_field(name=f"🔴 الأحمر ({len(self.red_team)}/{self.team_size})", value=red_txt, inline=True)
            embed.add_field(name=f"🔵 الأزرق ({len(self.blue_team)}/{self.team_size})", value=blue_txt, inline=True)
        else:
            pool_txt = "\n".join([f"<@{u}>" for u in self.pool]) if self.pool else "..."
            total_needed = self.team_size * 2
            embed.add_field(name=f"📋 المسجلين ({len(self.pool)}/{total_needed})", value=pool_txt, inline=False)
            
        embed.set_footer(text=f"المنظم: {self.organizer.display_name}")
        return embed

    async def interaction_check(self, interaction: discord.Interaction):
        custom_id = interaction.data["custom_id"]

        if custom_id == "help_btn":
            msg = "**📜 القوانين:**\nأي جواب لازم يبدأ بـ نقطة `.` (مثال: `.جواب`)"
            await interaction.response.send_message(msg, ephemeral=True)
            return False

        if custom_id == "start_game":
            if interaction.user.id != self.organizer.id:
                await interaction.response.send_message("بس المنظم!", ephemeral=True)
                return False
            
            if self.mode == "MANUAL":
                if not self.red_team or not self.blue_team:
                    await interaction.response.send_message("الفرق ناقصة!", ephemeral=True)
                    return False
            else:
                if len(self.pool) < 2:
                    await interaction.response.send_message("العدد قليل!", ephemeral=True)
                    return False
                random.shuffle(self.pool)
                mid = len(self.pool) // 2
                self.red_team = self.pool[:mid]
                self.blue_team = self.pool[mid:]
            
            self.started = True
            for item in self.children: item.disabled = True
            await interaction.response.edit_message(content="✅ **انطلقت اللعبة!**", view=self)
            self.stop()
            return False

        user_id = interaction.user.id
        if custom_id == "join_red":
            if user_id in self.blue_team: self.blue_team.remove(user_id)
            if user_id not in self.red_team: 
                if len(self.red_team) >= self.team_size: return await interaction.response.send_message("ممتلئ!", ephemeral=True)
                self.red_team.append(user_id)
        
        elif custom_id == "join_blue":
            if user_id in self.red_team: self.red_team.remove(user_id)
            if user_id not in self.blue_team:
                if len(self.blue_team) >= self.team_size: return await interaction.response.send_message("ممتلئ!", ephemeral=True)
                self.blue_team.append(user_id)
        
        elif custom_id == "join_pool":
            if user_id not in self.pool:
                if len(self.pool) >= self.team_size * 2: return await interaction.response.send_message("اكتمل!", ephemeral=True)
                self.pool.append(user_id)
            else: return await interaction.response.send_message("مسجل!", ephemeral=True)

        await interaction.response.edit_message(embed=self.update_embed(), view=self)
        return False

# --- 🧠 محرك اللعبة (Game Engine) ---
class GameSession:
    def __init__(self, ctx, red_team, blue_team, questions):
        self.ctx = ctx
        self.red_team = red_team
        self.blue_team = blue_team
        self.questions = questions
        self.scores = {"red": 0, "blue": 0}
        self.current_q = None
        self.revealed_answers = [] 
        self.bank_points = 0
        self.strikes = 0
        self.controlling_team = None 

    def get_board_embed(self, title_prefix=""):
        q_text = self.current_q["question"]
        color = 0xff0000 if self.controlling_team == "red" else 0x0000ff if self.controlling_team == "blue" else 0xffffff
        embed = discord.Embed(title=f"{title_prefix} {q_text}", color=color)
        
        board_str = ""
        for i, (ans_txt, pts) in enumerate(self.current_q["answers"], 1):
            if i in self.revealed_answers:
                board_str += f"✅ **{i}. {ans_txt}** ➔ ({pts})\n"
            else:
                board_str += f"⬜ **{i}.** ـــــ\n"
        
        embed.description = board_str
        strikes_emoji = "❌ " * self.strikes
        status = f"الدور: {self.controlling_team}" if self.controlling_team else "🔥 وجهًا لوجه"
        
        embed.add_field(name="💰 البنك", value=str(self.bank_points))
        embed.add_field(name="الأخطاء", value=strikes_emoji if self.strikes > 0 else "0")
        embed.set_footer(text=f"🔴 {self.scores['red']} | 🔵 {self.scores['blue']}")
        return embed

# --- ⚙️ الكوك الرئيسي ---
class FamilyFeud(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}
        self.games_config = 'data/games_config.json'

    # جلب النصوص من ملف الاعدادات
    def get_text(self):
        try:
            with open(self.games_config, 'r', encoding='utf-8') as f:
                return json.load(f).get('family', {})
        except: return {}

    # الأمر الديناميكي
    @commands.command(name=get_command_name(), aliases=["عائلتي"])
    async def start(self, ctx):
        if ctx.channel.id in self.active_games: return await ctx.send("اكو لعبة شغالة!")

        # تحميل النصوص
        txt = self.get_text()

        # 1. قائمة الإعدادات (Setup)
        setup_view = SetupView(ctx, ctx.author, txt)
        setup_msg = await ctx.send(embed=setup_view.update_embed(), view=setup_view)
        await setup_view.wait()

        if not setup_view.confirmed:
            return await ctx.send("تكنسل الإعداد.")
        
        await setup_msg.delete()

        # 2. اللوبي (Lobby)
        lobby_view = GameLobbyView(ctx, ctx.author, setup_view.team_size, setup_view.mode, txt)
        lobby_msg = await ctx.send(embed=lobby_view.update_embed(), view=lobby_view)
        await lobby_view.wait()
        
        if not lobby_view.started: return await ctx.send("تكنسلت اللعبة.")

        try:
            with open("data/questions.json", "r", encoding="utf-8") as f:
                qs = json.load(f)
            game_questions = random.sample(qs, min(3, len(qs)))
        except:
            return await ctx.send("ملف الأسئلة فارغ!")

        session = GameSession(ctx, lobby_view.red_team, lobby_view.blue_team, game_questions)
        self.active_games[ctx.channel.id] = session
        
        await ctx.send(f"🏆 **بدأت اللعبة!**\n⚠️ تذكير: الجواب يبدأ بنقطة `.`")
        await asyncio.sleep(2)
        await self.run_game_loop(session)

    # --- 🔄 باقي منطق اللعب (نفسه ما يحتاج تغيير) ---
    async def run_game_loop(self, session):
        for round_num in range(1, len(session.questions) + 1):
            session.current_q = session.questions.pop(0)
            session.revealed_answers = []
            session.bank_points = 0
            session.strikes = 0
            session.controlling_team = None
            
            winner = await self.phase_face_off(session)
            session.controlling_team = winner
            
            result = await self.phase_main_round(session)
            
            if result == "STRIKES":
                await self.phase_steal(session)
            
            await asyncio.sleep(3)
        
        await self.end_game(session)

    def make_check(self, session, allowed_teams=None):
        def check(m):
            if m.channel.id != session.ctx.channel.id or m.author.bot: return False
            if not m.content.startswith('.'): return False
            if allowed_teams:
                is_red = m.author.id in session.red_team
                is_blue = m.author.id in session.blue_team
                if "red" in allowed_teams and is_red: return True
                if "blue" in allowed_teams and is_blue: return True
                return False
            return m.author.id in session.red_team or m.author.id in session.blue_team
        return check

    async def phase_face_off(self, session):
        board = session.get_board_embed("🔔 سؤال السرعة:")
        await session.ctx.send(embed=board)
        await session.ctx.send(f"🔥 **وجهًا لوجه!** ({FACE_OFF_TIME} ثانية)\nاكتبوا `.جواب`")

        try:
            msg = await self.bot.wait_for('message', timeout=FACE_OFF_TIME, check=self.make_check(session, ["red", "blue"]))
            guess = msg.content[1:].strip() 
            team = "red" if msg.author.id in session.red_team else "blue"
            
            found_ans = None
            for i, (ans_txt, pts) in enumerate(session.current_q["answers"], 1):
                if guess == ans_txt or check_similarity(guess, ans_txt) > 0.75:
                    found_ans = {"pts": pts, "index": i, "text": ans_txt}
                    break
            
            if found_ans:
                session.revealed_answers.append(found_ans["index"])
                session.bank_points += found_ans["pts"]
                await msg.add_reaction("⚡")
                await session.ctx.send(f"⚡ **كفو!** التحكم للفريق **{team}**.")
                return team
            else:
                await session.ctx.send(f"❌ غلط! التحكم عشوائي.")
                return random.choice(["red", "blue"])

        except asyncio.TimeoutError:
            t = random.choice(["red", "blue"])
            await session.ctx.send(f"⏰ محد جاوب! التحكم للفريق **{t}**.")
            return t

    async def phase_main_round(self, session):
        while len(session.revealed_answers) < len(session.current_q["answers"]):
            await session.ctx.send(embed=session.get_board_embed())
            
            try:
                msg = await self.bot.wait_for('message', timeout=TURN_TIME, check=self.make_check(session, [session.controlling_team]))
                guess = msg.content[1:].strip()
                
                found_ans = None
                for i, (ans_txt, pts) in enumerate(session.current_q["answers"], 1):
                    if i in session.revealed_answers: continue
                    if guess == ans_txt or check_similarity(guess, ans_txt) > 0.75:
                        found_ans = {"pts": pts, "index": i, "text": ans_txt}
                        break
                
                if found_ans:
                    session.revealed_answers.append(found_ans["index"])
                    session.bank_points += found_ans["pts"]
                    await msg.add_reaction("✅")
                else:
                    session.strikes += 1
                    await msg.add_reaction("❌")
                    await session.ctx.send(f"❌ **غلط!** ({session.strikes}/3)")

            except asyncio.TimeoutError:
                session.strikes += 1
                await session.ctx.send(f"⏰ **تأخرتوا!** ({session.strikes}/3)")

            if session.strikes >= 3: return "STRIKES"
        
        session.scores[session.controlling_team] += session.bank_points
        await session.ctx.send(f"👏 **مسحتوا البورد!**")
        return "CLEARED"

    async def phase_steal(self, session):
        steal_team = "blue" if session.controlling_team == "red" else "red"
        await session.ctx.send(f"🚨 **فرصة للسرقة!** الفريق **{steal_team}**، عندكم فرصة وحدة!")

        try:
            msg = await self.bot.wait_for('message', timeout=STEAL_TIME, check=self.make_check(session, [steal_team]))
            guess = msg.content[1:].strip()
            
            found = False
            for i, (ans_txt, pts) in enumerate(session.current_q["answers"], 1):
                if i not in session.revealed_answers:
                    if guess == ans_txt or check_similarity(guess, ans_txt) > 0.75:
                        found = True
                        session.bank_points += pts
                        break
            
            if found:
                session.scores[steal_team] += session.bank_points
                await session.ctx.send(f"🥷 **نجحت السرقة!**")
            else:
                session.scores[session.controlling_team] += session.bank_points
                await session.ctx.send(f"🛡️ **فشلت السرقة!** النقاط رجعت.")

        except asyncio.TimeoutError:
             session.scores[session.controlling_team] += session.bank_points
             await session.ctx.send(f"⏰ خلص الوقت.")

    async def end_game(self, session):
        red = session.scores['red']
        blue = session.scores['blue']
        winner = "🔴 الأحمر" if red > blue else "🔵 الأزرق" if blue > red else "🤝 تعادل"
        
        embed = discord.Embed(title="👑 النتائج النهائية", description=f"الفائز: **{winner}**", color=0xffd700)
        embed.add_field(name="🔴 الأحمر", value=str(red))
        embed.add_field(name="🔵 الأزرق", value=str(blue))
        await session.ctx.send(embed=embed)
        del self.active_games[session.ctx.channel.id]

async def setup(bot):
    await bot.add_cog(FamilyFeud(bot))