import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import io
import os
import json
import arabic_reshaper
from bidi.algorithm import get_display
import sys
import aiohttp

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.data_manager import get_guild_file, get_guild_asset

class WelcomeSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # دالة لتحميل الإعدادات بأمان
    def load_config(self, guild_id):
        path = get_guild_file(guild_id, 'welcome_config.json')
        try:
            with open(path, 'r', encoding='utf-8') as f: return json.load(f)
        except: return {}

    async def send_welcome_card(self, member, is_test=False):
        # Determine guild_id
        if is_test:
            # If testing, member might be the bot user, need to find a guild or passed implicitly
            # In test_welcome_api we pass member as guild.me, so member.guild works
            pass

        guild = member.guild
        if not guild: return

        config = self.load_config(guild.id)
        if not config.get('enabled') and not is_test: return

        # 1. تجهيز النصوص والمتغيرات
        if is_test:
            user_name = "Lona Bot"
            server_name = guild.name
            member_count = str(guild.member_count)
            inviter_name = "Admin"
            invites_count = "10"
            user_avatar_url = str(self.bot.user.avatar.url) if self.bot.user.avatar else None
        else:
            user_name = member.name
            server_name = guild.name
            member_count = str(guild.member_count)
            inviter_name = "Unknown"
            invites_count = "0"
            user_avatar_url = str(member.avatar.url) if member.avatar else None

        def format_text(text):
            return str(text).replace('{user}', user_name)\
                            .replace('{username}', user_name)\
                            .replace('{server}', server_name)\
                            .replace('{count}', member_count)\
                            .replace('{inviter}', inviter_name)\
                            .replace('{invites}', invites_count)

        # 2. تجهيز القماش (Canvas)
        # ⚠️ الحل الجذري: نثبت الحجم 800x450 نفس الموقع بالضبط
        CANVAS_WIDTH = 800
        CANVAS_HEIGHT = 450
        
        file = None
        try:
            # Determine paths based on guild
            bg_path = get_guild_asset(guild.id, 'welcome_bg.png', 'data/welcome_bg.png')
            
            # تحميل الخلفية وتغيير حجمها لتطابق الموقع
            if os.path.exists(bg_path):
                img = Image.open(bg_path).convert("RGBA")
                img = img.resize((CANVAS_WIDTH, CANVAS_HEIGHT)) # إجبار الحجم
            else:
                img = Image.new('RGBA', (CANVAS_WIDTH, CANVAS_HEIGHT), color='black')

            draw = ImageDraw.Draw(img)

            # 3. رسم صورة العضو (Avatar)
            try:
                # تحميل الصورة
                if user_avatar_url:
                    if not hasattr(self.bot, 'session') or self.bot.session.closed:
                        self.bot.session = aiohttp.ClientSession()

                    async with self.bot.session.get(user_avatar_url) as resp:
                        if resp.status == 200:
                            data = await resp.read()
                            avatar_img = Image.open(io.BytesIO(data)).convert("RGBA")
                        else: raise Exception("Fail load avatar")
                else:
                    # صورة احتياطية في حال الفشل
                    avatar_img = Image.new('RGBA', (150, 150), color='gray')

                # الحجم والموقع
                av_size = int(float(config.get('avatar_size', 150)))
                avatar_img = avatar_img.resize((av_size, av_size))
                
                # الشكل (دائرة/مربع)
                shape = config.get('avatar_shape', 'circle')
                mask = Image.new("L", (av_size, av_size), 0)
                draw_mask = ImageDraw.Draw(mask)
                
                if shape == 'circle':
                    draw_mask.ellipse((0, 0, av_size, av_size), fill=255)
                elif shape == 'round':
                    draw_mask.rounded_rectangle((0, 0, av_size, av_size), radius=30, fill=255)
                else:
                    draw_mask.rectangle((0, 0, av_size, av_size), fill=255)
                
                av_x = int(float(config.get('avatar_x', 50)))
                av_y = int(float(config.get('avatar_y', 50)))
                
                img.paste(avatar_img, (av_x, av_y), mask)

            except Exception as e:
                print(f"⚠️ Avatar Error: {e}")

            # 4. رسم النص (Text)
            try:
                raw_text = config.get('image_text', 'Welcome')
                final_text = format_text(raw_text)

                # معالجة العربي
                reshaped_text = arabic_reshaper.reshape(final_text)
                bidi_text = get_display(reshaped_text)

                # إعداد الخط
                f_size = int(float(config.get('font_size', 40)))

                # Custom font per guild or default
                font_path = get_guild_asset(guild.id, 'welcome_font.ttf', 'data/welcome_font.ttf')

                font = None
                
                # محاولة تحميل الخط المرفوع
                try:
                    font = ImageFont.truetype(font_path, f_size)
                except:
                    # محاولة تحميل خط نظام يدعم العربي
                    try:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", f_size)
                    except:
                        font = ImageFont.load_default() # آخر حل

                txt_x = int(float(config.get('text_x', 250)))
                txt_y = int(float(config.get('text_y', 100)))
                txt_color = config.get('text_color', '#FFFFFF')

                # رسم النص
                draw.text((txt_x, txt_y), bidi_text, font=font, fill=txt_color)

            except Exception as e:
                print(f"⚠️ Text Error: {e}")

            # 5. الحفظ والإرسال
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            file = discord.File(buffer, filename="welcome.png")

        except Exception as e:
            print(f"❌ Critical Drawing Error: {e}")

        # تجهيز الرسالة النصية المرافقة للصورة
        msg_content = format_text(config.get('message', 'Welcome {user}'))
        if not is_test:
            msg_content = msg_content.replace(user_name, member.mention) # تحويل الاسم لمنشن حقيقي
        else:
            msg_content = "🧪 **[تجربة]**\n" + msg_content

        channel_id = config.get('channel_id')
        if channel_id:
            channel = guild.get_channel(int(channel_id))
            if channel:
                await channel.send(content=msg_content, file=file)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self.send_welcome_card(member)

    # نحتاج نجهز Session لتحميل الصور
    async def cog_load(self):
        if not hasattr(self.bot, 'session'):
            self.bot.session = aiohttp.ClientSession()

async def setup(bot):
    await bot.add_cog(WelcomeSystem(bot))
