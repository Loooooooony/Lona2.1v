import discord
from discord.ext import commands
import asyncio
import random
import json
import datetime
import os
import sys

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.data_manager import get_guild_file

# دالة لجلب اسم الأمر من الملف (عشان يشتغل ديناميكي)
# This needs guild_id, but decorators run at import time.
# We cannot dynamic command name PER GUILD easily in discord.py without hacks.
# For now, we keep command name static or global.
# Or we register multiple aliases?
# Let's assume standard 'royal' or fetch from a global config if needed,
# OR just keep 'royal' as default and let user edit aliases in moderation?
# The prompt says: "Ensure bot name/avatar changes update the bot globally but load settings per page context."
# Game settings like title/color should be per guild. Command name... usually hard to make per-guild.
# We will use 'royal' as base command, and check guild config inside.

class RouletteRoyal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Paths are dynamic

    def get_config_path(self, guild_id):
        return get_guild_file(guild_id, 'games_config.json')

    def get_log_path(self, guild_id):
        return get_guild_file(guild_id, 'death_log.json')

    # دالة لجلب النصوص الحالية من الداشبورد
    def get_text(self, guild_id):
        try:
            with open(self.get_config_path(guild_id), 'r', encoding='utf-8') as f:
                return json.load(f).get('roulette', {})
        except:
            return {}

    def log_death(self, guild_id, user_name, user_id):
        path = self.get_log_path(guild_id)
        try:
            with open(path, 'r') as f:
                logs = json.load(f)
        except:
            logs = []
            
        logs.append({"name": user_name, "id": str(user_id), "time": str(datetime.datetime.now())})
        
        with open(path, 'w') as f:
            json.dump(logs, f, indent=4)

    # الأمر يتغير حسب الداشبورد -> Fixed name 'royal' but reads config
    @commands.command(name='royal', aliases=['روليت'])
    async def royal_game(self, ctx):
        txt = self.get_text(ctx.guild.id)
        
        # التصميم
        title = txt.get('title', "💀 روليت الإقصاء الملكي")
        desc = txt.get('description', "اضغط على انضمام للموت..")
        color = int(txt.get('color', '#990000').replace('#', ''), 16)
        
        embed = discord.Embed(title=title, description=desc, color=color)
        embed.set_footer(text=f"المنظم: {ctx.author.display_name}")
        
        view = LobbyView(ctx, txt)
        msg = await ctx.send(embed=embed, view=view)
        await view.wait()
        
        if len(view.players) < 2:
            await ctx.send("❌ ماكو ضحايا كفاية، الغيت اللعبة.")
            return

        players = list(view.players)
        random.shuffle(players)
        
        await ctx.send(f"🔒 **قفلت الأبواب!** الضحايا: {len(players)}")
        await asyncio.sleep(2)

        # 🔥 تجهيز مسدس خاص لكل لاعب
        guns = {}
        for p in players:
            guns[p.id] = {
                'bullet': random.randint(0, 5), # مكان الطلقة
                'used': [] # الأزرار المحروقة
            }

        active_players = players.copy()

        # حلقة اللعب
        while len(active_players) > 1:
            round_players = active_players.copy()
            
            for player in round_players:
                if player not in active_players: continue
                if len(active_players) == 1: break 

                my_gun = guns[player.id]
                used_slots = my_gun['used']
                bullet_loc = my_gun['bullet']

                # عرض المسدس الخاص باللاعب
                ch_embed = discord.Embed(
                    title=f"🔫 دورك يا {player.display_name}", 
                    description=f"المتبقي في مسدسك: **{6 - len(used_slots)}** طلقات\nاختر زر...", 
                    color=0x2b2d31
                )
                
                # نمرر "الأزرار المحروقة" للفيو
                ch_view = ChamberView(player, used_slots, timeout=30)
                ch_msg = await ctx.send(player.mention, embed=ch_embed, view=ch_view)
                
                timed_out = await ch_view.wait()

                if timed_out:
                    await ctx.send(f"😴 **{player.display_name}** نام ومات (Time Out)")
                    active_players.remove(player)
                    try:
                        await ch_msg.delete()
                    except:
                        pass
                    continue

                chosen_slot = ch_view.chosen_slot
                
                if chosen_slot == bullet_loc:
                    # 💀 مات
                    self.log_death(ctx.guild.id, player.name, player.id)
                    txt_lose = "💥 **BOOM!** تناثر مخه!"
                    
                    try:
                        await player.timeout(datetime.timedelta(minutes=1), reason="Dead")
                    except:
                        pass
                    
                    await ctx.send(f"{txt_lose} {player.mention} ودع الملاعب 💀")
                    active_players.remove(player)
                
                else:
                    # 😅 عاش
                    await ctx.send(f"💨 **Click..** {player.display_name} نجا بأعجوبة!")
                    guns[player.id]['used'].append(chosen_slot)

                try:
                    await ch_msg.delete()
                except:
                    pass
                await asyncio.sleep(1)

        # إعلان الفائز
        winner = active_players[0]
        msg_win = txt.get('msg_win', "👑 الفائز والناجي الوحيد:")
        await ctx.send(f"{msg_win} {winner.mention} 🎉")


# --- كلاسات الأزرار ---

class LobbyView(discord.ui.View):
    def __init__(self, ctx, txt):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.players = []
        self.children[0].label = txt.get('btn_join', "انضمام")
        self.children[1].label = txt.get('btn_start', "بدء")

    @discord.ui.button(style=discord.ButtonStyle.danger)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in self.players:
            return await interaction.response.send_message("مسجل!", ephemeral=True)
        self.players.append(interaction.user)
        embed = interaction.message.embeds[0]
        # تحديث الوصف مع الحفاظ على النص الأصلي
        desc_parts = embed.description.split('\n\n')
        new_desc = desc_parts[0] + f"\n\n**الضحايا ({len(self.players)}):**\n" + "\n".join([p.display_name for p in self.players])
        embed.description = new_desc
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(style=discord.ButtonStyle.success)
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user == self.ctx.author:
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(view=self)
            self.stop()

class ChamberView(discord.ui.View):
    def __init__(self, player, used_slots, timeout=30):
        super().__init__(timeout=timeout)
        self.player = player
        self.chosen_slot = -1
        self.used_slots = used_slots 
        
        for i in range(6):
            btn = discord.ui.Button(label="?", style=discord.ButtonStyle.secondary, custom_id=str(i), row=i//3)
            
            # تعطيل الأزرار المستخدمة
            if i in used_slots:
                btn.disabled = True
                btn.label = "❌"
                btn.style = discord.ButtonStyle.primary

            btn.callback = self.click
            self.add_item(btn)

    async def click(self, interaction: discord.Interaction):
        if interaction.user != self.player: return
        
        try:
            self.chosen_slot = int(interaction.data['custom_id'])
        except:
            self.chosen_slot = int(interaction.custom_id)
        
        await interaction.response.defer()
        self.stop()

async def setup(bot):
    await bot.add_cog(RouletteRoyal(bot))
