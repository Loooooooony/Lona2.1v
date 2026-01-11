import discord
from discord.ext import commands
import random
import asyncio
from utils.user_data import SPECIAL_USERS

class Social(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- 🛠️ دالة مساعدة لرسم شريط النسبة ---
    def create_bar(self, percentage):
        # كل 10% تمثل مربع واحد
        filled = int(percentage / 10)
        empty = 10 - filled
        bar = "🟩" * filled + "⬜" * empty
        return bar

    # ==========================
    # 💍 1. نظام الزواج (تفاعلي)
    # ==========================
    @commands.command(name="زواج", aliases=["marry", "خطبة"])
    async def marry(self, ctx, member: discord.Member = None):
        if not member or member == ctx.author:
            await ctx.send(f"يا {ctx.author.mention}، تريد تتزوج نفسك لو تتزوج الهوا؟ منشن شريك حياتك! 💍🌚")
            return

        # رسالة الخطبة
        await ctx.send(f"🔔 **إعلان خطوبة!** \nيا {member.mention}، العضو {ctx.author.mention} يطلب ايدك للزواج! 💍\nعندك 30 ثانية.. اكتب **(نعم)** للموافقة أو **(لا)** للرفض.")

        # دالة التحقق من الرد
        def check(m):
            return m.author == member and m.channel == ctx.channel and m.content.lower() in ["نعم", "لا", "yes", "no"]

        try:
            # انتظار الرد لمدة 30 ثانية
            msg = await self.bot.wait_for('message', timeout=30.0, check=check)

            if msg.content.lower() in ["نعم", "yes"]:
                await ctx.send(f"كللللللوش! 💃🏻🎉✨\nمبروك للعروسين {ctx.author.mention} ❤️ {member.mention}!\nالله يرزقكم الذرية الصالحة (وبوتات صغار) 🤖👶🏻")
            else:
                await ctx.send(f"أوووويلي.. 💔🌚\n{ctx.author.mention} مع الأسف.. {member.mention} رفضك وكال: ما أفكر بالارتباط حالياً (جذاب).")

        except asyncio.TimeoutError:
            await ctx.send(f"⏰ انتهى الوقت! {member.mention} سكب لك (طنشك). \nيا {ctx.author.mention} لم كرامتك وروح 🏃🏻‍♀️💔")

    # ==========================
    # ❤️ 2. نسبة الحب (Love Rate)
    # ==========================
    @commands.command(name="حب", aliases=["love"])
    async def love(self, ctx, member: discord.Member = None):
        if not member: member = ctx.author
        
        # نسبة عشوائية
        rate = random.randint(0, 100)
        bar = self.create_bar(rate)
        
        comment = ""
        if rate >= 90: comment = "يا عيني! عصافير حب للأبد 🦜❤️"
        elif rate >= 50: comment = "علاقة جيدة.. بس يرادلها شوية اهتمام 🤝🏻"
        elif rate >= 20: comment = "حب من طرف واحد.. الله يعينك 💔🌚"
        else: comment = "ماكو أي مشاعر.. انسى الموضوع 🧊💀"

        embed = discord.Embed(title="❤️ مقياس الحب", description=f"بين {ctx.author.name} و {member.name}", color=0xff0000)
        embed.add_field(name="النسبة", value=f"**{rate}%**\n{bar}", inline=False)
        embed.set_footer(text=comment)
        await ctx.send(embed=embed)

    # ==========================
    # 🤝🏻 3. نسبة الصداقة (Friendship)
    # ==========================
    @commands.command(name="صداقة", aliases=["friend", "friendship"])
    async def friendship(self, ctx, member: discord.Member = None):
        if not member: member = ctx.author
        
        rate = random.randint(0, 100)
        bar = self.create_bar(rate)

        comment = ""
        if rate >= 90: comment = "ضلع وضلع.. مستحيل تفترقون! 👬✨"
        elif rate >= 50: comment = "أصدقاء عاديين، بس دير بالك منه مرات 🐍"
        else: comment = "هاي مو صداقة، هاي مصلحة! 🌚💸"

        embed = discord.Embed(title="🤝🏻 مقياس الصداقة", description=f"بين {ctx.author.name} و {member.name}", color=0x00ff00)
        embed.add_field(name="النسبة", value=f"**{rate}%**\n{bar}", inline=False)
        embed.set_footer(text=comment)
        await ctx.send(embed=embed)

    # ==========================
    # 😡 4. نسبة الكره (Hate Rate)
    # ==========================
    @commands.command(name="كره", aliases=["hate"])
    async def hate(self, ctx, member: discord.Member = None):
        if not member: member = ctx.author
        
        rate = random.randint(0, 100)
        bar = self.create_bar(rate)

        embed = discord.Embed(title="😡 مقياس الكره", description=f"مدى كره {ctx.author.name} لـ {member.name}", color=0x000000)
        embed.add_field(name="النسبة", value=f"**{rate}%**\n{bar}", inline=False)
        await ctx.send(embed=embed)

    # ==========================
    # 🥴 5. نسبة الكرنج (Cringe Rate) - مرتبطة بالداتا!
    # ==========================
    @commands.command(name="كرنج", aliases=["cringe"])
    async def cringe(self, ctx, member: discord.Member = None):
        if not member: member = ctx.author

        # نحسب نسبة عشوائية
        rate = random.randint(0, 100)
        bar = self.create_bar(rate)
        
        # الرد المبدئي
        roast = f"نسبة الكرنج عندك واصلة للسما! ☁️🥴"

        # --- تخصيص الرد حسب الشخص (من ملف الداتا) ---
        # اذا النسبة عالية والشخص موجود بالداتا، نجيب رد "كرنج" خاص بيه
        if rate > 70 and member.id in SPECIAL_USERS:
            user_data = SPECIAL_USERS[member.id]
            # نشيك اذا عنده ردود خاصة بالكرنج (راح نضيفها بالداتا باسم 'cringe_roast')
            if "cringe_roast" in user_data:
                roast = random.choice(user_data["cringe_roast"])
        
        # اذا ماكو رد خاص، نستخدم ردود عامة حسب النسبة
        elif rate < 20:
            roast = "طبيعي جداً، انسان راقي ومو كرنج ✨🎩"
        elif rate < 50:
            roast = "نص نص.. مرات تذب خيط 🧵🌚"
        elif rate > 90:
            roast = "يا إلهي! العداد طك! لازمك فورمات 📉💀"

        embed = discord.Embed(title="🥴 مقياس الكرنج", description=f"فحص شامل لـ {member.name}", color=0xffa500)
        embed.add_field(name="النسبة", value=f"**{rate}%**\n{bar}", inline=False)
        embed.set_footer(text=roast)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Social(bot))