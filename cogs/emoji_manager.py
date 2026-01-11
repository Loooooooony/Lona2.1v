import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import aiohttp
import io
import os
import asyncio
import subprocess
import uuid
from PIL import Image, ImageSequence # استدعاء الملكة Pillow 👑

# ==========================================
# 1. محرك المعالجة (النسخة الهجينة الذكية 🧠)
# ==========================================
class MediaProcessor:
    @staticmethod
    async def download_with_limit(url, limit_mb=8):
        """تحميل آمن للملفات"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200: return None
                    size = int(resp.headers.get('Content-Length', 0))
                    limit_bytes = limit_mb * 1024 * 1024
                    if size > limit_bytes: return None
                    data = await resp.read()
                    if len(data) > limit_bytes: return None
                    return bytes(data)
        except:
            return None

    @staticmethod
    async def save_temp_file(data, ext):
        filename = f"temp_{uuid.uuid4()}.{ext}"
        with open(filename, 'wb') as f:
            f.write(data)
        return filename

    @staticmethod
    def cleanup(filename):
        if filename and os.path.exists(filename):
            try: os.remove(filename)
            except: pass

    @staticmethod
    async def smart_convert(input_path, target_type, is_video_input):
        """
        🔥 هنا السحر:
        - الصور الثابتة -> نستخدم Pillow (سريع وخفيف)
        - الفيديو/GIF -> نستخدم FFmpeg (قوي للمتحرك)
        """
        if input_path.endswith('.json'): return input_path

        # إعدادات الحجم
        if target_type == 'sticker':
            max_size = 320
        else: # Emoji
            max_size = 128

        output_ext = "gif" if is_video_input else "png"
        output_path = f"out_{uuid.uuid4()}.{output_ext}"

        # -------------------------------------------
        # المسار الأول: الصور الثابتة (شغل Pillow) 🎨
        # -------------------------------------------
        if not is_video_input:
            try:
                with Image.open(input_path) as img:
                    # تحويل الألوان للتأكد من الشفافية
                    img = img.convert("RGBA")
                    
                    # تغيير الحجم مع الحفاظ على الأبعاد (Thumbnail)
                    img.thumbnail((max_size, max_size))
                    
                    # ضغط وحفظ (Optimize)
                    img.save(output_path, "PNG", optimize=True)
                    return output_path
            except Exception as e:
                print(f"Pillow Error: {e}")
                return None

        # -------------------------------------------
        # المسار الثاني: فيديو/متحرك (شغل FFmpeg) 🎬
        # -------------------------------------------
        else:
            time_limit = 2.5 if target_type == 'sticker' else 2.0
            fps_limit = 15 if target_type == 'sticker' else 12
            
            # فلتر معقد لضغط الـ GIF وجودة عالية
            filter_complex = (
                f"[0:v]fps={fps_limit},"
                f"scale='min({max_size},iw)':-1:flags=lanczos,"
                f"pad=ceil(iw/2)*2:ceil(ih/2)*2," # أبعاد زوجية
                f"split[s0][s1];"
                f"[s0]palettegen=max_colors=64:reserve_transparent=1[p];"
                f"[s1][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle"
            )
            
            cmd = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-threads", "2", 
                "-i", input_path, "-t", str(time_limit),
                "-filter_complex", filter_complex, "-f", "gif", output_path
            ]

            try:
                # استخدام nice لتخفيف الحمل
                if os.name == 'posix': cmd = ["nice", "-n", "10"] + cmd
                
                process = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                await asyncio.wait_for(process.communicate(), timeout=20)
                
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0: 
                    return output_path 
            except Exception as e:
                print(f"FFmpeg Error: {e}")
        
        return output_path

# ==========================================
# 2. المودال والأزرار
# ==========================================
class NameModal(Modal):
    def __init__(self, bot, asset_url=None, is_video=False, is_lottie=False, is_already_sticker=False, source_msg=None):
        super().__init__(title="تسمية الاستيكر")
        self.bot = bot
        self.asset_url = asset_url
        self.is_video = is_video
        self.is_lottie = is_lottie 
        self.is_already_sticker = is_already_sticker
        self.source_msg = source_msg 
        self.name_input = TextInput(label="الاسم", placeholder="sticker_name", min_length=2, max_length=30)
        self.add_item(self.name_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        temp_input = None; temp_output = None
        
        try:
            data = await MediaProcessor.download_with_limit(self.asset_url)
            if not data:
                return await interaction.followup.send("❌ الملف كبير جداً أو تالف.", ephemeral=True)

            final_data = None; filename = ""
            
            # Lottie Files
            if self.is_lottie:
                 final_data = data
                 clean_name = self.name_input.value.strip().replace(" ", "_")
                 filename = f"{clean_name}.json"
                 file = discord.File(fp=io.BytesIO(final_data), filename=filename)
                 try:
                    await interaction.guild.create_sticker(name=clean_name, description="Lona Lab Lottie", emoji="🤖", file=file)
                    await interaction.followup.send(f"✅ **تم إضافة استيكر Lottie:** `{clean_name}`")
                    if self.source_msg: await self.source_msg.delete()
                 except Exception as e:
                     await interaction.followup.send(f"❌ فشل Lottie: {e}", ephemeral=True)
                 return

            # Normal Processing
            if self.is_already_sticker and not self.is_video: 
                final_data = data
                filename = f"{self.name_input.value}.png"
            else:
                ext = "gif" if self.is_video else "png"
                temp_input = await MediaProcessor.save_temp_file(data, ext)
                temp_output = await MediaProcessor.smart_convert(temp_input, 'sticker', self.is_video)
                
                if not temp_output or not os.path.exists(temp_output):
                     return await interaction.followup.send("❌ فشل التحويل.", ephemeral=True)
                
                with open(temp_output, 'rb') as f: final_data = f.read()
                filename = f"{self.name_input.value}.{'png' if temp_output.endswith('.png') else 'gif'}"

            clean_name = self.name_input.value.strip().replace(" ", "_")
            clean_name = "".join(x for x in clean_name if x.isalnum() or x in "_-")
            
            file = discord.File(fp=io.BytesIO(final_data), filename=filename)
            await interaction.guild.create_sticker(name=clean_name, description="Lona Lab", emoji="🤖", file=file)
            
            await interaction.followup.send(f"✅ **تم إضافة الاستيكر:** `{clean_name}`")
            if self.source_msg: 
                try: await self.source_msg.delete()
                except: pass

        except discord.HTTPException as e:
            if e.code == 30039: 
                await interaction.followup.send("❌ السيرفر ممتلئ بالاستيكرات!", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ خطأ ديسكورد: {e}", ephemeral=True)
        except Exception as e: 
            await interaction.followup.send(f"❌ خطأ عام: {e}", ephemeral=True)
        finally: 
            MediaProcessor.cleanup(temp_input)
            MediaProcessor.cleanup(temp_output)

class MediaControlView(View):
    def __init__(self, bot, author_id, url, filename, content_type):
        super().__init__(timeout=60)
        self.bot = bot; self.author_id = author_id; self.url = url; self.filename = filename
        self.is_video = any(x in content_type for x in ['video', 'gif', 'webm'])

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id: 
            await interaction.response.send_message("مو لك!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="إيموجي 😀", style=discord.ButtonStyle.primary)
    async def make_emoji(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(thinking=True)
        temp_input = None; temp_output = None
        try:
            data = await MediaProcessor.download_with_limit(self.url, limit_mb=8)
            if not data: return await interaction.followup.send("❌ الملف كبير.", ephemeral=True)

            temp_input = await MediaProcessor.save_temp_file(data, "gif" if self.is_video else "png")
            temp_output = await MediaProcessor.smart_convert(temp_input, 'emoji', self.is_video)
            
            with open(temp_output, 'rb') as f: final_data = f.read()
            
            name = self.filename.split('.')[0].replace("-", "_")
            name = "".join(x for x in name if x.isalnum() or x == "_")[:30]
            if not name: name = f"emoji_{uuid.uuid4().hex[:4]}"

            new_emoji = await interaction.guild.create_custom_emoji(name=name, image=final_data)
            await interaction.followup.send(f"✅ **تم:** {new_emoji}")
            try: await interaction.message.delete()
            except: pass
        except Exception as e: await interaction.followup.send(f"❌ خطأ: {e}", ephemeral=True)
        finally: MediaProcessor.cleanup(temp_input); MediaProcessor.cleanup(temp_output)

    @discord.ui.button(label="استيكر 🏷️", style=discord.ButtonStyle.success)
    async def make_sticker(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(NameModal(self.bot, asset_url=self.url, is_video=self.is_video, is_lottie=False, is_already_sticker=False, source_msg=interaction.message))

    @discord.ui.button(label="إلغاء ❌", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.message.delete()

class StealStickerView(View):
    def __init__(self, bot, sticker_url, is_animated, is_lottie):
        super().__init__(timeout=60)
        self.bot = bot; self.url = sticker_url; self.is_animated = is_animated; self.is_lottie = is_lottie

    @discord.ui.button(label="🕵️‍♂️ سرقة", style=discord.ButtonStyle.secondary)
    async def steal(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(NameModal(self.bot, asset_url=self.url, is_video=self.is_animated, is_lottie=self.is_lottie, is_already_sticker=True, source_msg=interaction.message))

# ==========================================
# 4. الكلاس الرئيسي
# ==========================================
class EmojiManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.LAB_ID = 1457941757177106513 

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.channel.id != self.LAB_ID: return

        # 1. الايموجيات
        import re
        custom_emojis = re.findall(r'<(a?):(\w+):(\d+)>', message.content)
        if custom_emojis:
            for is_anim, name, e_id in custom_emojis:
                emoji_obj = discord.utils.get(message.guild.emojis, id=int(e_id))
                if emoji_obj: # حذف
                    try:
                        await emoji_obj.delete()
                        await message.reply(f"🗑️ **حذفت:** `:{name}:`")
                    except: pass
                else: # إضافة
                    try:
                        ext = 'gif' if is_anim else 'png'
                        url = f"https://cdn.discordapp.com/emojis/{e_id}.{ext}"
                        data = await MediaProcessor.download_with_limit(url)
                        if data:
                            await message.guild.create_custom_emoji(name=name, image=data)
                            await message.reply(f"✅ **ضفت:** `:{name}:`")
                    except: pass
            return

        # 2. الاستيكرات
        if message.stickers:
            sticker = message.stickers[0]
            try:
                local_sticker = await message.guild.fetch_sticker(sticker.id)
                if local_sticker:
                    await local_sticker.delete()
                    await message.reply(f"🗑️ **حذفت:** `{local_sticker.name}`")
                    return 
            except: pass

            is_lottie = (sticker.format == discord.StickerFormatType.lottie)
            is_anim = (sticker.format in [discord.StickerFormatType.apng, discord.StickerFormatType.gif]) or is_lottie
            view = StealStickerView(self.bot, sticker.url, is_anim, is_lottie)
            await message.reply("🕵️‍♂️ **اسرقه؟**", view=view)
            return

        # 3. المرفقات
        if message.attachments:
            att = message.attachments[0]
            acceptable_types = ['image', 'video', 'application/json']
            is_acceptable = any(t in att.content_type for t in acceptable_types)
            if is_acceptable:
                view = MediaControlView(self.bot, message.author.id, att.url, att.filename, att.content_type)
                await message.reply("🎨 **تحويل إلى:**", view=view)

async def setup(bot):
    await bot.add_cog(EmojiManager(bot))