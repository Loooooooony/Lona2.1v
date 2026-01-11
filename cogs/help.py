import discord
from discord.ext import commands
from discord.ui import Select, View

# --- 🎮 قائمة المساعدة التفاعلية ---

class HelpSelect(Select):
    def __init__(self, bot, mapping):
        self.bot = bot
        self.mapping = mapping
        
        options = [
            discord.SelectOption(
                label="القائمة الرئيسية",
                description="عودة للصفحة الأولى",
                emoji="🏠",
                value="home"
            )
        ]
        
        # جلب الـ Cogs (الأقسام) تلقائياً
        for cog, commands_list in mapping.items():
            if cog is None: continue # تخطي الأوامر بدون قسم
            if not commands_list: continue # تخطي الأقسام الفارغة
            
            # تخصيص إيموجي لكل قسم (اختياري)
            emoji = "📂"
            desc = cog.description if cog.description else "أوامر القسم"
            
            # محاولة تخمين الإيموجي من اسم الملف
            name = cog.qualified_name.lower()
            if "tod" in name: emoji = "🍾"; desc = "لعبة صراحة أو جرأة"
            elif "spy" in name: emoji = "🕵️"; desc = "لعبة الجاسوس"
            elif "code" in name: emoji = "🤐"; desc = "لعبة الأسماء الحركية"
            elif "fami" in name: emoji = "👨‍👩‍👧‍👦"; desc = "لعبة عائلتي تربح"
            elif "luna" in name: emoji = "🌙"; desc = "ألعاب لونا الخاصة"
            elif "khira" in name: emoji = "🤔"; desc = "لعبة لو خيروك"
            elif "confess" in name: emoji = "💌"; desc = "نظام الاعترافات"
            elif "social" in name: emoji = "👥"; desc = "الأوامر الاجتماعية"
            
            options.append(discord.SelectOption(
                label=cog.qualified_name,
                description=desc,
                emoji=emoji,
                value=cog.qualified_name
            ))

        super().__init__(placeholder="اختر القسم الذي تريد استعراضه...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        value = self.values[0]
        
        if value == "home":
            await interaction.response.edit_message(embed=self.view.home_embed, view=self.view)
            return

        # البحث عن الـ Cog المختار
        cog = self.bot.get_cog(value)
        if cog is None:
            await interaction.response.send_message("❌ حدث خطأ، لم يتم العثور على القسم.", ephemeral=True)
            return

        # بناء الامبد للأوامر
        embed = discord.Embed(
            title=f"{self.options[self.get_option_index(value)].emoji} قسم: {cog.qualified_name}",
            description=f"**{self.options[self.get_option_index(value)].description}**\n\n",
            color=discord.Color.from_rgb(47, 49, 54) # لون غامق فخم
        )
        
        commands_list = cog.get_commands()
        for command in commands_list:
            if command.hidden: continue # تخطي الأوامر المخفية
            
            # جلب الشرح من الكود (Docstring) أو وضع افتراضي
            help_text = command.help if command.help else "لا يوجد وصف لهذا الأمر."
            
            # تنسيق الأمر بشكل جميل
            embed.add_field(
                name=f"`!{command.name}`",
                value=f"└ {help_text}",
                inline=False
            )
        
        embed.set_footer(text=f"طلب بواسطة: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        await interaction.response.edit_message(embed=embed, view=self.view)

    def get_option_index(self, value):
        for i, option in enumerate(self.options):
            if option.value == value:
                return i
        return 0

class HelpView(View):
    def __init__(self, bot, mapping, home_embed):
        super().__init__(timeout=120) # ينتهي بعد دقيقتين
        self.home_embed = home_embed
        self.add_item(HelpSelect(bot, mapping))
        
    async def on_timeout(self):
        # تعطيل القائمة بعد انتهاء الوقت
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except:
            pass

class CustomHelp(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        # الصفحة الرئيسية (Home)
        embed = discord.Embed(
            title="🎮 **قائمة أوامر بوت لونا** 🌙",
            description=(
                "أهلاً بك! أنا لونا، بوت الألعاب والترفيه العراقي 🇮🇶\n"
                "استخدم القائمة بالأسفل لاختيار اللعبة ومعرفة أوامرها.\n\n"
                "**📌 تلميح:** جميع الأوامر تبدأ بـ `!`"
            ),
            color=discord.Color.magenta()
        )
        embed.set_thumbnail(url=self.context.bot.user.display_avatar.url)
        embed.set_image(url="https://media.discordapp.net/attachments/YOUR_IMAGE_LINK_HERE.png") # (اختياري) ضعي رابط بانر هنا
        
        # إحصائيات سريعة
        total_commands = len([c for c in self.context.bot.commands if not c.hidden])
        embed.add_field(name="🤖 الأوامر", value=f"`{total_commands}` أمر", inline=True)
        embed.add_field(name="📶 البنج", value=f"`{round(self.context.bot.latency * 1000)}` ms", inline=True)
        
        view = HelpView(self.context.bot, mapping, embed)
        view.message = await self.context.send(embed=embed, view=view)

    async def send_command_help(self, command):
        # عند كتابة !help command_name
        embed = discord.Embed(
            title=f"🔎 استعلام عن أمر: `!{command.name}`",
            color=discord.Color.blue()
        )
        embed.add_field(name="📝 الوصف:", value=command.help or "لا يوجد وصف.", inline=False)
        
        if command.aliases:
            embed.add_field(name="🔗 اختصارات:", value=", ".join([f"`{a}`" for a in command.aliases]), inline=False)
            
        embed.add_field(name="💡 الاستخدام:", value=f"`!{command.name} {command.signature}`", inline=False)
        
        await self.context.send(embed=embed)

async def setup(bot):
    # تسجيل نظام المساعدة الجديد
    bot.help_command = CustomHelp()