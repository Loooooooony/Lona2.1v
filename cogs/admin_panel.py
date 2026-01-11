import discord
from discord.ext import commands
import sys
import os

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.data_manager import set_guild_password

class AdminPanel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setpanel")
    @commands.has_permissions(administrator=True)
    async def set_panel_password(self, ctx, password: str = None):
        """Sets the password for the web dashboard."""
        if not password:
            return await ctx.send("❌ Please provide a password. Usage: `!setpanel <password>`")

        try:
            set_guild_password(ctx.guild.id, password)
            await ctx.author.send(f"✅ Dashboard password for **{ctx.guild.name}** set to: `{password}`\nLogin here: {ctx.bot.dashboard_url if hasattr(ctx.bot, 'dashboard_url') else 'Dashboard URL'}")
            await ctx.send("✅ Password updated! I've sent it to your DM.")
        except Exception as e:
            await ctx.send(f"❌ Error saving password: {e}")

async def setup(bot):
    await bot.add_cog(AdminPanel(bot))
