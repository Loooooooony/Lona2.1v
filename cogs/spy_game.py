import discord
from discord.ext import commands
import asyncio
import random
import math
import json
import sys
import os

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.data_manager import get_guild_file

# --- 🌍 مواضيع عامة (Global) ---
TOPICS = {
    "أماكن عامة": ["مستشفى 🏥", "مدرسة 🏫", "سجن 👮", "مطار ✈️", "حلاق 💇‍♂️", "مطعم 🍽️", "سوك (سوق) 🛒", "سينما 🍿", "مدينة ألعاب 🎡", "ملعب ⚽"],
    "أكلات": ["بيتزا 🍕", "دولمة 🥘", "فلافل 🥙", "سمك مسكوف 🐟", "اندومي 🍜", "بيض سلق 🥚", "شاورما 🌯", "باجة 🐑", "رقي 🍉", "قيمة 🍲"],
    "حيوانات": ["أسد 🦁", "بزونة 🐱", "كلب 🐕", "صرصر 🪳", "طلي 🐑", "دجاجة 🐔", "حية 🐍", "فيل 🐘", "سمكة 🐠", "قرد 🐒"],
    "أشياء بالبيت": ["ثلاجة ❄️", "تلفزيون 📺", "صوبة 🔥", "مبرد 💨", "مراية 🪞", "سرير 🛌", "غسالة 🧺", "نعال 🩴", "شاحنة 🔌", "كنتور 🚪"],
    "وظائف": ["دكتور 👨‍⚕️", "شرطي 👮", "معلم 👨‍🏫", "سائق تكسي 🚕", "خباز 🍞", "عامل بناء 🧱", "طبيب أسنان 🦷", "جندي 🪖", "طيار ✈️"]
}

class GameSession:
    def __init__(self, guild_id):
        self.game_active = False
        self.players = []
        self.host = None
        self.imposter = None
        self.secret_word = None
        self.category = None
        self.current_turn = None
        self.innocent_kicked = 0
        self.max_mistakes = 0
        self.vote_in_progress = False
        self.game_mode = "classic"
        self.turn_order = []
        self.round_count = 0
        self.guild_id = guild_id

class SpyGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}

    def get_session(self, channel_id, guild_id):
        if channel_id not in self.sessions:
            self.sessions[channel_id] = GameSession(guild_id)
        return self.sessions[channel_id]

    def clear_session(self, channel_id):
        if channel_id in self.sessions:
            del self.sessions[channel_id]

    # جلب النصوص من ملف الاعدادات
    def get_text(self, guild_id):
        path = get_guild_file(guild_id, 'games_config.json')
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f).get('spyfall', {})
        except: return {}

    # --- 1️⃣ اللوبي ---
    @commands.command(name='spy', aliases=["برا_السالفة"])
    async def start_spy(self, ctx):
        session = self.get_session(ctx.channel.id, ctx.guild.id)
        if session.game_active:
            await ctx.send("اكو لعبة شغالة بهالقناة! كملوها بالأول 🕵️‍♂️")
            return

        # تصفير البيانات
        session = GameSession(ctx.guild.id)
        self.sessions[ctx.channel.id] = session
        session.host = ctx.author
        session.players = [ctx.author]

        # قراءة الإعدادات
        txt = self.get_text(ctx.guild.id)
        title = txt.get('title', "🕵️‍♂️ لعبة برا السالفة")
        desc = txt.get('description', "واحد منكم جاسوس! والباقين يعرفون السالفة.")
        color = int(txt.get('color', '#f1c40f').replace('#', ''), 16)

        embed = discord.Embed(title=title, description=desc, color=color)
        embed.set_footer(text=f"المنظم: {session.host.display_name}")
        
        view = LobbyView(self, session, txt)
        view.message = await ctx.send(embed=embed, view=view)

    # --- 2️⃣ بدء اللعبة ---
    async def start_game_logic(self, channel):
        session = self.get_session(channel.id, channel.guild.id)
        if len(session.players) < 3:
            await channel.send("⚠️ لازم 3 لاعبين عالأقل!")
            return

        session.game_active = True
        session.category = random.choice(list(TOPICS.keys()))
        session.secret_word = random.choice(TOPICS[session.category])
        session.imposter = random.choice(session.players)
        session.max_mistakes = 1 if len(session.players) <= 4 else 2

        view = RoleRevealView(self, session)
        await channel.send(f"🚨 **بدأت اللعبة!**\nالكل يضغط الزر جوة حتى يشوف دوره 👇", view=view)
        
        await asyncio.sleep(10)
        await channel.send(
            f"💡 **تلميح:** الموضوع هو **({session.category})**\n"
            f"لكشف الجاسوس: اكتبوا `تصويت` ولازم {math.ceil(len(session.players)/3)} يوافقون."
        )
        
        if session.game_mode == "classic":
            first_player = random.choice(session.players)
            await self.start_classic_turn(channel, first_player)
        else:
            session.turn_order = session.players.copy()
            random.shuffle(session.turn_order)
            session.round_count = 0
            await channel.send(f"🎤 **ترتيب الوصف:**\n{' -> '.join([p.display_name for p in session.turn_order])}")
            await self.start_desc_round(channel)

    # --- باقي منطق اللعبة (نفسه) ---
    async def start_classic_turn(self, channel, player):
        session = self.get_session(channel.id, channel.guild.id)
        if not session.game_active: return
        session.current_turn = player
        view = PickVictimView(self, session, player)
        await channel.send(f"🎤 **دور {player.mention}!**\nاختار واحد تسأله 👇", view=view)

    async def execute_question_phase(self, channel, asker, victim):
        session = self.get_session(channel.id, channel.guild.id)
        if not session.game_active: return
        await channel.send(f"⚔️ **تحقيق!**\n{asker.mention} 🗣️ يسأل ----> {victim.mention}\n⏳ **45 ثانية للنقاش...**")
        await asyncio.sleep(45)
        if session.game_active and not session.vote_in_progress:
            await channel.send(f"🔔 **انتهى الوقت!**\nهسة دور {victim.mention} يسأل! 😈")
            await self.start_classic_turn(channel, victim)

    async def start_desc_round(self, channel):
        session = self.get_session(channel.id, channel.guild.id)
        session.round_count += 1
        await channel.send(f"🌀 **الجولة رقم {session.round_count}** بدأت!")
        
        for player in session.turn_order:
            if not session.game_active: return
            if player not in session.players:
                await channel.send(f"🚫 {player.display_name} مطرود، نعبر دوره.")
                continue 
            
            session.current_turn = player
            await channel.send(f"💬 **دور {player.mention}**.. أوصف الكلمة! (اكتب بالشات)")
            
            def check(m): return m.author == player and m.channel.id == channel.id
            try:
                msg = await self.bot.wait_for('message', timeout=30.0, check=check)
                await msg.add_reaction("✅")
            except asyncio.TimeoutError:
                if player in session.players and session.game_active:
                     await channel.send(f"😴 {player.display_name} نام! نعبره.")
        
        if session.round_count == 2 and session.game_active:
            await channel.send("🕵️‍♂️ **انتهت جولتين!**\nاذا الجاسوس ذكي وكدر يعرف الكلمة، يكدر يحسم اللعبة هسة 👇", view=SpyGuessTriggerView(self, session))
            await asyncio.sleep(5)
            if session.game_active: await self.start_desc_round(channel)
        elif session.game_active:
            await self.start_desc_round(channel)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        if message.channel.id not in self.sessions: return

        session = self.get_session(message.channel.id, message.guild.id)
        if not session.game_active: return
        if session.vote_in_progress: return

        if message.content.strip() in ["تصويت", "vote"]:
            if message.author not in session.players: return
            session.vote_in_progress = True
            required = math.ceil(len(session.players) / 3)
            msg = await message.channel.send(f"🚨 **طلب تصويت!**\nنحتاج **{required}** لاعبين يسوون رياكشن 🗳️ للموافقة!")
            await msg.add_reaction("🗳️")

            def check(reaction, user):
                return str(reaction.emoji) == "🗳️" and user in session.players and reaction.message.id == msg.id

            voters = set()
            try:
                end_time = asyncio.get_event_loop().time() + 20
                while True:
                    timeout = end_time - asyncio.get_event_loop().time()
                    if timeout <= 0: break
                    try:
                        reaction, user = await self.bot.wait_for('reaction_add', timeout=timeout, check=check)
                        voters.add(user.id)
                        if len(voters) >= required:
                            await message.channel.send("✅ **تمت الموافقة!** جاري فتح التصويت...")
                            await self.start_actual_vote(message.channel, session)
                            return
                    except asyncio.TimeoutError: break
            except: pass
            
            session.vote_in_progress = False
            await msg.edit(content="❌ **فشل الطلب!** محد عبركم.. كملوا لعب.")

    async def start_actual_vote(self, channel, session):
        view = VoteView(self, session)
        view.message = await channel.send(f"🗳️ **منو الجاسوس؟**\n⚠️ التصويت يخلص بسرعة!", view=view)

    @commands.command(name="نفي", aliases=["انف"])
    async def kick_player(self, ctx, member: discord.Member):
        session = self.get_session(ctx.channel.id, ctx.guild.id)
        if not session.game_active: return
        if ctx.author != session.host: return await ctx.send("بس المضيف يكدر يطرد! 😒")
        if member not in session.players: return

        if member == session.imposter:
            await ctx.send(f"🔨 **تم نفي {member.mention}!** وجان هو **الجاسوس**! 😱\n🎉 **فازوا المواطنين!**")
            session.game_active = False
            return

        session.players.remove(member)
        await ctx.send(f"🔨 **تم نفي {member.mention}!** الله وياك.")

        if len(session.players) < 3:
            await ctx.send("🚫 **انتهت اللعبة!** عدد اللاعبين صار قليل. فاز الجاسوس.")
            session.game_active = False

    async def process_elimination(self, interaction, session, victim):
        if victim == session.imposter:
            await interaction.channel.send(f"🎉 **صدتوه!**\nالجاسوس {victim.mention} والكلمة **{session.secret_word}**! ✅")
            session.game_active = False
        else:
            session.innocent_kicked += 1
            remaining = session.max_mistakes - session.innocent_kicked
            await interaction.channel.send(f"😱 **ظلمتوه!** {victim.mention} بريء! 😭")
            if victim in session.players: session.players.remove(victim)

            if remaining <= 0:
                await interaction.channel.send(f"🏴 **خسرتوا!** فاز الجاسوس {session.imposter.mention} 😈")
                session.game_active = False
            else:
                await interaction.channel.send(f"⚠️ باقي محاولات: **{remaining}**")
                if session.game_mode == "classic":
                    next_p = random.choice(session.players)
                    await self.start_classic_turn(interaction.channel, next_p)
        
        session.vote_in_progress = False

# --- Views ---
class LobbyView(discord.ui.View):
    def __init__(self, cog, session, txt):
        super().__init__(timeout=None)
        self.cog = cog
        self.session = session
        self.txt = txt
        self.update_mode_select()

        # أزرار الداشبورد
        join_txt = txt.get('btn_join', "دخول")
        start_txt = txt.get('btn_start', "بدء")
        
        self.add_item(discord.ui.Button(label=join_txt, style=discord.ButtonStyle.green, emoji="🏃‍♂️", custom_id="join_btn"))
        self.add_item(discord.ui.Button(label="شرح اللعبة", style=discord.ButtonStyle.grey, emoji="📜", custom_id="help_btn"))
        self.add_item(discord.ui.Button(label=start_txt, style=discord.ButtonStyle.blurple, emoji="🚀", custom_id="start_btn"))

        # ربط الـ Callbacks
        for child in self.children:
            if child.custom_id == "join_btn": child.callback = self.join
            elif child.custom_id == "help_btn": child.callback = self.help_btn
            elif child.custom_id == "start_btn": child.callback = self.start

    def update_mode_select(self):
        for item in self.children:
            if isinstance(item, discord.ui.Select): self.remove_item(item)
        
        select = discord.ui.Select(
            placeholder="اختار نوع اللعبة (للمنظم فقط)",
            options=[
                discord.SelectOption(label="مود الأسئلة (كلاسيك)", value="classic", emoji="🎤", default=self.session.game_mode=="classic"),
                discord.SelectOption(label="مود الوصف الخفي", value="desc", emoji="🕵️", default=self.session.game_mode=="desc")
            ]
        )
        select.callback = self.mode_callback
        self.add_item(select)

    async def mode_callback(self, interaction: discord.Interaction):
        if interaction.user != self.session.host: return await interaction.response.send_message("بس المنظم!", ephemeral=True)
        self.session.game_mode = interaction.data['values'][0]
        self.update_mode_select()
        await interaction.response.edit_message(view=self)

    async def join(self, interaction: discord.Interaction):
        if interaction.user in self.session.players: return await interaction.response.send_message("انت موجود!", ephemeral=True)
        self.session.players.append(interaction.user)
        embed = interaction.message.embeds[0]
        players_str = "\n".join([p.mention for p in self.session.players])
        embed.set_field_at(0, name=f"اللاعبين ({len(self.session.players)})", value=players_str, inline=False) if embed.fields else embed.add_field(name=f"اللاعبين ({len(self.session.players)})", value=players_str, inline=False)
        await interaction.message.edit(embed=embed)
        await interaction.response.send_message("تم!", ephemeral=True)

    async def help_btn(self, interaction: discord.Interaction):
        msg = "**📜 طريقة اللعب:**\n1. **مود الأسئلة:** كل واحد يسأل الثاني.\n2. **مود الوصف:** كل واحد يوصف الكلمة."
        await interaction.response.send_message(msg, ephemeral=True)

    async def start(self, interaction: discord.Interaction):
        if interaction.user != self.session.host: return
        await interaction.message.delete()
        await self.cog.start_game_logic(interaction.channel)

class RoleRevealView(discord.ui.View):
    def __init__(self, cog, session):
        super().__init__(timeout=None)
        self.cog = cog
        self.session = session

    @discord.ui.button(label="👁️ اضغط لكشف دورك", style=discord.ButtonStyle.grey)
    async def reveal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.session.players: return await interaction.response.send_message("مو باللعبة!", ephemeral=True)
        if interaction.user == self.session.imposter:
            msg = f"🤫 **أنت الجاسوس!**\nالموضوع: **{self.session.category}**"
        else:
            msg = f"💡 **أنت مواطن!**\nالموضوع: {self.session.category}\nكلمة السر: **{self.session.secret_word}**"
        await interaction.response.send_message(msg, ephemeral=True)

class PickVictimView(discord.ui.View):
    def __init__(self, cog, session, asker):
        super().__init__(timeout=None)
        self.cog = cog
        self.session = session
        self.asker = asker
        for player in [p for p in session.players if p != asker]:
            btn = discord.ui.Button(label=player.display_name, style=discord.ButtonStyle.secondary)
            btn.callback = self.create_callback(player)
            self.add_item(btn)

    def create_callback(self, victim):
        async def callback(interaction: discord.Interaction):
            if interaction.user != self.asker: return
            self.stop()
            await interaction.message.delete()
            await self.cog.execute_question_phase(interaction.channel, self.asker, victim)
        return callback

class SpyGuessTriggerView(discord.ui.View):
    def __init__(self, cog, session):
        super().__init__(timeout=None)
        self.cog = cog
        self.session = session

    @discord.ui.button(label="أنا الجاسوس! (تخمين)", style=discord.ButtonStyle.danger, emoji="🕵️‍♂️")
    async def guess_trigger(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.session.game_active or self.session.vote_in_progress: return
        if interaction.user != self.session.imposter: return await interaction.response.send_message("استريح!", ephemeral=True)
        
        options = [self.session.secret_word]
        wrong = [w for w in TOPICS[self.session.category] if w != self.session.secret_word]
        options.extend(random.sample(wrong, min(4, len(wrong))))
        random.shuffle(options)
        
        view = SpyDecoyView(self.cog, self.session, options)
        await interaction.response.send_message("🤫 **اختار الكلمة:**", view=view, ephemeral=True)

class SpyDecoyView(discord.ui.View):
    def __init__(self, cog, session, options):
        super().__init__(timeout=None)
        self.cog = cog
        self.session = session
        for word in options:
            btn = discord.ui.Button(label=word, style=discord.ButtonStyle.primary)
            btn.callback = self.create_callback(word)
            self.add_item(btn)

    def create_callback(self, word):
        async def callback(interaction: discord.Interaction):
            if not self.session.game_active: return
            if word == self.session.secret_word:
                await interaction.channel.send(f"🎉 **فاز الجاسوس!** عرف الكلمة ({word}) 🏆")
            else:
                await interaction.channel.send(f"🚑 **خسر الجاسوس!** خمن غلط ({word}). الكلمة جانت **{self.session.secret_word}**.")
            self.session.game_active = False
            self.stop()
        return callback

class VoteView(discord.ui.View):
    def __init__(self, cog, session):
        super().__init__(timeout=None)
        self.cog = cog
        self.session = session
        self.votes = {}
        self.timer_started = False
        options = [discord.SelectOption(label=p.display_name, value=str(p.id)) for p in session.players]
        select = discord.ui.Select(placeholder="اختر الجاسوس...", options=options)
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id in self.votes: return await interaction.response.send_message("صوتت قبل!", ephemeral=True)
        self.votes[interaction.user.id] = int(interaction.data['values'][0])
        await interaction.response.send_message("تم 🗳️", ephemeral=True)
        
        if len(self.votes) >= len(self.session.players) / 2 and not self.timer_started:
            self.timer_started = True
            await interaction.channel.send("⏳ **باقي 20 ثانية!**")
            asyncio.create_task(self.start_rush_timer(interaction))
        
        if len(self.votes) >= len(self.session.players): await self.calculate_final(interaction)

    async def start_rush_timer(self, interaction):
        await asyncio.sleep(20)
        if self.session.vote_in_progress: await self.calculate_final(interaction)

    async def calculate_final(self, interaction):
        self.stop()
        if not self.votes: return
        counts = {}
        for vid in self.votes.values(): counts[vid] = counts.get(vid, 0) + 1
        winner_id = max(counts, key=counts.get)
        victim = interaction.guild.get_member(winner_id)
        if hasattr(self, 'message'): await self.message.delete()
        await interaction.channel.send(f"🛑 **قرار المحكمة:** الكل ضد {victim.mention}")
        await self.cog.process_elimination(interaction, self.session, victim)

async def setup(bot):
    await bot.add_cog(SpyGame(bot))
