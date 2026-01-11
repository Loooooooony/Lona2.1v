from quart import Quart, render_template, request, redirect, url_for, send_file, session, jsonify
import discord
import os
import sys
import asyncio
import json
import io
import re
import datetime
from utils.data_manager import get_guild_file, check_guild_password, get_guild_asset, load_guild_json, save_guild_json

app = Quart(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.secret_key = b'Lona_Secret_Key_2025_Secure'

# 🔐 باسورد المحرر
EDITOR_PASSWORD = "lona"

# تعريف المتغيرات العامة
bot = None      

# ملفات الداتا للمحرر (Global Files Only)
DATA_FILES = {
    "tod": {"name": "🍾 صراحة وجرأة", "path": "data/tod_data.py"},
    "family": {"name": "👨‍👩‍👧‍👦 عائلتي تربح", "path": "data/questions.json"},
    "codenames": {"name": "🕵️‍♂️ كود نيمز", "path": "data/codenames_data.py"},
    "social": {"name": "🤬 ردود القصف", "path": "utils/user_data.py"},
    "khira": {"name": "🤔 لو خيروك", "path": "utils/khira_data.py"},
}

# --- Context Processor ---
@app.context_processor
def inject_guild():
    # Helper to be used in templates if needed
    return dict()

# --- الصفحة الرئيسية ---
# الصفحة الرئيسية: بوابة اختيار السيرفر
@app.route('/')
async def select_server():
    # هنا نجيب قائمة السيرفرات من البوت
    guilds_list = []
    if bot:
        for guild in bot.guilds:
            guilds_list.append({
                "id": str(guild.id),
                "name": guild.name,
                "icon": guild.icon.url if guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png",
                "member_count": guild.member_count
            })
    
    return await render_template('select_server.html', guilds=guilds_list)

# صفحة تسجيل الدخول للسيرفر
@app.route('/login/<guild_id>', methods=['GET', 'POST'])
async def server_login(guild_id):
    error = None
    guild = bot.get_guild(int(guild_id)) if bot else None
    
    if request.method == 'POST':
        form = await request.form
        password = form.get('password')
        
        # Check against data/server_passwords.json
        if check_guild_password(guild_id, password):
            session[f'access_{guild_id}'] = True 
            return redirect(f'/dashboard/{guild_id}')
        else:
            error = "❌ كلمة المرور خطأ!"

    return await render_template('server_login.html', guild=guild, error=error)

# --- HELPER: Authentication Check ---
def is_authorized(guild_id):
    return session.get(f'access_{guild_id}')

# لوحة التحكم (الداشبورد) الرئيسية للسيرفر
@app.route('/dashboard/<int:guild_id>')
async def dashboard(guild_id):
    if not is_authorized(guild_id):
        return redirect(f'/login/{guild_id}')
    
    guild = bot.get_guild(guild_id) if bot else None
    # Fix: Render full dashboard page, not just sidebar
    return await render_template('index.html', guild=guild,
                                 ping=round(bot.latency * 1000) if bot else 0,
                                 guild_count=len(bot.guilds) if bot else 0,
                                 user_count=sum([g.member_count for g in bot.guilds]) if bot else 0,
                                 uptime="Calculating...") # Uptime logic can be added later

# --- 🔐 تسجيل الدخول للمحرر (Global Admin) ---
@app.route('/login_editor', methods=['POST'])
async def login_editor():
    form = await request.form
    password = form.get('password')
    
    if password == EDITOR_PASSWORD:
        session['editor_access'] = True
        return redirect(url_for('editor_menu'))
    else:
        return redirect('/?error=wrong_pass')

# --- 📝 قائمة المحرر ---
@app.route('/editor', methods=['GET', 'POST'])
async def editor_menu():
    if not session.get('editor_access'):
        return redirect('/?error=need_login')

    cogs_files = []
    if os.path.exists('./cogs'):
        cogs_files = [f for f in os.listdir('./cogs') if f.endswith('.py')]
        
    return await render_template('editor_menu.html', data_files=DATA_FILES, cogs_files=cogs_files)

# --- 📝 تعديل الملفات ---
@app.route('/editor/<file_key>', methods=['GET', 'POST'])
async def edit_file(file_key):
    if not session.get('editor_access'):
        return redirect('/?error=need_login')

    file_path = ""
    display_name = ""

    if file_key in DATA_FILES:
        file_path = DATA_FILES[file_key]['path']
        display_name = DATA_FILES[file_key]['name']
    elif os.path.exists(os.path.join('cogs', file_key)):
        file_path = os.path.join('cogs', file_key)
        display_name = f"كود برمجي: {file_key}"
    else:
        return "❌ الملف غير موجود!"

    if request.method == 'POST':
        form = await request.form
        new_content = form.get('content')
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return await render_template('editor.html', file_name=display_name, file_key=file_key, content=new_content, success="✅ تم الحفظ! (التحديث فوري)")
        except Exception as e:
            return await render_template('editor.html', file_name=display_name, file_key=file_key, content=new_content, error=f"خطأ: {e}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        content = "# لا يمكن القراءة"
    
    return await render_template('editor.html', file_name=display_name, file_key=file_key, content=content)

# =================================================================================================
#  🎟️ TICKET SYSTEM ROUTES
# =================================================================================================

@app.route('/dashboard/<int:guild_id>/tickets', methods=['GET', 'POST'])
async def tickets_dashboard(guild_id):
    if not is_authorized(guild_id): return redirect(f'/login/{guild_id}')
    guild = bot.get_guild(guild_id) if bot else None

    if request.method == 'POST':
        form = await request.form
        # Update Config
        if 'update_config' in form:
            data = {
                "support_role_id": form.get('support_role'),
                "admin_role_id": form.get('admin_role'),
                "category_id": form.get('category'),
                "log_channel_id": form.get('log_channel'),
                "naming_format": form.get('naming'),
                "require_shift": 'require_shift' in form,
                "allow_voice": 'allow_voice' in form,
                "allow_escalation": 'allow_escalation' in form
            }
            await save_guild_json(guild_id, 'tickets_config.json', data)

        # Create Panel
        elif 'create_panel' in form:
            # We save the panel settings, but we still need the user to "deploy" it via command or button.
            # But the requirement was to let them create it.
            # We will save it to tickets_panel.json
            panel_data = {
                "embed_title": form.get('p_title'),
                "embed_desc": form.get('p_desc'),
                "embed_color": form.get('p_color'),
                "button_label": form.get('b_label'),
                "button_emoji": form.get('b_emoji'),
                "button_color": form.get('b_color')
            }
            await save_guild_json(guild_id, 'tickets_panel.json', panel_data)

            # Optionally trigger bot to send the panel if we can (advanced)
            # For now, just save config.

        return redirect(f'/dashboard/{guild_id}/tickets')

    config = await load_guild_json(guild_id, 'tickets_config.json')
    panel = await load_guild_json(guild_id, 'tickets_panel.json')
    active_tickets_map = await load_guild_json(guild_id, 'active_tickets.json')

    # Filter closed tickets for display
    closed_tickets = []
    if active_tickets_map:
        for ch_id, t_data in active_tickets_map.items():
            if t_data.get('status') == 'closed':
                closed_tickets.append(t_data)

    # Sort by created_at desc (if available, otherwise random)
    closed_tickets.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    return await render_template('tickets.html', guild=guild, config=config, panel=panel, tickets=closed_tickets)

@app.route('/dashboard/<int:guild_id>/emojis', methods=['GET', 'POST'])
async def emojis_dashboard(guild_id):
    if not is_authorized(guild_id): return redirect(f'/login/{guild_id}')
    guild = bot.get_guild(guild_id) if bot else None

    if request.method == 'POST':
        form = await request.form
        data = {
            "target_channel_id": form.get('channel_id'),
            "allow_external": 'allow_external' in form,
            "only_emojis_mode": 'only_emojis' in form,
            "enabled": 'enabled' in form
        }
        await save_guild_json(guild_id, 'emoji_settings.json', data)
        return redirect(f'/dashboard/{guild_id}/emojis')

    settings = await load_guild_json(guild_id, 'emoji_settings.json')
    return await render_template('emojis.html', guild=guild, settings=settings)

# =================================================================================================
#  🛡️ SECTIONS REFACTORED FOR MULTI-GUILD (Routes now accept guild_id)
# =================================================================================================

# --- 🛡️ قسم الإدارة (Moderation) ---
@app.route('/dashboard/<int:guild_id>/moderation')
async def moderation_panel(guild_id):
    if not is_authorized(guild_id): return redirect(f'/login/{guild_id}')
    guild = bot.get_guild(guild_id) if bot else None

    # Use helper
    config = await load_guild_json(guild_id, 'moderation.json')
    
    # Default commands
    default_cmds = {
        "kick": {"name": "طرد (Kick)", "desc": "طرد عضو من السيرفر", "enabled": True, "aliases": ["k", "طرد"], "roles": [], "channels": [], "delete_after": 0},
        "ban": {"name": "حظر (Ban)", "desc": "حظر عضو نهائياً", "enabled": True, "aliases": ["b", "حظر", "باند"], "roles": [], "channels": [], "delete_after": 0},
        "unban": {"name": "فك الحظر (Unban)", "desc": "إزالة الحظر عن عضو", "enabled": True, "aliases": ["ub", "فك_حظر"], "roles": [], "channels": [], "delete_after": 0},
        "vkick": {"name": "طرد صوتي (Voice Kick)", "desc": "طرد العضو من الروم الصوتي", "enabled": True, "aliases": ["vk", "طرد_صوتي"], "roles": [], "channels": [], "delete_after": 0},
        "mute": {"name": "إسكات كتابي (Mute)", "desc": "منع الكتابة (Timeout)", "enabled": True, "aliases": ["m", "ميوت"], "roles": [], "channels": [], "delete_after": 0},
        "unmute": {"name": "فك الإسكات (Unmute)", "desc": "السماح بالكتابة", "enabled": True, "aliases": ["unm", "تكلم"], "roles": [], "channels": [], "delete_after": 0},
        "vmute": {"name": "إسكات صوتي (Voice Mute)", "desc": "منع التحدث بالروم الصوتي", "enabled": True, "aliases": ["vm", "اخرس"], "roles": [], "channels": [], "delete_after": 0},
        "vunmute": {"name": "فك صوتي (Voice Unmute)", "desc": "السماح بالتحدث صوتياً", "enabled": True, "aliases": ["vum", "انطق"], "roles": [], "channels": [], "delete_after": 0},
        "move": {"name": "سحب عضو (Move)", "desc": "سحب عضو لروم صوتي", "enabled": True, "aliases": ["mv", "سحب"], "roles": [], "channels": [], "delete_after": 0},
        "clear": {"name": "مسح (Clear)", "desc": "تنظيف الرسائل", "enabled": True, "aliases": ["c", "مسح"], "roles": [], "channels": [], "delete_after": 0},
        "lock": {"name": "قفل الروم (Lock)", "desc": "منع الجميع من الكتابة", "enabled": True, "aliases": ["l", "قفل"], "roles": [], "channels": [], "delete_after": 0},
        "unlock": {"name": "فتح الروم (Unlock)", "desc": "السماح للجميع بالكتابة", "enabled": True, "aliases": ["ul", "فتح"], "roles": [], "channels": [], "delete_after": 0},
        "slowmode": {"name": "الوضع البطيء (Slowmode)", "desc": "تحديد وقت بين الرسائل", "enabled": True, "aliases": ["sm", "بطيء"], "roles": [], "channels": [], "delete_after": 0},
        "warn": {"name": "تحذير (Warn)", "desc": "إعطاء تحذير لعضو", "enabled": True, "aliases": ["w", "نذار", "تحذير"], "roles": [], "channels": [], "delete_after": 0},
        "warns": {"name": "التحذيرات (Warnings)", "desc": "عرض تحذيرات العضو", "enabled": True, "aliases": ["ws", "انذارات"], "roles": [], "channels": [], "delete_after": 0},
        "role": {"name": "إعطاء رتبة (Role)", "desc": "إضافة/إزالة رتبة", "enabled": True, "aliases": ["r", "رتبة"], "roles": [], "channels": [], "delete_after": 0},
        "setnick": {"name": "تغيير لقب (Nick)", "desc": "تغيير اسم العضو", "enabled": True, "aliases": ["n", "لقب"], "roles": [], "channels": [], "delete_after": 0},
        "setcolor": {"name": "تغيير لون (Color)", "desc": "تغيير لون رتبة (Hex)", "enabled": True, "aliases": ["color", "لون"], "roles": [], "channels": [], "delete_after": 0}
    }

    updated = False
    for k, v in default_cmds.items():
        if k not in config:
            config[k] = v
            updated = True

    if updated:
        await save_guild_json(guild_id, 'moderation.json', config)

    return await render_template('moderation.html', commands=config, guild=guild)

@app.route('/api/toggle_mod_cmd', methods=['POST'])
async def toggle_mod_cmd():
    data = await request.get_json()
    guild_id = data.get('guild_id') # Must be passed from frontend
    cmd_key = data.get('cmd')
    state = data.get('state')
    
    if not is_authorized(guild_id): return {"status": "error", "msg": "Unauthorized"}

    config = await load_guild_json(guild_id, 'moderation.json')
    try:
        if cmd_key in config:
            config[cmd_key]['enabled'] = state
            await save_guild_json(guild_id, 'moderation.json', config)
            return {"status": "success"}
    except Exception as e:
        return {"status": "error", "msg": str(e)}
    return {"status": "error"}

@app.route('/dashboard/<int:guild_id>/moderation/edit/<cmd_key>', methods=['GET', 'POST'])
async def edit_mod_cmd(guild_id, cmd_key):
    if not is_authorized(guild_id): return redirect(f'/login/{guild_id}')
    guild = bot.get_guild(guild_id) if bot else None

    config = await load_guild_json(guild_id, 'moderation.json')
    if not config: return redirect(f'/dashboard/{guild_id}/moderation')

    if cmd_key not in config: return redirect(f'/dashboard/{guild_id}/moderation')
    
    if request.method == 'POST':
        form = await request.form
        
        aliases_str = form.get('aliases', '')
        config[cmd_key]['aliases'] = [x.strip() for x in aliases_str.split(',') if x.strip()]

        roles_str = form.get('roles', '')
        config[cmd_key]['roles'] = [x.strip() for x in roles_str.split(',') if x.strip()]

        channels_str = form.get('channels', '')
        config[cmd_key]['channels'] = [x.strip() for x in channels_str.split(',') if x.strip()]

        config[cmd_key]['delete_after'] = int(form.get('delete_after', 0))
        config[cmd_key]['enabled'] = 'enabled' in form

        await save_guild_json(guild_id, 'moderation.json', config)
            
        return redirect(f'/dashboard/{guild_id}/moderation')

    return await render_template('moderation_edit.html', cmd=config[cmd_key], key=cmd_key, guild=guild)

# --- 🎮 ستوديو الألعاب ---
@app.route('/dashboard/<int:guild_id>/game_studio', methods=['GET', 'POST'])
async def game_studio(guild_id):
    if not is_authorized(guild_id): return redirect(f'/login/{guild_id}')
    guild = bot.get_guild(guild_id) if bot else None

    config = await load_guild_json(guild_id, 'games_config.json')
    
    default_config = {
        "roulette": {
            "command_name": "royal", "title": "💀 روليت الإقصاء الملكي", 
            "description": "اضغط على انضمام للموت..", "color": "#990000", 
            "btn_join": "انضمام للموت 💀", "btn_start": "بدء المجزرة 🔥", "msg_win": "👑 الفائز:"
        },
        "codenames": {
            "command_name": "codenames", "title": "🕵️‍♂️ الأسماء الحركية", 
            "description": "انقسموا فريقين.. وحاولوا تعرفون كلماتكم!", "color": "#e74c3c", 
            "btn_join": "انضمام", "btn_start": "بدء اللعب"
        },
        "family": {
            "command_name": "family", "title": "👨‍👩‍👧‍👦 عائلتي تربح", 
            "description": "جاوبوا على أكثر الإجابات شيوعاً!", "color": "#f1c40f", 
            "btn_join": "تسجيل", "btn_start": "انطلاق"
        },
        "spyfall": {
            "command_name": "spy", "title": "🕵️‍♂️ لعبة برا السالفة", 
            "description": "واحد منكم جاسوس.. حاولوا تكشفوه!", "color": "#f1c40f", 
            "btn_join": "دخول", "btn_start": "بدء"
        }
    }

    if not config:
        config = default_config
        await save_guild_json(guild_id, 'games_config.json', config)

    if request.method == 'POST':
        form = await request.form
        
        # Roulette
        config['roulette']['command_name'] = form.get('r_cmd')
        config['roulette']['title'] = form.get('r_title')
        config['roulette']['description'] = form.get('r_desc')
        config['roulette']['color'] = form.get('r_color')
        config['roulette']['btn_join'] = form.get('r_btn_join')
        config['roulette']['btn_start'] = form.get('r_btn_start')
        config['roulette']['msg_win'] = form.get('r_msg_win')

        # Codenames
        config['codenames']['command_name'] = form.get('c_cmd')
        config['codenames']['title'] = form.get('c_title')
        config['codenames']['description'] = form.get('c_desc')
        config['codenames']['color'] = form.get('c_color')
        config['codenames']['btn_join'] = form.get('c_btn_join')
        config['codenames']['btn_start'] = form.get('c_btn_start')

        # Family
        config['family']['command_name'] = form.get('f_cmd')
        config['family']['title'] = form.get('f_title')
        config['family']['description'] = form.get('f_desc')
        config['family']['color'] = form.get('f_color')
        config['family']['btn_join'] = form.get('f_btn_join')
        config['family']['btn_start'] = form.get('f_btn_start')

        # Spyfall
        config['spyfall']['command_name'] = form.get('s_cmd')
        config['spyfall']['title'] = form.get('s_title')
        config['spyfall']['description'] = form.get('s_desc')
        config['spyfall']['color'] = form.get('s_color')
        config['spyfall']['btn_join'] = form.get('s_btn_join')
        config['spyfall']['btn_start'] = form.get('s_btn_start')
        
        await save_guild_json(guild_id, 'games_config.json', config)
            
        msg = "✅ تم الحفظ!"
        return await render_template('game_studio.html', config=config, success=msg, guild=guild)

    return await render_template('game_studio.html', config=config, guild=guild)

# --- دالة القيف اوي الشاملة ---
@app.route('/dashboard/<int:guild_id>/giveaway', methods=['GET', 'POST'])
async def giveaway_panel(guild_id):
    if not is_authorized(guild_id): return redirect(f'/login/{guild_id}')
    guild = bot.get_guild(guild_id) if bot else None

    config = await load_guild_json(guild_id, 'giveaway_config.json')
    active_giveaways = await load_guild_json(guild_id, 'active_giveaways.json')

    if request.method == 'POST':
        form = await request.form
        action = form.get('action')

        if action == 'end_now':
            target_id = int(form.get('target_id'))
            if bot:
                cog = bot.get_cog('GiveawaySystem')
                if cog:
                    # Need to implement end_giveaway with guild_id awareness or logic
                    await cog.end_giveaway(target_id, guild_id)
                    return redirect(f'/dashboard/{guild_id}/giveaway')

        new_config = {
            "prize": form.get('prize'),
            "winners": int(form.get('winners', 1)),
            "time_val": int(form.get('time_val', 24)),
            "time_unit": form.get('time_unit', 'h'),
            "description": form.get('description'),
            "color": form.get('color'),
            "channel_id": form.get('channel_id'),
            "image_url": form.get('image_url'),
            "thumbnail_url": form.get('thumbnail_url'),
            "ping_type": form.get('ping_type'),
            "req_role_id": form.get('req_role_id'),
            "blacklist_role_id": form.get('blacklist_role_id'),
            "bypass_role_id": form.get('bypass_role_id'),
            "req_voice_minutes": int(form.get('req_voice_minutes', 0) or 0),
            "min_account_age": int(form.get('min_account_age', 0) or 0),
            "min_server_age": int(form.get('min_server_age', 0) or 0)
        }        
        await save_guild_json(guild_id, 'giveaway_config.json', new_config)

        return await render_template('giveaway.html', config=new_config, active_list=[], success="✅ تم حفظ القالب الشامل!", guild=guild)

    active_list = []
    if active_giveaways:
        for msg_id, g_data in active_giveaways.items():
            active_list.append({
                'id': msg_id,
                'prize': g_data.get('prize', 'جائزة'),
                'winners': g_data.get('winners_count', 1),
                'participants': len(g_data.get('participants', [])),
                'end_time': datetime.datetime.fromtimestamp(g_data['end_timestamp']).strftime('%H:%M:%S')
            })

    return await render_template('giveaway.html', config=config, active_list=active_list, guild=guild)

# --- ⚙️ الإعدادات (Settings - Now Per Guild for Bot Naming etc?) ---
@app.route('/dashboard/<int:guild_id>/settings', methods=['GET', 'POST'])
async def settings(guild_id):
    if not is_authorized(guild_id): return redirect(f'/login/{guild_id}')
    guild = bot.get_guild(guild_id) if bot else None
    
    # Global status file
    status_config_path = 'data/status_config.json'

    if request.method == 'POST':
        form = await request.form
        files = await request.files
        
        status_type = form.get('status_type')
        activity_type = form.get('activity_type')
        activity_text = form.get('activity_text')
        stream_url = form.get('stream_url')

        d_status = discord.Status.online
        if status_type == 'idle':
            d_status = discord.Status.idle
        elif status_type == 'dnd':
            d_status = discord.Status.dnd
        elif status_type == 'invisible':
            d_status = discord.Status.invisible

        d_activity = None
        if activity_text:
            if activity_type == 'playing':
                d_activity = discord.Game(name=activity_text)
            elif activity_type == 'listening':
                d_activity = discord.Activity(type=discord.ActivityType.listening, name=activity_text)
            elif activity_type == 'watching':
                d_activity = discord.Activity(type=discord.ActivityType.watching, name=activity_text)
            elif activity_type == 'competing':
                d_activity = discord.Activity(type=discord.ActivityType.competing, name=activity_text)
            elif activity_type == 'streaming':
                d_activity = discord.Streaming(name=activity_text, url=stream_url or "https://twitch.tv/discord")

        await bot.change_presence(status=d_status, activity=d_activity)

        save_data = {"status": status_type, "activity_type": activity_type, "text": activity_text, "url": stream_url}
        
        with open(status_config_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=4)

        try:
            edit_kwargs = {}
            new_name = form.get('username')
            if new_name and new_name != bot.user.name:
                edit_kwargs['username'] = new_name
            
            avatar_file = files.get('avatar')
            if avatar_file and avatar_file.filename:
                edit_kwargs['avatar'] = avatar_file.read()

            if edit_kwargs:
                await bot.user.edit(**edit_kwargs)
                
        except Exception as e:
            return await render_template('settings.html', error=f"فشل تحديث البروفايل: {e}", bot=bot.user, config=save_data, guild=guild)

        return await render_template('settings.html', success="✅ تم التحديث!", bot=bot.user, config=save_data, guild=guild)
    
    try:
        with open(status_config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except:
        config = {"status": "online", "activity_type": "playing", "text": "", "url": ""}
        
    return await render_template('settings.html', bot=bot.user, config=config, guild=guild)

# --- 🧠 الردود التلقائية ---
@app.route('/dashboard/<int:guild_id>/auto_reply', methods=['GET', 'POST'])
async def auto_reply_manager(guild_id):
    if not is_authorized(guild_id): return redirect(f'/login/{guild_id}')
    guild = bot.get_guild(guild_id) if bot else None

    replies = await load_guild_json(guild_id, 'auto_reply.json')

    if request.method == 'POST':
        form = await request.form
        if 'add_trigger' in form:
            trigger = form.get('trigger').strip()
            response = form.get('response').strip()
            if trigger and response:
                replies[trigger] = response
                await save_guild_json(guild_id, 'auto_reply.json', replies)

                # Notify cog to reload for this guild?
                if bot and bot.get_cog('AutoReply'):
                     bot.get_cog('AutoReply').update_guild_replies(guild_id, replies)

        elif 'delete_trigger' in form:
            trigger = form.get('delete_trigger')
            if trigger in replies:
                del replies[trigger]
                await save_guild_json(guild_id, 'auto_reply.json', replies)

                if bot and bot.get_cog('AutoReply'):
                    bot.get_cog('AutoReply').update_guild_replies(guild_id, replies)
                    
    return await render_template('auto_reply.html', replies=replies, guild=guild)

# --- 👮🏻‍♀️ إعدادات اللوق ---
@app.route('/dashboard/<int:guild_id>/logger_settings', methods=['GET', 'POST'])
async def logger_settings(guild_id):
    if not is_authorized(guild_id): return redirect(f'/login/{guild_id}')
    guild = bot.get_guild(guild_id) if bot else None

    config = await load_guild_json(guild_id, 'log_config.json')
    if not config:
        config = {"log_channel_id": "", "events": {}}

    if request.method == 'POST':
        form = await request.form
        config['log_channel_id'] = form.get('channel_id')
        event_keys = ['msg_delete', 'msg_edit', 'msg_bulk', 'member_join', 'member_leave', 'member_update', 'user_update', 'voice_update', 'emoji_update', 'server_update', 'invite_update', 'ban_add', 'ban_remove', 'channel_create', 'channel_delete', 'channel_update', 'role_create', 'role_delete', 'role_update']
        if 'events' not in config: config['events'] = {}
        for key in event_keys:
            config['events'][key] = key in form

        await save_guild_json(guild_id, 'log_config.json', config)
        return await render_template('logger_settings.html', config=config, success="✅ تم الحفظ!", guild=guild)
    
    return await render_template('logger_settings.html', config=config, guild=guild)

def parse_emoji(emoji_str):
    if not emoji_str: return None
    custom_match = re.search(r'<(a?):(\w+):(\d+)>', emoji_str)
    return discord.PartialEmoji(name=custom_match.group(2), id=int(custom_match.group(3)), animated=bool(custom_match.group(1))) if custom_match else emoji_str

# --- 📢 المذيع ---
@app.route('/dashboard/<int:guild_id>/broadcast', methods=['GET', 'POST'])
async def broadcast_page(guild_id):
    if not is_authorized(guild_id): return redirect(f'/login/{guild_id}')
    guild = bot.get_guild(guild_id) if bot else None

    if request.method == 'POST':
        if not bot: return "Bot not connected"
        form = await request.form
        files = await request.files 
        try:
            channel = guild.get_channel(int(form.get('channel_id')))
            if not channel: return await render_template('broadcast.html', error="❌ القناة خطأ", guild=guild)
            
            webhook = None
            for w in await channel.webhooks():
                if w.user == bot.user:
                    webhook = w
                    break
            if not webhook:
                webhook = await channel.create_webhook(name="Lona Hook")
            
            sender_name = form.get('sender_name') or "Lona Broadcast"
            if 'sender_avatar_file' in files and files['sender_avatar_file'].filename:
                try: 
                    files['sender_avatar_file'].seek(0)
                    await webhook.edit(avatar=files['sender_avatar_file'].read(), name=sender_name)
                except: pass

            embed = discord.Embed(title=form.get('title'), description=form.get('description'), color=int(form.get('color', '#000000').replace('#', ''), 16))
            if form.get('footer'): embed.set_footer(text=form.get('footer'))
            
            discord_files = []
            if 'image_file' in files and files['image_file'].filename:
                discord_files.append(discord.File(io.BytesIO(files['image_file'].read()), filename="img.png"))
                embed.set_image(url="attachment://img.png")
            if 'thumbnail_file' in files and files['thumbnail_file'].filename:
                discord_files.append(discord.File(io.BytesIO(files['thumbnail_file'].read()), filename="thumb.png"))
                embed.set_thumbnail(url="attachment://thumb.png")

            view = discord.ui.View()
            has_btns = False
            for i in range(1, 6):
                lbl = form.get(f'btn_label_{i}')
                if not lbl: continue
                style = getattr(discord.ButtonStyle, form.get(f'btn_style_{i}', 'primary'))
                emoji = parse_emoji(form.get(f'btn_emoji_{i}'))
                action, val = form.get(f'btn_action_{i}'), form.get(f'btn_value_{i}')
                
                if action == 'link':
                    view.add_item(discord.ui.Button(label=lbl, url=val, emoji=emoji))
                else:
                    view.add_item(discord.ui.Button(label=lbl, style=style, custom_id=f"lona_cmd:{action}:{val}", emoji=emoji))
                has_btns = True
            
            await webhook.send(username=sender_name, embed=embed, files=discord_files, view=view if has_btns else discord.utils.MISSING)
            return await render_template('broadcast.html', success="✅ تم النشر!", guild=guild)
        except Exception as e:
            return await render_template('broadcast.html', error=f"خطأ: {e}", guild=guild)
            
    return await render_template('broadcast.html', guild=guild)

# --- 🎮 إدارة الألعاب (Active Games in Guild) ---
@app.route('/dashboard/<int:guild_id>/games')
async def games_manager(guild_id):
    if not is_authorized(guild_id): return redirect(f'/login/{guild_id}')
    guild = bot.get_guild(guild_id) if bot else None

    if not bot:
        return "Bot loading..."
    active_games = []

    # Filter games by guild_id
    if bot.get_cog('SpyGame'):
        for cid, s in bot.get_cog('SpyGame').sessions.items():
            if s.guild.id == guild_id and s.game_active:
                active_games.append({'name': 'Spyfall', 'cid': cid, 'type': 'spy'})
    if bot.get_cog('CodenamesGame'):
        for cid, s in bot.get_cog('CodenamesGame').sessions.items():
            if s.guild.id == guild_id and s.game_active:
                active_games.append({'name': 'Codenames', 'cid': cid, 'type': 'codenames'})
    if bot.get_cog('FamilyFeud'):
        for cid, s in bot.get_cog('FamilyFeud').active_games.items():
            if s.guild.id == guild_id:
                active_games.append({'name': 'Family Feud', 'cid': cid, 'type': 'family'})

    return await render_template('games.html', games=active_games, guild=guild)

@app.route('/dashboard/<int:guild_id>/stop_game/<gtype>/<int:cid>')
async def stop_game(guild_id, gtype, cid):
    if not is_authorized(guild_id): return redirect(f'/login/{guild_id}')

    if not bot:
        return "Bot error"
    try:
        ch = bot.get_channel(cid)
        if gtype == 'spy':
            if cid in bot.get_cog('SpyGame').sessions:
                bot.get_cog('SpyGame').sessions[cid].game_active = False
        elif gtype == 'codenames':
            if cid in bot.get_cog('CodenamesGame').sessions:
                bot.get_cog('CodenamesGame').sessions[cid].game_active = False
        elif gtype == 'family':
            if cid in bot.get_cog('FamilyFeud').active_games:
                del bot.get_cog('FamilyFeud').active_games[cid]
        if ch:
            await ch.send("🛑 **تم إيقاف اللعبة من الداشبورد!**")
    except:
        pass
    return redirect(f'/dashboard/{guild_id}/games')

# --- 👋🏻 الترحيب ---
@app.route('/dashboard/<int:guild_id>/welcome', methods=['GET', 'POST'])
async def welcome_studio(guild_id):
    if not is_authorized(guild_id): return redirect(f'/login/{guild_id}')
    guild = bot.get_guild(guild_id) if bot else None

    config = await load_guild_json(guild_id, 'welcome_config.json')
        
    if request.method == 'POST':
        form = await request.form
        files = await request.files
        config.update({k: v for k, v in form.items() if k in ['channel_id', 'message', 'avatar_shape', 'avatar_x', 'avatar_y', 'avatar_size', 'text_x', 'text_y', 'font_size', 'text_color', 'image_text']})
        config['enabled'] = 'enabled' in form
        
        # Save images to guild folder
        if 'bg_file' in files and files['bg_file'].filename:
            # We save as 'welcome_bg.png' in guild/images/
            path = get_guild_file(guild_id, 'images/welcome_bg.png')
            await files['bg_file'].save(path)

        if 'font_file' in files and files['font_file'].filename:
            path = get_guild_file(guild_id, 'images/welcome_font.ttf')
            await files['font_file'].save(path)
            
        await save_guild_json(guild_id, 'welcome_config.json', config)
            
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return {"status": "success", "msg": "✅ تم الحفظ!"}
        return await render_template('welcome.html', config=config, success="✅ تم الحفظ!", guild=guild)
    
    return await render_template('welcome.html', config=config, guild=guild)

@app.route('/dashboard/<int:guild_id>/welcome_assets/<filename>')
async def welcome_assets(guild_id, filename):
    if not is_authorized(guild_id): return "Unauthorized"
    # Helper to serve the correct file
    # filename is likely 'welcome_bg.png'

    # Logic: Check guild folder, else default
    path = get_guild_asset(guild_id, filename, default_path=f'data/{filename}')
    return await send_file(path)

@app.route('/api/test_welcome', methods=['POST'])
async def test_welcome_api():
    # Needs guild_id in body
    # But wait, send_welcome_card needs member object
    # For test we simulate it.
    data = await request.get_json()
    guild_id = data.get('guild_id') # We should pass this
    if not guild_id: return {"status": "error", "msg": "No guild ID"}

    if not bot or not bot.get_cog('WelcomeSystem'):
        return {"status": "error", "msg": "Welcome Cog Not Loaded"}
    try:
        # We need a fake member from this guild
        guild = bot.get_guild(int(guild_id))
        member = guild.me # Test with bot itself
        await bot.get_cog('WelcomeSystem').send_welcome_card(member, is_test=True)
        return {"status": "success", "msg": "✅ تم الإرسال!"}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

# --- 💀 الروليت ---
@app.route('/dashboard/<int:guild_id>/roulette_control', methods=['GET', 'POST'])
async def roulette_control(guild_id):
    if not is_authorized(guild_id): return redirect(f'/login/{guild_id}')
    guild = bot.get_guild(guild_id) if bot else None

    config = await load_guild_json(guild_id, 'roulette_config.json')
    if not config: config = {"mode": "kick"}
    
    logs = await load_guild_json(guild_id, 'death_log.json')
    if logs is None: logs = [] # load_guild_json returns {} default if not specified list
    if isinstance(logs, dict): logs = [] # Safety check

    if request.method == 'POST':
        form = await request.form
        config['mode'] = form.get('mode')
        await save_guild_json(guild_id, 'roulette_config.json', config)
        return redirect(f'/dashboard/{guild_id}/roulette_control')
        
    return await render_template('roulette.html', config=config, logs=logs[::-1], guild=guild)

# --- 🕌 الإسلامي ---
@app.route('/dashboard/<int:guild_id>/islamic', methods=['GET', 'POST'])
async def islamic_settings(guild_id):
    if not is_authorized(guild_id): return redirect(f'/login/{guild_id}')
    guild = bot.get_guild(guild_id) if bot else None

    config = await load_guild_json(guild_id, 'islamic_config.json')

    if request.method == 'POST':
        form = await request.form
        data = {
            "enabled": 'enabled' in form, "voice_channel_id": form.get('voice_channel_id'), "text_channel_id": form.get('text_channel_id'),
            "reader": form.get('reader'), "azkar_sabah": 'azkar_sabah' in form, "azkar_masa": 'azkar_masa' in form, "friday_kahf": 'friday_kahf' in form
        }
        await save_guild_json(guild_id, 'islamic_config.json', data)
        return redirect(f'/dashboard/{guild_id}/islamic')
    
    return await render_template('islamic.html', config=config, guild=guild)

# --- 📡 Live Chat ---
@app.route('/dashboard/<int:guild_id>/live_chat')
async def live_chat_page(guild_id):
    if not is_authorized(guild_id): return redirect(f'/login/{guild_id}')
    guild = bot.get_guild(guild_id) if bot else None
    return await render_template('live_chat.html', guild=guild)

@app.route('/api/get_sidebar')
async def get_sidebar():
    # This was used for live chat channel list?
    # Logic seems to return ALL guilds. We might want to restrict it or keep it for the sidebar loading?
    # Actually sidebar.html is server side rendered now.
    # But live_chat might use it.
    if not bot:
        return {"guilds": []}
    data = []
    for guild in bot.guilds:
        # Check if user has access? For now, public API... risky.
        # But this is local dashboard.
        channels = [{'id': str(c.id), 'name': c.name} for c in guild.text_channels if c.permissions_for(guild.me).read_messages]
        if channels:
            data.append({'id': str(guild.id), 'name': guild.name, 'icon': str(guild.icon.url) if guild.icon else None, 'channels': channels})
    return {"guilds": data}

@app.route('/api/get_messages')
async def get_messages():
    cid = request.args.get('channel_id')
    if not cid or not bot:
        return {"error": "No ID"}
    try:
        ch = bot.get_channel(int(cid))
        # Add Security: Verify if the channel belongs to a guild the session has access to?
        # Difficult without passing guild_id.
        if not ch:
            return {"error": "Channel Not Found"}
        msgs = []
        async for m in ch.history(limit=50):
            content = m.content
            for u in m.mentions:
                content = content.replace(f"<@{u.id}>", f"@{u.display_name}")
            msgs.append({
                "id": str(m.id), "author": m.author.display_name, "avatar": str(m.author.avatar.url) if m.author.avatar else "",
                "content": content, "is_bot": m.author.bot, "timestamp": m.created_at.strftime("%I:%M %p"),
                "attachments": [a.url for a in m.attachments]
            })
        return {"messages": msgs[::-1], "bot_id": str(bot.user.id)}
    except Exception as e:
        return {"error": str(e)}

@app.route('/api/send_message', methods=['POST'])
async def send_message_api():
    data = await request.get_json()
    if not bot:
        return {"status": "error"}
    try:
        ch = bot.get_channel(int(data.get('channel_id')))
        await ch.send(data.get('content'))
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "details": str(e)}

@app.route('/api/get_server_emojis')
async def get_server_emojis():
    # Only for the current guild?
    # This seems used by broadcast or something.
    if not bot:
        return {"emojis": []}
    emojis = []
    for g in bot.guilds:
        for e in g.emojis:
            emojis.append({"name": e.name, "url": str(e.url), "code": f"<{'a' if e.animated else ''}:{e.name}:{e.id}>"})
    return {"emojis": emojis[:100]}

# --- أوامر أخرى (Global) ---
@app.route('/commands')
async def commands_view():
    if not bot:
        return "Bot loading..."
    data = {name: [{'name': c.name, 'desc': c.description or ""} for c in cog.get_commands()] for name, cog in bot.cogs.items()}
    return await render_template('commands.html', cogs=data)

@app.route('/confessions')
async def confessions():
    return await render_template('confessions.html', secrets=getattr(bot, 'confessions_list', []))

@app.route('/kill_switch', methods=['POST'])
async def kill_switch():
    os.execv(sys.executable, ['python'] + sys.argv)

@app.route('/reload', methods=['POST'])
async def reload_cogs():
    if bot:
        for ext in list(bot.extensions):
            try:
                await bot.reload_extension(ext)
            except:
                pass
    return redirect('/')

# --- 🔥 تشغيل السيرفر ---
async def run_server(bot_instance):
    global bot
    bot = bot_instance
    await app.run_task(host='0.0.0.0', port=26669)
