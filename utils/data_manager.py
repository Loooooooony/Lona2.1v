import os
import json
import shutil

# Paths
DATA_DIR = 'data'
GUILDS_DIR = os.path.join(DATA_DIR, 'guilds')
PASSWORDS_FILE = os.path.join(DATA_DIR, 'server_passwords.json')

def ensure_data_dirs():
    if not os.path.exists(GUILDS_DIR):
        os.makedirs(GUILDS_DIR)
    if not os.path.exists(PASSWORDS_FILE):
        with open(PASSWORDS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)

ensure_data_dirs()

def get_guild_dir(guild_id):
    """Returns the directory path for a specific guild, creating it if needed."""
    path = os.path.join(GUILDS_DIR, str(guild_id))
    if not os.path.exists(path):
        os.makedirs(path)
        # Create images folder inside
        os.makedirs(os.path.join(path, 'images'), exist_ok=True)
    return path

def get_guild_file(guild_id, filename):
    """Returns the full path to a specific file within a guild's directory."""
    guild_dir = get_guild_dir(guild_id)
    return os.path.join(guild_dir, filename)

def get_guild_asset(guild_id, filename, default_path):
    """
    Checks if a custom asset exists in 'data/guilds/{id}/images/{filename}'.
    If yes, returns that path.
    If no, returns 'default_path'.
    """
    guild_dir = get_guild_dir(guild_id)
    custom_path = os.path.join(guild_dir, 'images', filename)

    if os.path.exists(custom_path):
        return custom_path
    return default_path

def check_guild_password(guild_id, password):
    """Checks if the provided password matches the guild's password."""
    try:
        with open(PASSWORDS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            real_pass = data.get(str(guild_id))
            return real_pass and real_pass == password
    except:
        return False

def set_guild_password(guild_id, password):
    """Sets the password for a guild."""
    try:
        with open(PASSWORDS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        data = {}

    data[str(guild_id)] = password

    with open(PASSWORDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
