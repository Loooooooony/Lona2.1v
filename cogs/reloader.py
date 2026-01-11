import discord
from discord.ext import commands
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ReloadHandler(FileSystemEventHandler):
    def __init__(self, bot):
        self.bot = bot
    def on_modified(self, event):
        if event.src_path.endswith(".py") and "cogs" in event.src_path:
            fname = os.path.basename(event.src_path)[:-3]
            if fname == "reloader": return
            try:
                self.bot.reload_extension(f"cogs.{fname}")
                print(f"🔄 Auto-Reloaded: {fname}")
            except Exception as e:
                print(f"⚠️ Reload Error ({fname}): {e}")

class AutoReloader(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.observer = Observer()
        self.handler = ReloadHandler(bot)
        if os.path.exists("./cogs"):
            self.observer.schedule(self.handler, path="./cogs", recursive=False)
            self.observer.start()

    def cog_unload(self):
        self.observer.stop()
        self.observer.join()

async def setup(bot):
    await bot.add_cog(AutoReloader(bot))