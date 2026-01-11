import discord
from discord.ext import commands
import asyncio
import random
import time

class LunaGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.game_running = False

    @commands.command(name="لونا_قالت", aliases=["simon", "لعبة"])
    async def luna_says(self, ctx):
        if self.game_running:
            return await ctx.send("⛔ اكو لعبة شغالة! اصبروا شوية.")
        
        self.game_running = True
        
        embed = discord.Embed(
            title="🎮 لونا قالت (Luna Says)",
            description=(
                "**📜 القوانين الجديدة:**\n"
                "1. **القانون الذهبي:** نفذ الأمر **فقط** إذا بدأ بـ `لونا قالت` (أو 🟢).\n"
                "2. **التركيز:** انتبه من الفخاخ والأسماء المزيفة!\n"
                "3. **أسباب الموت:** اذا خسرت، البوت راح يكولك ليش (حتى لا تبجي وتكول ظلم) 😂\n\n"
                f"👑 **المنظم:** {ctx.author.mention}\n"
                "⏳ **اللعبة تبدأ بعد 20 ثانية...**"
            ),
            color=0xff0000
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name="👥 اللاعبين (0)", value="انتظار...", inline=False)
        
        view = JoinView(ctx.author, embed)
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg 
        
        await view.wait() 
        
        players = view.players
        if len(players) < 2: 
            self.game_running = False
            return await ctx.send("❌ ماكو لاعبين كفاية! (يراد 2 عالأقل) 🌚")
        
        await ctx.send(f"✅ **انطلقت اللعبة!** ({len(players)} لاعبين)\nيا ويلكم... ⚡")
        await asyncio.sleep(2)

        # --- 🔥 بداية الجحيم 🔥 ---
        round_num = 1
        last_modes = [] 
        last_was_trap = False 

        while len(players) > 0:
            all_modes = [
                "classic", "math", "odd_one_out", "true_false", 
                "massive", "ghost", "moving_target", "combo",   
                "liar", "spoiler", "color_mix", "needle",       
                "risk", "fusion", "sacrifice", "whisper"                                
            ]
            
            # اختيار المود بذكاء (منع التكرار)
            if round_num < 3: pool = ["classic", "math", "true_false", "odd_one_out"]
            else: pool = all_modes

            available_modes = [m for m in pool if m not in last_modes]
            if not available_modes: available_modes = pool; last_modes = []

            current_mode = random.choice(available_modes)
            last_modes.append(current_mode)
            if len(last_modes) > 3: last_modes.pop(0)

            if current_mode == "sacrifice" and len(players) < 3: current_mode = "classic"

            options = []      
            prompt = ""       
            correct_val = ""  
            special_logic = None 
            
            # تسريع الوقت تدريجياً
            base_time = 8.0
            reduction = (round_num * 0.4)
            view_timeout = max(4.0, base_time - reduction)

            # نظام الفخاخ
            is_trap = False
            trap_text_override = None 
            
            base_trap_chance = 0.3 if round_num < 5 else 0.5
            if last_was_trap: base_trap_chance = 0.1 

            safe_modes = ["risk", "liar", "sacrifice", "whisper", "ghost"]
            
            if random.random() < base_trap_chance and current_mode not in safe_modes:
                is_trap = True
                last_was_trap = True
                trap_type = random.choices(["no_prefix", "imposter", "typo"], weights=[40, 30, 30], k=1)[0]
                
                if trap_type == "imposter":
                    fake_name = random.choice(["مونا", "لورا", "نولا", "بونا", "تونا"])
                    trap_text_override = f"🔴 **{fake_name} قالت:**"
                elif trap_type == "typo":
                    bad_luna = random.choice(["لونا قاIت", "لونـا قالت", "لونا قاالت", "لونا كات"])
                    trap_text_override = f"🔴 **{bad_luna}:**"
                else: 
                    trap_text_override = f"🔴 **بسرعة:**"
            else:
                last_was_trap = False

            # --- إعداد المودات ---
            if current_mode == "classic":
                items = ["أحمر", "أزرق", "أخضر", "أصفر"]
                target = random.choice(items)
                prompt = f"اضغط على اللون **{target}**"
                correct_val = target
                colors = {"أحمر": discord.ButtonStyle.danger, "أزرق": discord.ButtonStyle.blurple, "أخضر": discord.ButtonStyle.success, "أصفر": discord.ButtonStyle.secondary}
                for i in items: options.append((i, colors[i], i))

            elif current_mode == "sacrifice":
                is_trap = False 
                prompt = "🔪 **ضحِّ بصديق! (اضغط اسم اللي تكرهه)**"
                correct_val = "sacrifice_mode"
                special_logic = "sacrifice"
                view_timeout = 8.0 
                targets = players[:5]
                if len(players) > 5: targets = random.sample(players, 5)
                for pid in targets:
                    user_obj = ctx.guild.get_member(pid)
                    u_name = user_obj.display_name if user_obj else "Unknown"
                    options.append((u_name, discord.ButtonStyle.danger, str(pid)))

            elif current_mode == "risk":
                # 🛑 التعديل رقم 5: تسهيل التوقيت للمجازفة
                # لازم ينتظرون الى ان يصير الوقت قليل
                prompt = "⏳ **انتظر... واضغط باللحظة الأخيرة!**"
                correct_val = "risk_pass"
                special_logic = "risk"
                options = [("💣 لا تضغط هسة", discord.ButtonStyle.danger, "bomb")]

            # ... (باقي المودات نفسها بالضبط كما في الكود السابق لتوفير المساحة، انسخيها من الكود القبله اذا تحبين، او اعيد كتابتها هنا؟)
            # للاختصار سأضع المودات الاساسية فقط مع التعديلات المطلوبة
            
            elif current_mode == "math":
                n1, n2 = random.randint(1, 10), random.randint(1, 10)
                ans = n1 + n2
                prompt = f"حل المعادلة: **{n1} + {n2}**"
                correct_val = str(ans)
                wrongs = [ans+1, ans-1, ans+2, ans-2]
                choices = [ans] + wrongs[:3]
                random.shuffle(choices)
                for c in choices: options.append((str(c), discord.ButtonStyle.secondary, str(c)))

            elif current_mode == "odd_one_out":
                prompt = "طلع **الغريب**!"
                groups = [(["🍎", "🍌", "🍇"], "🚗"), (["🐶", "🐱", "🦁"], "⏰"), (["⚽", "🏀", "🏐"], "💡")]
                grp = random.choice(groups)
                others, target = grp
                correct_val = target
                choices = others + [target]
                random.shuffle(choices)
                for c in choices: options.append((c, discord.ButtonStyle.secondary, c))
                
            elif current_mode == "true_false":
                facts = [("بغداد عاصمة العراق", "صح"), ("النار باردة", "خطأ"), ("1+1=11", "خطأ"), ("لونا روبوت", "صح")]
                fact, ans = random.choice(facts)
                prompt = f"**{fact}**.. صح لو غلط؟"
                correct_val = ans
                options = [("صح", discord.ButtonStyle.success, "صح"), ("خطأ", discord.ButtonStyle.danger, "خطأ")]

            elif current_mode == "massive":
                target = random.randint(1, 15)
                prompt = f"وين الرقم **{target}**؟"
                correct_val = str(target)
                nums = list(range(1, 16))
                random.shuffle(nums)
                for n in nums: options.append((str(n), discord.ButtonStyle.secondary, str(n)))
                view_timeout = 10.0

            elif current_mode == "ghost":
                prompt = "احفظ مكان **الأحمر** بسرعة!"
                correct_val = "أحمر"
                special_logic = "ghost"
                raw_opts = [("أحمر", discord.ButtonStyle.danger, "أحمر"), ("أزرق", discord.ButtonStyle.blurple, "أزرق"), ("أخضر", discord.ButtonStyle.success, "أخضر")]
                random.shuffle(raw_opts)
                options = raw_opts

            elif current_mode == "moving_target":
                prompt = "صيد **الموزة 🍌** بسرعة"
                correct_val = "🍌"
                special_logic = "moving"
                items = ["🍌", "🍎", "🍇", "🍉"]
                for i in items: options.append((i, discord.ButtonStyle.primary, i))

            elif current_mode == "combo":
                prompt = "اضغط بالتسلسل: **أحمر -> أزرق -> أحمر**"
                correct_val = "combo_done"
                special_logic = "combo"
                options = [("🔴", discord.ButtonStyle.danger, "🔴"), ("🔵", discord.ButtonStyle.blurple, "🔵"), ("🟢", discord.ButtonStyle.success, "🟢")]

            elif current_mode == "liar":
                real_target = "أزرق"
                fake_target = "أحمر"
                prompt = f"🤥 **أني كذابة.. اضغط {fake_target}!**" 
                correct_val = real_target 
                options = [("أحمر", discord.ButtonStyle.danger, "أحمر"), ("أزرق", discord.ButtonStyle.blurple, "أزرق")]

            elif current_mode == "spoiler":
                target = random.choice(["يمين ➡️", "يسار ⬅️"])
                prompt = f"افتح وشوف: || اضغط {target} ||"
                correct_val = target
                options = [("يمين ➡️", discord.ButtonStyle.primary, "يمين ➡️"), ("يسار ⬅️", discord.ButtonStyle.primary, "يسار ⬅️")]
            
            elif current_mode == "whisper":
                target = random.choice(["أحمر", "أزرق"])
                fake_target = "أخضر" if target != "أخضر" else "أحمر"
                prompt = f"🔊 **صيح: اضغط {fake_target}!**"
                correct_val = target
                special_logic = "whisper" 
                options = [("أحمر", discord.ButtonStyle.danger, "أحمر"), ("أزرق", discord.ButtonStyle.blurple, "أزرق"), ("أخضر", discord.ButtonStyle.success, "أخضر")]

            elif current_mode == "color_mix":
                prompt = "اخلط **أصفر + أزرق**.. شيطلع؟"
                correct_val = "خضر"
                options = [("خضر", discord.ButtonStyle.success, "خضر"), ("بنفسجي", discord.ButtonStyle.primary, "بنفسجي"), ("برتقالي", discord.ButtonStyle.secondary, "برتقالي")]

            elif current_mode == "needle":
                prompt = "اضغط على **القطوة الحزينة (😿)**"
                correct_val = "😿"
                cats = ["😺", "😸", "😹", "😻", "😼", "😽", "😿", "😾"]
                selection = random.sample([c for c in cats if c != "😿"], 4) + ["😿"]
                random.shuffle(selection)
                for c in selection: options.append((c, discord.ButtonStyle.secondary, c))

            elif current_mode == "fusion":
                prompt = "⚠️ **لا تضغط** ناتج 1+1"
                correct_val = "not_2" 
                special_logic = "fusion_negation"
                choices = ["2", "3", "4"]
                for c in choices: options.append((c, discord.ButtonStyle.primary, c))

            # --- صياغة الرسالة ---
            final_text = ""
            footer_text = "" 
            if special_logic == "whisper":
                final_text = prompt 
                footer_text = f"\n-# 🤫 لونا تهمس: لونا قالت اضغط {correct_val}"
            elif special_logic == "sacrifice":
                final_text = f"🟢 **لونا قالت:** {prompt}"
            elif current_mode == "liar":
                final_text = f"🟢 **لونا قالت:** {prompt}"
            elif is_trap:
                if trap_text_override: final_text = f"{trap_text_override} {prompt}"
                else: final_text = f"🔴 **بسرعة: {prompt}**"
            else:
                final_text = f"🟢 **لونا قالت:** {prompt}"

            view = GameView(players, correct_val, is_trap, special_logic, options)
            msg_content = f"🔥 **جولة {round_num}** ({int(view_timeout)}ث)\n# {final_text}{footer_text}"
            
            try:
                if special_logic == "ghost":
                    # زيادة وقت الشبح عشان اللاغ
                    msg = await ctx.send(f"👻 **جولة الأشباح!**\nاحفظ الأماكن... (4 ثواني)", view=view)
                    await asyncio.sleep(4)
                    view.turn_to_ghost()
                    await msg.edit(content=f"👻 **وين جان {correct_val}؟**\n# {final_text}{footer_text}", view=view)
                elif special_logic == "moving":
                    msg = await ctx.send(content=msg_content, view=view)
                    for _ in range(2):
                        await asyncio.sleep(1.5)
                        view.shuffle_buttons()
                        try: await msg.edit(view=view)
                        except: pass
                else:
                    msg = await ctx.send(content=msg_content, view=view)
            except: pass 
            
            view.start_time = time.time()
            await asyncio.sleep(view_timeout)
            view.stop()

            # --- 💀 الحكم والفرز (تعديل الأسباب) ---
            eliminated = {} # ديكشنري للاسم والسبب: {id: reason}
            
            sacrificed_victims = []
            if special_logic == "sacrifice":
                for p_id, (target_id, c_time) in view.player_clicks.items():
                    if target_id != str(p_id):
                        if target_id not in sacrificed_victims: sacrificed_victims.append(int(target_id))
            
            for p_id in players[:]:
                # 1. التضحية
                if p_id in sacrificed_victims:
                    eliminated[p_id] = "غدروا بيه"
                    players.remove(p_id)
                    continue

                click_data = view.player_clicks.get(p_id) 
                
                # 2. الفخاخ
                if is_trap:
                    if click_data is not None:
                        eliminated[p_id] = "وقع بالفخ"
                        players.remove(p_id)
                    continue

                # 3. ما ضغط شي
                if click_data is None:
                    if special_logic == "sacrifice": continue 
                    eliminated[p_id] = "انتهى الوقت" # او ما ضغط
                    players.remove(p_id)
                    continue
                
                val, c_time = click_data
                
                # 4. المودات الخاصة
                if special_logic == "combo":
                    if val is not True: 
                        eliminated[p_id] = "غلط بالتسلسل"
                        players.remove(p_id)
                
                elif special_logic == "risk":
                    elapsed = c_time - view.start_time
                    # 🛑 تسهيل التوقيت: نعطيه سماحية 2 ثانية قبل النهاية
                    # يعني اذا الوقت 7 ثواني، لازم يدوس بعد الثانية 5
                    # القديم كان (timeout - 2.5) هسة صار اكثر مرونة
                    safe_threshold = view_timeout - 2.0 
                    if elapsed < safe_threshold: 
                        eliminated[p_id] = "استعجل ومات"
                        players.remove(p_id)
                
                elif special_logic == "fusion_negation":
                    if val == "2": 
                        eliminated[p_id] = "حسبها غلط"
                        players.remove(p_id)
                
                elif special_logic == "sacrifice": pass 
                
                else:
                    if val != correct_val: 
                        eliminated[p_id] = "جواب غلط"
                        players.remove(p_id)

            if eliminated:
                # 🛑 طباعة الأسباب
                details = []
                for pid, reason in eliminated.items():
                    details.append(f"<@{pid}> ({reason})")
                
                msg_str = ", ".join(details)
                if special_logic == "sacrifice":
                    await ctx.send(f"🔪 **الضحايا:** {msg_str}")
                else:
                    msgs = ["ودعوا الملاعب", "طاروا", "اكلوا بوري"]
                    await ctx.send(f"💀 **{random.choice(msgs)}:** {msg_str}")
            else:
                if len(players) > 0: await ctx.send("👏🏻 **عبرتوا بسلام!**")

            if len(players) <= 1:
                if players: await ctx.send(f"👑 **الفائز الأسطوري:** <@{players[0]}> 🎉")
                else: await ctx.send("❌ **الكل مات.. لونا فازت!** 😌💅")
                break
            
            round_num += 1
            await asyncio.sleep(2)

        self.game_running = False

# --- الكلاسات المساعدة (بدون تغيير) ---
class JoinView(discord.ui.View):
    def __init__(self, host, embed):
        super().__init__(timeout=20) 
        self.players = [] 
        self.host = host
        self.embed = embed
        self.message = None

    @discord.ui.button(label="دخول اللعبة 🩸", style=discord.ButtonStyle.blurple)
    async def join(self, interaction, button):
        if interaction.user.id in self.players:
            return await interaction.response.send_message("أنت مسجل أصلاً!", ephemeral=True)
        self.players.append(interaction.user.id)
        if self.message:
            player_list_str = ""
            for i, pid in enumerate(self.players, 1):
                player_list_str += f"`#{i}` <@{pid}>\n"
            if len(player_list_str) > 950: player_list_str = player_list_str[:950] + "\n..."
            self.embed.clear_fields()
            self.embed.add_field(name=f"👥 اللاعبين ({len(self.players)})", value=player_list_str, inline=False)
            await self.message.edit(embed=self.embed)
        await interaction.response.send_message("تم التسجيل!", ephemeral=True)

    @discord.ui.button(label="بدء اللعبة 🚀", style=discord.ButtonStyle.success)
    async def start_game(self, interaction, button):
        if interaction.user != self.host:
            return await interaction.response.send_message("بس المنظم يكدر يبديها!", ephemeral=True)
        self.stop() 

class GameButton(discord.ui.Button):
    def __init__(self, label, style, real_value, custom_id=None):
        super().__init__(label=label, style=style, custom_id=custom_id)
        self.real_value = real_value 
    
    async def callback(self, interaction):
        view: GameView = self.view
        user_id = interaction.user.id
        if user_id not in view.current_players: return

        if view.special_logic == "sacrifice":
            if str(user_id) == self.real_value:
                return await interaction.response.send_message("تريد تنتحر؟ اضغط اسم غيرك! 😂", ephemeral=True)
            view.player_clicks[user_id] = (self.real_value, time.time())
            await interaction.response.send_message(f"🔪 غدرت بـ <@{self.real_value}>!", ephemeral=True)
            return

        if view.special_logic == "combo":
            if user_id not in view.combo_tracker: view.combo_tracker[user_id] = []
            required = ["🔴", "🔵", "🔴"] 
            current_step = len(view.combo_tracker[user_id])
            if current_step < len(required):
                if self.real_value == required[current_step]:
                    view.combo_tracker[user_id].append(self.real_value)
                    if len(view.combo_tracker[user_id]) == len(required):
                        view.player_clicks[user_id] = (True, time.time())
                        await interaction.response.send_message("✅ كملت التسلسل!", ephemeral=True)
                    else:
                        await interaction.response.send_message(f"صح! كمل ({len(view.combo_tracker[user_id])}/{len(required)})", ephemeral=True)
                else:
                    view.player_clicks[user_id] = (False, time.time()) 
                    await interaction.response.send_message("❌ غلطت بالتسلسل!", ephemeral=True)
            return

        if user_id in view.player_clicks: 
            return await interaction.response.send_message("ما يصير تغير رأيك!", ephemeral=True)
        
        view.player_clicks[user_id] = (self.real_value, time.time())
        await interaction.response.send_message(f"تم الاختيار!", ephemeral=True)

class GameView(discord.ui.View):
    def __init__(self, players, correct_val, is_trap, special_logic, options_data):
        super().__init__(timeout=None)
        self.current_players = players
        self.correct_val = correct_val
        self.is_trap = is_trap
        self.special_logic = special_logic
        self.player_clicks = {} 
        self.combo_tracker = {} 
        self.start_time = time.time()
        
        for label, style, real_val in options_data:
            cid = f"btn_{real_val}_{random.randint(1,99999)}"
            self.add_item(GameButton(label, style, real_val, custom_id=cid))

    def turn_to_ghost(self):
        for child in self.children:
            if isinstance(child, GameButton):
                child.label = "👻"
                child.style = discord.ButtonStyle.secondary

    def shuffle_buttons(self):
        current_buttons = [b for b in self.children if isinstance(b, GameButton)]
        self.clear_items()
        random.shuffle(current_buttons)
        for btn in current_buttons:
            self.add_item(btn)

async def setup(bot):
    await bot.add_cog(LunaGame(bot))