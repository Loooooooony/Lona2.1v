import discord
from discord.ext import commands
from database import db

class EmojiManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_settings(self, guild_id):
        return await db.fetchrow("SELECT * FROM emoji_settings WHERE guild_id = %s", guild_id)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild: return

        settings = await self.get_settings(message.guild.id)
        if not settings or not settings['enabled']: return

        # Check target channel
        if settings['target_channel_id'] and message.channel.id == settings['target_channel_id']:

            # Only Emojis Mode
            if settings['only_emojis_mode']:
                # Simple check: remove spaces and check if content is only emojis
                # This is complex regex, simplistic approach for now:
                # If message has content that is NOT an emoji custom tag or unicode, delete.
                # Regex for custom emoji: <a?:name:id>
                # If we strip all custom emojis, is it empty?
                import re
                custom_emoji_pattern = r'<a?:[a-zA-Z0-9_]+:[0-9]+>'
                clean_content = re.sub(custom_emoji_pattern, '', message.content).strip()

                # If clean_content is not empty (and doesn't look like unicode emojis only - hard to validate perfectly without lib), delete.
                # For safety, let's just delete if it has alphanumeric chars outside tags?
                if any(c.isalnum() for c in clean_content):
                    try:
                        await message.delete()
                        # Warning msg?
                    except: pass

            # Auto-Add External Emojis (Stealer)
            # If user posted external emoji, maybe add it?
            # (Requires complex logic, usually manual command is better. Skipping auto-add to avoid spam)

    @commands.command(name="steal")
    @commands.has_permissions(manage_emojis=True)
    async def steal_emoji(self, ctx, emoji: discord.PartialEmoji, name=None):
        """Steals a custom emoji from another server."""
        try:
            image = await emoji.read()
            name = name or emoji.name
            new_emoji = await ctx.guild.create_custom_emoji(name=name, image=image)
            await ctx.send(f"✅ Stolen: {new_emoji}")
        except Exception as e:
            await ctx.send(f"❌ Failed: {e}")

async def setup(bot):
    await bot.add_cog(EmojiManager(bot))
