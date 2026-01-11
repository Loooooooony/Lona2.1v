import discord
from discord.ext import commands
import random
# استدعاء الداتا (راح نعبيها بالخطوة الاخيرة)
from utils.user_data import SPECIAL_USERS, GENERAL_RESPONSES

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- 🧠 دالة ذكية تختار الرد المناسب حسب الشخص والأمر ---
    def get_response(self, member_id, command_type):
        # 1. شيك اذا العضو مميز وعنده رد خاص
        if member_id in SPECIAL_USERS:
            user_data = SPECIAL_USERS[member_id]
            if command_type in user_data:
                return random.choice(user_data[command_type])
        
        # 2. اذا ماكو، جيب رد عام
        if command_type in GENERAL_RESPONSES:
             return random.choice(GENERAL_RESPONSES[command_type])
        
        return "صار خطأ بالردود.. لونا لحكيلي! 🌚💔"

    # ==========================
    # 🥊 1. أوامر العنف (كف، رفس، تف)
    # ==========================
    @commands.command(name="كف", aliases=["راشدي", "slap"])
    async def slap(self, ctx, member: discord.Member = None):
        if not member: member = ctx.author
        reply = self.get_response(member.id, "kuff") # مفتاح الداتا: kuff
        await ctx.send(f"{reply} \n(الضحية: {member.mention})")

    @commands.command(name="رفسة", aliases=["رفس", "دفرة"])
    async def kick(self, ctx, member: discord.Member = None):
        if not member: member = ctx.author
        reply = self.get_response(member.id, "kick") # مفتاح الداتا: kick
        await ctx.send(f"{reply} \n(الضحية: {member.mention})")

    @commands.command(name="تف", aliases=["تفل", "spit"])
    async def spit(self, ctx, member: discord.Member = None):
        if not member: 
            await ctx.send("تتفل على الهوا؟ 🌬️ لازم تمنشن احد!")
            return
        reply = self.get_response(member.id, "spit") # مفتاح الداتا: spit
        await ctx.send(f"{reply} \n(الموجه له: {member.mention})")

    # ==========================
    # 🤗 2. أوامر العاطفة (حضن)
    # ==========================
    @commands.command(name="حضن", aliases=["hug"])
    async def hug(self, ctx, member: discord.Member = None):
        if not member: member = ctx.author
        # الحضن ممكن يكون دافي، وممكن يكون مقلب
        reply = self.get_response(member.id, "hug") # مفتاح الداتا: hug
        await ctx.send(f"{reply} \n(حضن لـ: {member.mention})")

    # ==========================
    # 🎲 3. أوامر الحظ واللعب (نرد، حظ، فضيحة)
    # ==========================
    @commands.command(name="نرد", aliases=["dice", "roll"])
    async def dice(self, ctx):
        num = random.randint(1, 6)
        if num == 6:
            await ctx.send(f"🎲 طلع لك **{num}**! (حظك كاعد اليوم 💃🏻🔥)")
        elif num == 1:
            await ctx.send(f"🎲 طلع لك **{num}**.. (حظ مشردين مع الأسف 🌚💔)")
        else:
            await ctx.send(f"🎲 طلع لك **{num}**.")

    @commands.command(name="حظ", aliases=["luck", "بخت"])
    async def luck(self, ctx):
        # هنا الرد يعتمد على الشخص نفسه، يعني حظ لونا غير حظ باترك
        reply = self.get_response(ctx.author.id, "luck") # مفتاح الداتا: luck
        await ctx.send(f"🔮 **بختك اليوم يكول:**\n{reply}")

    @commands.command(name="فضيحة", aliases=["scandal"])
    async def scandal(self, ctx, member: discord.Member = None):
        if not member: member = ctx.author
        reply = self.get_response(member.id, "scandal") # مفتاح الداتا: scandal
        await ctx.send(f"📸 **فضيحة حصرية:**\n{reply} \n({member.mention})")

async def setup(bot):
    await bot.add_cog(Fun(bot))
