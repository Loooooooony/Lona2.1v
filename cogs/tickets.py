import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import io
import datetime
from utils.data_manager import load_guild_json, save_guild_json

# --- Views ---


class TicketLauncherView(View):
    def __init__(self, guild_id):
        super().__init__(timeout=None)
        self.guild_id = guild_id

    @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.blurple, custom_id="open_ticket_btn", emoji="📩")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        config = await load_guild_json(interaction.guild.id, 'tickets_config.json')
        if not config:
            return await interaction.followup.send("❌ Ticket system not configured!", ephemeral=True)

        if config.get('require_shift') and not config.get('staff_shift_active', True):
            return await interaction.followup.send("⛔ Support is currently **CLOSED**. Please come back later!", ephemeral=True)

        active_tickets = await load_guild_json(interaction.guild.id, 'active_tickets.json')
        existing = None
        for cid, t_data in active_tickets.items():
            if t_data['user_id'] == interaction.user.id and t_data['status'] == 'open':
                existing = cid
                break

        if existing:
            return await interaction.followup.send(f"⚠️ You already have an open ticket: <#{existing}>", ephemeral=True)

        cat_id = config.get('category_id')
        category = interaction.guild.get_channel(int(cat_id)) if cat_id else None

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        if config.get('support_role_id'):
            support_role = interaction.guild.get_role(int(config['support_role_id']))
            if support_role:
                overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel_name = config.get('naming_format', 'ticket-{user}').replace('{user}', interaction.user.name)

        try:
            channel = await interaction.guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)
        except Exception as e:
            return await interaction.followup.send(f"❌ Failed to create channel: {e}", ephemeral=True)

        active_tickets[str(channel.id)] = {
            "channel_id": channel.id,
            "guild_id": interaction.guild.id,
            "user_id": interaction.user.id,
            "status": "open",
            "created_at": datetime.datetime.now().isoformat()
        }
        await save_guild_json(interaction.guild.id, 'active_tickets.json', active_tickets)

        embed = discord.Embed(
            title=f"Ticket #{channel.name}",
            description=f"Welcome {interaction.user.mention}! Support will be with you shortly.",
            color=0x3498db
        )

        view = TicketControlView()
        await channel.send(content=interaction.user.mention, embed=embed, view=view)

        await interaction.followup.send(f"✅ Ticket created: {channel.mention}", ephemeral=True)


class TicketControlView(View):
    def __init__(self):
        super().__init__(timeout=None)

    async def get_config(self, guild_id):
        return await load_guild_json(guild_id, 'tickets_config.json')

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.success, custom_id="ticket_claim", emoji="🙋‍♂️")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = await self.get_config(interaction.guild.id)

        active_tickets = await load_guild_json(interaction.guild.id, 'active_tickets.json')
        ticket = active_tickets.get(str(interaction.channel.id))

        if not ticket:
            return await interaction.response.send_message("❌ Ticket not found in Data.", ephemeral=True)

        if interaction.user.id == ticket['user_id']:
            return await interaction.response.send_message("❌ You cannot claim your own ticket.", ephemeral=True)

        await interaction.response.defer()

        if config.get('support_role_id'):
            support_role = interaction.guild.get_role(int(config['support_role_id']))
            if support_role:
                await interaction.channel.set_permissions(support_role, send_messages=False)

        await interaction.channel.set_permissions(interaction.user, send_messages=True, read_messages=True)

        ticket['claimed_by'] = interaction.user.id
        await save_guild_json(interaction.guild.id, 'active_tickets.json', active_tickets)

        button.disabled = True
        button.label = f"Claimed by {interaction.user.display_name}"
        await interaction.message.edit(view=self)
        await interaction.channel.send(f"✅ **{interaction.user.mention}** has claimed this ticket!")

    @discord.ui.button(label="Voice", style=discord.ButtonStyle.secondary, custom_id="ticket_voice", emoji="🎙️")
    async def voice(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = await self.get_config(interaction.guild.id)
        if not config or not config.get('allow_voice'):
            return await interaction.response.send_message("❌ Voice tickets are disabled.", ephemeral=True)

        await interaction.response.defer()

        overwrites = interaction.channel.overwrites
        vc_name = f"voice-{interaction.channel.name}"

        vc = await interaction.guild.create_voice_channel(name=vc_name, category=interaction.channel.category, overwrites=overwrites)
        await interaction.followup.send(f"🎙️ Voice channel created: {vc.mention}\n(It will be deleted when the ticket closes)")

    @discord.ui.button(label="Escalate", style=discord.ButtonStyle.danger, custom_id="ticket_escalate", emoji="🚨")
    async def escalate(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = await self.get_config(interaction.guild.id)
        if not config or not config.get('allow_escalation'):
            return await interaction.response.send_message("❌ Escalation disabled.", ephemeral=True)

        await interaction.response.defer()
        admin_role_id = config.get('admin_role_id')
        if not admin_role_id:
            return await interaction.followup.send("❌ No Admin role configured.", ephemeral=True)

        await interaction.channel.edit(name=f"🔴-{interaction.channel.name}")
        await interaction.channel.send(f"🚨 **ESCALATION REQUESTED!** <@&{admin_role_id}>")
        button.disabled = True
        await interaction.message.edit(view=self)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, custom_id="ticket_close", emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = await self.get_config(interaction.guild.id)
        await interaction.response.send_modal(CloseReasonModal(config))


class CloseReasonModal(Modal):
    def __init__(self, config):
        super().__init__(title="Close Ticket")
        self.config = config
        self.reason = TextInput(label="Reason", placeholder="Issue resolved...", required=False)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        channel = interaction.channel

        active_tickets = await load_guild_json(interaction.guild.id, 'active_tickets.json')
        ticket = active_tickets.get(str(channel.id))

        if not ticket:
            return

        user = interaction.guild.get_member(ticket['user_id'])

        messages = [msg async for msg in channel.history(limit=500, oldest_first=True)]
        transcript_text = generate_html_transcript(channel, messages)
        file = discord.File(io.BytesIO(transcript_text.encode('utf-8')), filename=f"transcript-{channel.name}.html")

        log_id = self.config.get('log_channel_id')
        if log_id:
            log_channel = interaction.guild.get_channel(int(log_id))
            if log_channel:
                embed = discord.Embed(title="Ticket Closed", color=0x2ecc71, timestamp=datetime.datetime.now())
                embed.add_field(name="User", value=f"<@{ticket['user_id']}>")
                embed.add_field(name="Closed By", value=interaction.user.mention)
                embed.add_field(name="Reason", value=self.reason.value or "No reason provided")
                await log_channel.send(embed=embed, file=file)

        if user:
            try:
                view = RatingView(channel.id, interaction.guild.id)
                await user.send(
                    f"👋 Your ticket in **{interaction.guild.name}** has been closed.\n"
                    f"Reason: {self.reason.value}\n"
                    "Please rate your experience:",
                    view=view
                )
            except Exception:
                pass

        ticket['status'] = 'closed'
        ticket['closed_at'] = datetime.datetime.now().isoformat()
        ticket['close_reason'] = self.reason.value

        await save_guild_json(interaction.guild.id, 'active_tickets.json', active_tickets)

        voice_channel = discord.utils.get(interaction.guild.voice_channels, name=f"voice-{channel.name}")
        if voice_channel:
            await voice_channel.delete()

        await channel.delete()


class RatingView(View):
    def __init__(self, ticket_id, guild_id):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id
        self.guild_id = guild_id
        for i in range(1, 6):
            self.add_item(Button(label="⭐"*i, custom_id=f"rate_{i}", style=discord.ButtonStyle.secondary))

    async def interaction_check(self, interaction: discord.Interaction):
        rating = int(interaction.data['custom_id'].split('_')[1])

        active_tickets = await load_guild_json(self.guild_id, 'active_tickets.json')
        if str(self.ticket_id) in active_tickets:
            active_tickets[str(self.ticket_id)]['rating'] = rating
            await save_guild_json(self.guild_id, 'active_tickets.json', active_tickets)

        await interaction.response.edit_message(content="✅ Thank you for your feedback!", view=None)
        return False


def generate_html_transcript(channel, messages):
    html = f"""
    <html>
    <head><style>body{{font-family:sans-serif;background:#36393f;color:#dcddde}}
    .msg{{padding:10px;border-bottom:1px solid #2f3136}}
    .author{{font-weight:bold;color:#fff}}
    .time{{font-size:0.8em;color:#72767d;margin-left:10px}}</style></head>
    <body>
    <h2>Transcript for #{channel.name}</h2>
    """
    for m in messages:
        html += f"""
        <div class="msg">
            <span class="author">{m.author.display_name}</span>
            <span class="time">{m.created_at.strftime('%Y-%m-%d %H:%M:%S')}</span>
            <div class="content">{m.content}</div>
        </div>
        """
    html += "</body></html>"
    return html


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(TicketLauncherView(None))
        self.bot.add_view(TicketControlView())
        print("🎟️ Ticket System Ready")

    @commands.command(name="panel")
    @commands.has_permissions(administrator=True)
    async def send_panel(self, ctx):
        await ctx.message.delete()

        panel_data = await load_guild_json(ctx.guild.id, 'tickets_panel.json')

        if panel_data:
            title = panel_data.get('embed_title', "Support Ticket")
            desc = panel_data.get('embed_desc', "Click below")
            try:
                color = int(panel_data.get('embed_color', '#3498db').replace('#', ''), 16)
            except Exception:
                color = 0x3498db
        else:
            title = "Support Ticket"
            desc = "Click the button below to open a ticket."
            color = 0x3498db

        embed = discord.Embed(title=title, description=desc, color=color)
        view = TicketLauncherView(ctx.guild.id)

        await ctx.send(embed=embed, view=view)

    @commands.command(name="shift")
    @commands.has_permissions(manage_channels=True)
    async def toggle_shift(self, ctx):
        config = await load_guild_json(ctx.guild.id, 'tickets_config.json')

        new_state = not config.get('staff_shift_active', True)
        config['staff_shift_active'] = new_state

        await save_guild_json(ctx.guild.id, 'tickets_config.json', config)

        status = "🟢 OPEN" if new_state else "🔴 CLOSED"
        await ctx.send(f"Support shift is now: **{status}**")


async def setup(bot):
    await bot.add_cog(Tickets(bot))
