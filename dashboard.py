from quart import Quart, render_template, request, redirect, url_for, send_file, session
import discord
import os
import sys
import asyncio
import json
import io
import re
import datetime

app = Quart(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.secret_key = b'Lona_Secret_Key_2025_Secure'

# 🔐 باسورد المحرر
EDITOR_PASSWORD = "lona"

# تعريف المتغيرات العامة
bot = None      

# ملفات الداتا للمحرر
DATA_FILES = {
    "tod": {"name": "🍾 صراحة وجرأة", "path": "data/tod_data.py"},
    "family": {"name": "👨‍👩‍👧‍👦 عائلتي تربح", "path": "data/questions.json"},
    "codenames": {"name": "🕵️‍♂️ كود نيمز", "path": "data/codenames_data.py"},
    "social": {"name": "🤬 ردود القصف", "path": "utils/user_data.py"},
    "khira": {"name": "🤔 لو خيروك", "path": "utils/khira_data.py"},
    "islamic": {"name": "🕌 إعدادات الإسلامي", "path": "data/islamic_config.json"}
}

# --- الصفحة الرئيسية ---
# في ملف dashboard.py

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
    
    # نودي هاي القائمة لملف html جديد
    return await render_template('select_server.html', guilds=guilds_list)

import json # تأكدي انه موجود فوق

# مسار ملف الباسوردات
PASSWORDS_FILE = 'data/server_passwords.json'

def get_server_password(guild_id):
    try:
        with open(PASSWORDS_FILE, 'r') as f:
            data = json.load(f)
            return data.get(str(guild_id))
    except:
        return None

# صفحة تسجيل الدخول للسيرفر
@app.route('/login/<guild_id>', methods=['GET', 'POST'])
async def server_login(guild_id):
    error = None
    guild = bot.get_guild(int(guild_id)) if bot else None
    
    if request.method == 'POST':
        form = await request.form
        password = form.get('password')
        
        real_password = get_server_password(guild_id)
        
        # اذا الباسورد صح
        if real_password and password == real_password:
            # نعطيه "فيزا" دخول لهذا السيرفر
            session[f'access_{guild_id}'] = True 
            return redirect(f'/dashboard/{guild_id}')
        else:
            error = "❌ كلمة المرور خطأ!"

    return await render_template('server_login.html', guild=guild, error=error)

# لوحة التحكم (الداشبورد) - مؤقتاً للتجربة
@app.route('/dashboard/<guild_id>')
async def dashboard(guild_id):
    # الحماية: هل عندك فيزا؟ 🛂
    if not session.get(f'access_{guild_id}'):
        return redirect(f'/login/{guild_id}') # ارجع لصفحة الدخول
    
    return f"<h1>🎉 هلو! انت دخلت لداشبورد السيرفر رقم {guild_id} بنجاح!</h1>"

# --- 🔐 تسجيل الدخول للمحرر ---
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

# --- 🛡️ قسم الإدارة (Moderation) ---
@app.route('/moderation')
async def moderation_panel():
    config_path = 'data/moderation_config.json'
    
    # القائمة الكاملة للأوامر
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
    try:
        with open(config_path, 'r', encoding='utf-8') as f: config = json.load(f)
        
        # دمج الأوامر الجديدة والتأكد من وجودها
        for k, v in default_cmds.items():
            if k not in config: 
                config[k] = v
                updated = True # لقينا أمر جديد!
        
        # 🔥 هنا الحل: اذا اكو تحديث، احفظ الملف فوراً
        if updated:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)

    except:
        config = default_cmds
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

    return await render_template('moderation.html', commands=config)
# API لتشغيل/إطفاء الأوامر بسرعة (Switch)
@app.route('/api/toggle_mod_cmd', methods=['POST'])
async def toggle_mod_cmd():
    data = await request.get_json()
    cmd_key = data.get('cmd')
    state = data.get('state') # True or False
    
    config_path = 'data/moderation_config.json'
    try:
        with open(config_path, 'r', encoding='utf-8') as f: config = json.load(f)
        if cmd_key in config:
            config[cmd_key]['enabled'] = state
            with open(config_path, 'w', encoding='utf-8') as f: json.dump(config, f, indent=4)
            return {"status": "success"}
    except Exception as e:
        return {"status": "error", "msg": str(e)}
    return {"status": "error"}

# --- ✏️ صفحة تعديل الأمر (Edit Command) ---
@app.route('/moderation/edit/<cmd_key>', methods=['GET', 'POST'])
async def edit_mod_cmd(cmd_key):
    config_path = 'data/moderation_config.json'
    try:
        with open(config_path, 'r', encoding='utf-8') as f: config = json.load(f)
    except: return redirect('/moderation')

    if cmd_key not in config: return redirect('/moderation')
    
    # عند الضغط على حفظ
    if request.method == 'POST':
        form = await request.form
        
        # 1. معالجة النصوص (Aliases)
        aliases_str = form.get('aliases', '')
        # نحول النص الى قائمة (نقسم بالفواصل)
        config[cmd_key]['aliases'] = [x.strip() for x in aliases_str.split(',') if x.strip()]

        # 2. معالجة الرتب (Roles IDs)
        roles_str = form.get('roles', '')
        config[cmd_key]['roles'] = [x.strip() for x in roles_str.split(',') if x.strip()]

        # 3. معالجة الرومات (Channels IDs)
        channels_str = form.get('channels', '')
        config[cmd_key]['channels'] = [x.strip() for x in channels_str.split(',') if x.strip()]

        # 4. باقي الإعدادات
        config[cmd_key]['delete_after'] = int(form.get('delete_after', 0))
        config[cmd_key]['enabled'] = 'enabled' in form

        # حفظ
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
            
        return redirect('/moderation')

    return await render_template('moderation_edit.html', cmd=config[cmd_key], key=cmd_key)

# --- 🎮 ستوديو الألعاب (مع التحديث التلقائي) ---
@app.route('/game_studio', methods=['GET', 'POST'])
async def game_studio():
    config_path = 'data/games_config.json'
    
    # الإعدادات الافتراضية
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

    try:
        with open(config_path, 'r', encoding='utf-8') as f: config = json.load(f)
    except:
        config = default_config
        with open(config_path, 'w', encoding='utf-8') as f: json.dump(config, f, indent=4)

    if request.method == 'POST':
        form = await request.form
        
        # 1. حفظ البيانات بالملف
        # الروليت
        config['roulette']['command_name'] = form.get('r_cmd')
        config['roulette']['title'] = form.get('r_title')
        config['roulette']['description'] = form.get('r_desc')
        config['roulette']['color'] = form.get('r_color')
        config['roulette']['btn_join'] = form.get('r_btn_join')
        config['roulette']['btn_start'] = form.get('r_btn_start')
        config['roulette']['msg_win'] = form.get('r_msg_win')

        # كودنيمز
        config['codenames']['command_name'] = form.get('c_cmd')
        config['codenames']['title'] = form.get('c_title')
        config['codenames']['description'] = form.get('c_desc')
        config['codenames']['color'] = form.get('c_color')
        config['codenames']['btn_join'] = form.get('c_btn_join')
        config['codenames']['btn_start'] = form.get('c_btn_start')

        # عائلتي
        config['family']['command_name'] = form.get('f_cmd')
        config['family']['title'] = form.get('f_title')
        config['family']['description'] = form.get('f_desc')
        config['family']['color'] = form.get('f_color')
        config['family']['btn_join'] = form.get('f_btn_join')
        config['family']['btn_start'] = form.get('f_btn_start')

        # الجاسوس
        config['spyfall']['command_name'] = form.get('s_cmd')
        config['spyfall']['title'] = form.get('s_title')
        config['spyfall']['description'] = form.get('s_desc')
        config['spyfall']['color'] = form.get('s_color')
        config['spyfall']['btn_join'] = form.get('s_btn_join')
        config['spyfall']['btn_start'] = form.get('s_btn_start')
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
            
        # 2. 🔥 التحديث الفوري (Hot Reload) 🔥
        # هذا الكود يخلي البوت يعيد تحميل الألعاب فوراً بدون ريستارت
        if bot:
            cogs_to_reload = [
                'cogs.roulette_royal',
                'cogs.codenames',
                'cogs.family_feud',
                'cogs.spy_game'
            ]
            reloaded_count = 0
            for cog in cogs_to_reload:
                try:
                    await bot.reload_extension(cog)
                    reloaded_count += 1
                except Exception as e:
                    print(f"⚠️ فشل تحديث {cog}: {e}")

            msg = f"✅ تم الحفظ وتحديث {reloaded_count} ألعاب فوراً!"
        else:
            msg = "✅ تم الحفظ (البوت غير متصل، سيتم التحديث عند التشغيل)"

        return await render_template('game_studio.html', config=config, success=msg)

    return await render_template('game_studio.html', config=config)

# --- دالة القيف اوي الشاملة ---
@app.route('/giveaway', methods=['GET', 'POST'])
async def giveaway_panel():
    config_path = 'data/giveaway_config.json'
    active_path = 'data/active_giveaways.json'
    
    # تحميل الإعدادات القديمة
    try:
        with open(config_path, 'r', encoding='utf-8') as f: config = json.load(f)
    except: config = {}

    if request.method == 'POST':
        form = await request.form
        action = form.get('action')

        # 1. أوامر الإنهاء (من الجدول)
        if action == 'end_now':
            target_id = int(form.get('target_id'))
            if bot:
                cog = bot.get_cog('GiveawaySystem')
                if cog:
                    await cog.end_giveaway(target_id)
                    return redirect('/giveaway')

        # 2. حفظ الإعدادات (كمية ضخمة من البيانات) 🤯
        new_config = {
            "prize": form.get('prize'),
            "winners": int(form.get('winners', 1)),
            "time_val": int(form.get('time_val', 24)),
            "time_unit": form.get('time_unit', 'h'),
            "description": form.get('description'),
            "color": form.get('color'),
            "channel_id": form.get('channel_id'),
            
            # 🔥 كل التخصيصات رجعت هنا 🔥
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
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(new_config, f, indent=4, ensure_ascii=False)

        return await render_template('giveaway.html', config=new_config, active_list=[], success="✅ تم حفظ القالب الشامل!")

    # --- قراءة القيفات النشطة من الملف (أضمن طريقة) ---
    active_list = []
    if os.path.exists(active_path):
        try:
            with open(active_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for msg_id, g_data in data.items():
                    active_list.append({
                        'id': msg_id,
                        'prize': g_data.get('prize', 'جائزة'),
                        'winners': g_data.get('winners_count', 1),
                        'participants': len(g_data.get('participants', [])),
                        'end_time': datetime.datetime.fromtimestamp(g_data['end_timestamp']).strftime('%H:%M:%S')
                    })
        except: pass

    return await render_template('giveaway.html', config=config, active_list=active_list)

# --- ⚙️ الإعدادات ---
@app.route('/settings', methods=['GET', 'POST'])
async def settings():
    if not bot:
        return "Bot not ready"
    
    status_config_path = 'data/status_config.json'

    if request.method == 'POST':
        form = await request.form
        files = await request.files
        
        # 1. الحالة
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

        # 2. البروفايل (اسم وصورة فقط)
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
            return await render_template('settings.html', error=f"فشل تحديث البروفايل: {e}", bot=bot.user, config=save_data)

        return await render_template('settings.html', success="✅ تم التحديث!", bot=bot.user, config=save_data)
    
    try:
        with open(status_config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except:
        config = {"status": "online", "activity_type": "playing", "text": "", "url": ""}
        
    return await render_template('settings.html', bot=bot.user, config=config)

# --- 🧠 الردود التلقائية ---
@app.route('/auto_reply', methods=['GET', 'POST'])
async def auto_reply_manager():
    path = 'data/auto_reply.json'
    try:
        with open(path, 'r', encoding='utf-8') as f:
            replies = json.load(f)
    except:
        replies = {}

    if request.method == 'POST':
        form = await request.form
        if 'add_trigger' in form:
            trigger = form.get('trigger').strip()
            response = form.get('response').strip()
            if trigger and response:
                replies[trigger] = response
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(replies, f, indent=4, ensure_ascii=False)
                if bot and bot.get_cog('AutoReply'):
                    bot.get_cog('AutoReply').replies = replies
        elif 'delete_trigger' in form:
            trigger = form.get('delete_trigger')
            if trigger in replies:
                del replies[trigger]
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(replies, f, indent=4, ensure_ascii=False)
                if bot and bot.get_cog('AutoReply'):
                    bot.get_cog('AutoReply').replies = replies
                    
    return await render_template('auto_reply.html', replies=replies)

# --- 👮🏻‍♀️ إعدادات اللوق ---
@app.route('/logger_settings', methods=['GET', 'POST'])
async def logger_settings():
    path = 'data/log_config.json'
    try:
        with open(path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except:
        config = {"log_channel_id": "", "events": {}}

    if request.method == 'POST':
        form = await request.form
        config['log_channel_id'] = form.get('channel_id')
        event_keys = ['msg_delete', 'msg_edit', 'msg_bulk', 'member_join', 'member_leave', 'member_update', 'user_update', 'voice_update', 'emoji_update', 'server_update', 'invite_update', 'ban_add', 'ban_remove', 'channel_create', 'channel_delete', 'channel_update', 'role_create', 'role_delete', 'role_update']
        for key in event_keys:
            config['events'][key] = key in form
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        return await render_template('logger_settings.html', config=config, success="✅ تم الحفظ!")
    
    return await render_template('logger_settings.html', config=config)

def parse_emoji(emoji_str):
    if not emoji_str: return None
    custom_match = re.search(r'<(a?):(\w+):(\d+)>', emoji_str)
    return discord.PartialEmoji(name=custom_match.group(2), id=int(custom_match.group(3)), animated=bool(custom_match.group(1))) if custom_match else emoji_str

# --- 📢 المذيع ---
@app.route('/broadcast', methods=['GET', 'POST'])
async def broadcast_page():
    if request.method == 'POST':
        if not bot: return "Bot not connected"
        form = await request.form
        files = await request.files 
        try:
            channel = bot.get_channel(int(form.get('channel_id')))
            if not channel: return await render_template('broadcast.html', error="❌ القناة خطأ")
            
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
            return await render_template('broadcast.html', success="✅ تم النشر!")
        except Exception as e:
            return await render_template('broadcast.html', error=f"خطأ: {e}")
            
    return await render_template('broadcast.html')

# --- 🎮 إدارة الألعاب ---
@app.route('/games')
async def games_manager():
    if not bot:
        return "Bot loading..."
    active_games = []
    if bot.get_cog('SpyGame'):
        for cid, s in bot.get_cog('SpyGame').sessions.items():
            if s.game_active:
                active_games.append({'name': 'Spyfall', 'cid': cid, 'type': 'spy'})
    if bot.get_cog('CodenamesGame'):
        for cid, s in bot.get_cog('CodenamesGame').sessions.items():
            if s.game_active:
                active_games.append({'name': 'Codenames', 'cid': cid, 'type': 'codenames'})
    if bot.get_cog('FamilyFeud'):
        for cid, s in bot.get_cog('FamilyFeud').active_games.items():
            active_games.append({'name': 'Family Feud', 'cid': cid, 'type': 'family'})
    return await render_template('games.html', games=active_games)

@app.route('/stop_game/<gtype>/<int:cid>')
async def stop_game(gtype, cid):
    if not bot:
        return "Bot error"
    try:
        ch = bot.get_channel(cid)
        if gtype == 'spy':
            bot.get_cog('SpyGame').sessions[cid].game_active = False
        elif gtype == 'codenames':
            bot.get_cog('CodenamesGame').sessions[cid].game_active = False
        elif gtype == 'family':
            del bot.get_cog('FamilyFeud').active_games[cid]
        if ch:
            await ch.send("🛑 **تم إيقاف اللعبة من الداشبورد!**")
    except:
        pass
    return redirect(url_for('games_manager'))

# --- 👋🏻 الترحيب ---
@app.route('/welcome', methods=['GET', 'POST'])
async def welcome_studio():
    config_path = 'data/welcome_config.json'
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except:
        config = {}
        
    if request.method == 'POST':
        form = await request.form
        files = await request.files
        config.update({k: v for k, v in form.items() if k in ['channel_id', 'message', 'avatar_shape', 'avatar_x', 'avatar_y', 'avatar_size', 'text_x', 'text_y', 'font_size', 'text_color', 'image_text']})
        config['enabled'] = 'enabled' in form
        
        if 'bg_file' in files and files['bg_file'].filename:
            await files['bg_file'].save('data/welcome_bg.png')
        if 'font_file' in files and files['font_file'].filename:
            await files['font_file'].save('data/welcome_font.ttf')
            
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
            
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return {"status": "success", "msg": "✅ تم الحفظ!"}
        return await render_template('welcome.html', config=config, success="✅ تم الحفظ!")
    
    return await render_template('welcome.html', config=config)

@app.route('/welcome_assets/<filename>')
async def welcome_assets(filename):
    return await send_file(f'data/{filename}')

@app.route('/api/test_welcome', methods=['POST'])
async def test_welcome_api():
    if not bot or not bot.get_cog('WelcomeSystem'):
        return {"status": "error", "msg": "Welcome Cog Not Loaded"}
    try:
        await bot.get_cog('WelcomeSystem').send_welcome_card(bot.user, is_test=True)
        return {"status": "success", "msg": "✅ تم الإرسال!"}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

# --- 💀 الروليت ---
@app.route('/roulette_control', methods=['GET', 'POST'])
async def roulette_control():
    config_path = 'data/roulette_config.json'
    log_path = 'data/death_log.json'
    
    if request.method == 'POST':
        form = await request.form
        with open(config_path, 'w') as f:
            json.dump({"mode": form.get('mode')}, f)
        return redirect(url_for('roulette_control'))
        
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except:
        config = {"mode": "kick"}
        
    try:
        with open(log_path, 'r') as f:
            logs = json.load(f)
    except:
        logs = []
        
    return await render_template('roulette.html', config=config, logs=logs[::-1])

# --- 🕌 الإسلامي ---
@app.route('/islamic', methods=['GET', 'POST'])
async def islamic_settings():
    config_path = 'data/islamic_config.json'
    if request.method == 'POST':
        form = await request.form
        data = {
            "enabled": 'enabled' in form, "voice_channel_id": form.get('voice_channel_id'), "text_channel_id": form.get('text_channel_id'),
            "reader": form.get('reader'), "azkar_sabah": 'azkar_sabah' in form, "azkar_masa": 'azkar_masa' in form, "friday_kahf": 'friday_kahf' in form
        }
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        return redirect(url_for('islamic_settings'))
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except:
        config = {}
        
    return await render_template('islamic.html', config=config)

# --- 📡 Live Chat ---
@app.route('/live_chat')
async def live_chat_page():
    return await render_template('live_chat.html')

@app.route('/api/get_sidebar')
async def get_sidebar():
    if not bot:
        return {"guilds": []}
    data = []
    for guild in bot.guilds:
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
    if not bot:
        return {"emojis": []}
    emojis = []
    for g in bot.guilds:
        for e in g.emojis:
            emojis.append({"name": e.name, "url": str(e.url), "code": f"<{'a' if e.animated else ''}:{e.name}:{e.id}>"})
    return {"emojis": emojis[:100]}
# --- أوامر أخرى ---
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

@app.route('/change_status', methods=['POST'])
async def change_status():
    if bot:
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Spotify 🎵"))
    return redirect('/')

# --- 🔥 تشغيل السيرفر ---
async def run_server(bot_instance):
    global bot
    bot = bot_instance
    await app.run_task(host='0.0.0.0', port=26669)